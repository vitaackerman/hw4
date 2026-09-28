"""PydanticAI agent for the Campus Customs chat widget, running an OpenAI model through Portkey."""

import logging
import os
import re
import time
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

# Hide PydanticAI's startup banner in the uvicorn logs.
os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from dotenv import load_dotenv
from pydantic_ai import Agent, ModelRetry, RunContext, capture_run_messages
from pydantic_ai.exceptions import ModelHTTPError, UsageLimitExceeded
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, ToolCallPart, UserPromptPart
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

from audit import record_run
from models import AgentReply, ChatDeps, ChatReply, ChatTurn, CustomerContext, LookupLog, PageContext, ViewedProduct
from tools import AGENT_TOOLS, find_product_name, product_cards, search_results_payload

TOOL_NAMES = {tool.__name__ for tool in AGENT_TOOLS}

HERE = Path(__file__).resolve().parent
PROMPT_PATH = HERE / "prompts" / "prompt.md"
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"
DEFAULT_MODEL = "gpt-5.6-luna"
REQUEST_LIMIT = 8  # model requests (each tool round trip is one) allowed per chat message
# uvicorn prints this logger at INFO, so tool calls show up in the backend terminal.
logger = logging.getLogger("uvicorn.error")
# Sent when the provider's content filter blocks a message before the model sees it.
FILTERED_REPLY = "I can't help with that one, but I'm always happy to help you find some Yale gear. What are you shopping for?"
# Sent if the agent hits its request cap (e.g. keeps searching for something we don't sell).
GAVE_UP_REPLY = (
    "I couldn't find that one in the Campus Customs shop. We carry hoodies, crewnecks, tees, quarter-zips "
    "and jackets. Want me to look for one of those?"
)

# Key lives in the Coding/.env shared by every homework; check HW4 and its parents, nearest first.
for folder in [HERE, *HERE.parents]:
    load_dotenv(folder / ".env")


class ChatNotConfigured(RuntimeError):
    """Raised when PORTKEY_API_KEY is missing, so the route can return a clear error."""


@lru_cache(maxsize=1)
def get_model() -> OpenAIChatModel:
    key = os.getenv("PORTKEY_API_KEY")
    if not key:
        raise ChatNotConfigured("PORTKEY_API_KEY is not set. Add it to the root .env file.")
    provider = OpenAIProvider(base_url=PORTKEY_BASE_URL, api_key=key)
    return OpenAIChatModel(os.getenv("OPENAI_MODEL", DEFAULT_MODEL), provider=provider)


agent = Agent(
    output_type=AgentReply,
    deps_type=ChatDeps,
    tools=AGENT_TOOLS,
    # Tools get 2 retries; the reply gets 3 chances to pass numbers_must_come_from_tools.
    retries={"tools": 2, "output": 3},
    model_settings={"timeout": 60},
    name="campus_customs_chat",
)

# "$68", "$68.00", "$ 72"
PRICE_PATTERN = re.compile(r"\$\s?(\d+(?:\.\d{1,2})?)")
# "5 left", "12 in stock", "only 2", "3 available", "8 units"
STOCK_PATTERN = re.compile(r"\b(\d+)\s+(?:left|in stock|available|units?|pieces?)\b|\bonly\s+(\d+)\b", re.IGNORECASE)


@agent.instructions
def load_prompt() -> str:
    # Read on every run so edits to prompt.md apply without restarting the server.
    return PROMPT_PATH.read_text(encoding="utf-8")


PAGE_DESCRIPTIONS = {
    "home": "the home page",
    "products": "the Products page",
    "about": "the About Us page",
    "login": "the Log In page",
    "create-account": "the Create Account page",
}
CATEGORIES = {"Hoodies", "Crewnecks", "Tees", "Quarter-zips", "Jackets & fleece"}


@agent.instructions
def session_context(ctx: RunContext[ChatDeps]) -> str:
    """Tells the agent who is chatting and which page they're looking at, for this message only."""
    deps = ctx.deps
    lines = ["## This conversation"]
    if deps.customer:
        c = deps.customer
        lines.append(
            f"- Customer: logged in as {c.first_name} {c.last_name} ({c.email}), member since {c.member_since[:10]}. "
            f"Greet them by first name now and then. Their earlier chats are saved and included above, so you can "
            f"refer back to them. Only share their own account details with them."
        )
    else:
        lines.append("- Customer: a guest (not logged in). You don't know their name. If they want you to remember them, suggest creating an account.")
    if deps.viewed_product:
        p = deps.viewed_product
        lines.append(
            f'- Page: they are viewing the product page for "{p.name}" (product_id: {p.product_id}). '
            f'"This", "it", "this one" or "that" means this product unless they name another. '
            f"Use its product_id directly with get_price, get_stock or check_size_stock; don't search for it."
        )
    else:
        page = PAGE_DESCRIPTIONS.get(deps.page_kind, "a page on the site")
        if deps.page_kind == "products" and deps.page_category:
            page += f", filtered to {deps.page_category}"
        lines.append(f"- Page: they are on {page}. If they say \"this\" without naming a product, ask which one they mean.")
    return "\n".join(lines)


@agent.output_validator
def numbers_must_come_from_tools(ctx: RunContext[LookupLog], output: AgentReply) -> AgentReply:
    """Reject replies that state a price or stock count no tool returned during this message."""
    log = ctx.deps
    bad_prices = sorted({m for m in PRICE_PATTERN.findall(output.reply) if round(float(m), 2) not in log.prices})
    bad_stock = sorted({int(a or b) for a, b in STOCK_PATTERN.findall(output.reply) if int(a or b) not in log.quantities})
    if bad_prices or bad_stock:
        problems = [f"price ${p}" for p in bad_prices] + [f"stock number {q}" for q in bad_stock]
        raise ModelRetry(
            f"Your reply mentions {', '.join(problems)}, which no tool returned for this message. "
            "Call get_price / get_stock / check_size_stock now and use only the numbers they return."
        )
    return output


def to_message_history(history: list[ChatTurn]) -> list[ModelMessage]:
    messages: list[ModelMessage] = []
    for turn in history:
        if turn.role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=turn.content)]))
        else:
            messages.append(ModelResponse(parts=[TextPart(content=turn.content)]))
    return messages


def build_deps(customer: CustomerContext | None, page: PageContext | None) -> ChatDeps:
    page = page or PageContext()
    viewed = None
    if page.kind == "product" and page.product_id:
        # Trust only the id from the browser; the name comes from the database (and bogus ids are ignored).
        if name := find_product_name(page.product_id):
            viewed = ViewedProduct(product_id=page.product_id, name=name)
    category = page.category if page.category in CATEGORIES else None
    return ChatDeps(customer=customer, viewed_product=viewed, page_kind=page.kind, page_category=category)


async def run_chat(
    message: str,
    history: list[ChatTurn],
    customer: CustomerContext | None = None,
    page: PageContext | None = None,
    customer_id: int | None = None,
) -> ChatReply:
    """Run the agent for one shopper message. Every run, successful or not, is appended to the audit trail."""
    started_at = datetime.now(timezone.utc)
    started = time.monotonic()
    stop_reason = "error"
    reply: ChatReply | None = None
    with capture_run_messages() as messages:
        try:
            reply = await _run_agent(message, history, customer, page)
            stop_reason = "completed"
            return reply
        except UsageLimitExceeded:
            logger.warning("Chat hit the request limit for message: %r", message[:200])
            stop_reason = f"request_limit ({REQUEST_LIMIT} model requests)"
            reply = ChatReply(reply=GAVE_UP_REPLY)
            return reply
        except ModelHTTPError as exc:
            # Portkey routes to Azure OpenAI, which rejects jailbreak-style or unsafe prompts with a 400 content_filter.
            if exc.status_code == 400 and "content_filter" in str(exc.body):
                stop_reason = "content_filtered (provider blocked the prompt)"
                reply = ChatReply(reply=FILTERED_REPLY)
                return reply
            stop_reason = f"model_http_error {exc.status_code}"
            raise
        except ChatNotConfigured:
            stop_reason = "not_configured (PORTKEY_API_KEY missing)"
            raise
        except Exception as exc:
            stop_reason = f"error: {type(exc).__name__}"
            raise
        finally:
            page = page or PageContext()
            record_run(
                started_at=started_at,
                duration_ms=round((time.monotonic() - started) * 1000),
                message=message,
                customer_id=customer_id,
                page={"kind": page.kind, "product_id": page.product_id, "category": page.category},
                messages=list(messages),
                tool_names=TOOL_NAMES,
                model_name=os.getenv("OPENAI_MODEL", DEFAULT_MODEL),
                stop_reason=stop_reason,
                reply=reply,
            )


async def _run_agent(
    message: str,
    history: list[ChatTurn],
    customer: CustomerContext | None,
    page: PageContext | None,
) -> ChatReply:
    log = build_deps(customer, page)
    # Numbers the shopper typed (a budget like "under $70") may be repeated back.
    log.allow_shopper_numbers(message)
    result = await agent.run(
        message,
        model=get_model(),
        deps=log,
        message_history=to_message_history(history),
        # Caps tool-call loops so one message can't run up the Portkey bill.
        usage_limits=UsageLimits(request_limit=REQUEST_LIMIT),
    )
    tool_calls = [
        f"{part.tool_name}({part.args_as_json_str()})"
        for msg in result.new_messages()
        if isinstance(msg, ModelResponse)
        for part in msg.parts
        if isinstance(part, ToolCallPart) and part.tool_name in TOOL_NAMES
    ]
    logger.info("Chat tools used (%d model requests): %s", result.usage.requests, "; ".join(tool_calls) or "none")
    output = result.output
    # The grid comes from what search_products actually matched, never from the reply text.
    search_results = None
    if output.show_search_results and log.last_search_ids:
        search_results = search_results_payload(log.last_search_query or "", log.last_search_ids)
    # Clarification options replace recommendation cards so the same products aren't shown twice.
    options = product_cards(output.clarification_options)
    return ChatReply(
        reply=output.reply.strip(),
        products=[] if options else product_cards(output.product_ids),
        search_results=search_results,
        clarification_options=options,
    )
