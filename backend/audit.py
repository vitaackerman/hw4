"""Append-only audit trail of agent activity: output/audit_trail.json.

One entry per chat run: when it ran, who (guest or user id, never name/email), which page, each tool call
with short arguments and a short result summary, how many model requests it took, any retries, what the
shopper was shown, and why the run stopped. Only structured facts and short summaries are stored; the
model's hidden reasoning is never recorded (PydanticAI doesn't expose it, and model text parts other
than the final reply are skipped).

Existing entries are never rewritten or removed. Each write re-reads the file, appends, and swaps the new
file in atomically, so a crash can't leave a half-written trail. If the file is ever unreadable, it is
moved aside (not deleted) and a fresh trail starts.
"""

import json
import os
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, RetryPromptPart, ToolCallPart, ToolReturnPart

from models import (
    ChatReply,
    LookupFailed,
    NeedsClarification,
    PriceLookup,
    ProductInfo,
    SearchResults,
    SizeStockLookup,
    StockLookup,
)

AUDIT_PATH = Path(__file__).resolve().parent.parent / "output" / "audit_trail.json"
MAX_ARGS_CHARS = 160
MAX_RESULT_CHARS = 200
MAX_PREVIEW_CHARS = 140
_lock = threading.Lock()

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
LONG_NUMBER = re.compile(r"\d[\d\s-]{6,}\d")  # card, phone or id-like digit runs


def redact(text: str) -> str:
    """Strip personal data the shopper (or a reply) might contain before it goes into a shared log."""
    return LONG_NUMBER.sub("[number]", EMAIL.sub("[email]", text))


def _short(text: str, limit: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def summarize_result(content: Any) -> str:
    """One-line, human-readable summary of what a tool returned."""
    if isinstance(content, SearchResults):
        top = ", ".join(p.product_id for p in content.products[:4])
        text = f"{content.total_matches} matches"
        if content.min_price is not None:
            text += f" (${content.min_price:g}-${content.max_price:g})"
        text += f"; top: {top}" if top else "; none"
        if content.note:
            text += f"; note: {content.note}"
        return text
    if isinstance(content, PriceLookup):
        return f"{content.product_id}: ${content.price:g}"
    if isinstance(content, SizeStockLookup):
        text = f"{content.product_id} size {content.size}: {content.quantity} left"
        if not content.in_stock:
            text += f" (sold out); alternatives: {', '.join(a.product_id for a in content.alternatives) or 'none'}"
        return text
    if isinstance(content, StockLookup):
        sizes = " ".join(f"{s.size}={s.quantity}" for s in content.sizes)
        return f"{content.product_id}: total {content.total_stock}; {sizes}"
    if isinstance(content, ProductInfo):
        return f"{content.product_id}: {content.garment_type}; colors {', '.join(content.colors)}"
    if isinstance(content, NeedsClarification):
        return f"needs clarification ({content.total_matches} matches): {', '.join(c.product_id for c in content.candidates)}"
    if isinstance(content, LookupFailed):
        return f"error: {content.error}"
    if isinstance(content, BaseModel):
        return content.model_dump_json()
    return json.dumps(content, default=str) if not isinstance(content, str) else content


def _tool_calls(messages: list[ModelMessage], tool_names: set[str]) -> list[dict]:
    returns = {
        part.tool_call_id: part
        for msg in messages
        if isinstance(msg, ModelRequest)
        for part in msg.parts
        if isinstance(part, ToolReturnPart)
    }
    calls = []
    for msg in messages:
        if not isinstance(msg, ModelResponse):
            continue
        for part in msg.parts:
            if isinstance(part, ToolCallPart) and part.tool_name in tool_names:
                returned = returns.get(part.tool_call_id)
                calls.append(
                    {
                        "tool": part.tool_name,
                        "args": _short(redact(part.args_as_json_str()), MAX_ARGS_CHARS),
                        "result": _short(redact(summarize_result(returned.content)), MAX_RESULT_CHARS)
                        if returned
                        else "(no result: run stopped before the tool returned)",
                    }
                )
    return calls


def _retries(messages: list[ModelMessage]) -> list[str]:
    """Why the framework asked the model to try again (our validator's or schema messages), shortened."""
    reasons = []
    for msg in messages:
        if isinstance(msg, ModelRequest):
            for part in msg.parts:
                if isinstance(part, RetryPromptPart):
                    target = part.tool_name or "reply"
                    content = part.content if isinstance(part.content, str) else json.dumps(part.content, default=str)
                    reasons.append(_short(f"{target}: {content}", MAX_RESULT_CHARS))
    return reasons


def _decision_summary(reply: ChatReply | None, calls: list[dict], stop_reason: str) -> str:
    """Short, auditable description of what the shopper was shown. Not the model's reasoning."""
    if reply is None:
        return f"No reply was shown; the run stopped with {stop_reason}."
    if reply.clarification_options:
        shown = f"asked which product they meant, offering {len(reply.clarification_options)} options"
    elif reply.search_results:
        shown = f"showed {reply.search_results.total_matches} search results on the page"
    elif reply.products:
        shown = f"answered with {len(reply.products)} product card(s)"
    else:
        shown = "answered in text only"
    tools = f"after {len(calls)} tool call(s)" if calls else "without calling a tool"
    return f"Agent {shown} {tools}."


def record_run(
    *,
    started_at: datetime,
    duration_ms: int,
    message: str,
    customer_id: int | None,
    page: dict,
    messages: list[ModelMessage],
    tool_names: set[str],
    model_name: str,
    stop_reason: str,
    reply: ChatReply | None,
) -> dict:
    """Append one run to the audit trail. Never raises: auditing must not break the chat."""
    responses = [m for m in messages if isinstance(m, ModelResponse)]
    calls = _tool_calls(messages, tool_names)
    entry = {
        "run_id": uuid.uuid4().hex[:12],
        "time": started_at.isoformat(timespec="seconds"),
        "duration_ms": duration_ms,
        "customer": f"user #{customer_id}" if customer_id is not None else "guest",
        "page": page,
        "message": _short(redact(message), MAX_PREVIEW_CHARS),
        "model": model_name,
        "model_requests": len(responses),
        "tool_calls": calls,
        "retries": _retries(messages),
        "result": {
            "reply_preview": _short(redact(reply.reply), MAX_PREVIEW_CHARS) if reply else None,
            "product_cards": [c.product_id for c in reply.products] if reply else [],
            "clarification_options": [c.product_id for c in reply.clarification_options] if reply else [],
            "search_results": reply.search_results.total_matches if reply and reply.search_results else 0,
        },
        "decision_summary": _decision_summary(reply, calls, stop_reason),
        "stop_reason": stop_reason,
        "model_finish_reason": responses[-1].finish_reason if responses else None,
    }
    try:
        append_entry(entry)
    except Exception:  # noqa: BLE001 - a logging failure must never take the chat down
        pass
    return entry


def append_entry(entry: dict) -> None:
    with _lock:
        entries: list = []
        if AUDIT_PATH.exists():
            try:
                entries = json.loads(AUDIT_PATH.read_text(encoding="utf-8") or "[]")
                if not isinstance(entries, list):
                    raise ValueError("audit trail is not a JSON list")
            except (ValueError, json.JSONDecodeError):
                # Keep the damaged file for inspection instead of overwriting it.
                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
                AUDIT_PATH.rename(AUDIT_PATH.with_name(f"audit_trail.unreadable-{stamp}.json"))
                entries = []
        entries.append(entry)
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = AUDIT_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp, AUDIT_PATH)
