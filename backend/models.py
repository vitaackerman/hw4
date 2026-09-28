"""Structured Pydantic types shared by the chat route, the agent and its tools."""

import re
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

MAX_MESSAGE_LENGTH = 1000
MAX_HISTORY_MESSAGES = 20


# ---------- Chat API (frontend <-> FastAPI) ----------


class ChatTurn(BaseModel):
    """One earlier message in the conversation, as the chat widget sends it."""

    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


PageKind = Literal["home", "products", "product", "about", "login", "create-account", "other"]


class PageContext(BaseModel):
    """Where the shopper is on the site. Only ids and fixed labels; the backend looks up names itself."""

    kind: PageKind = "other"
    product_id: str | None = Field(default=None, max_length=120, description="Set on a product page.")
    category: str | None = Field(default=None, max_length=40, description="Category filter on the Products page.")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)
    # Guests only: earlier turns kept in the widget. Logged-in history comes from chat_messages instead.
    history: list[ChatTurn] = Field(default_factory=list, max_length=MAX_HISTORY_MESSAGES)
    page: PageContext | None = None


class ProductCard(BaseModel):
    """A product shown under a chat reply. Always built from the database, never from model text."""

    product_id: str
    name: str
    price: float
    image_url: str
    total_stock: int


class ProductMatch(BaseModel):
    """One catalogue match for the page's result grid. Same fields a Products-page card needs."""

    product_id: str
    name: str
    garment_type: str
    price: float
    image_url: str
    short_description: str
    colors: list[str]
    total_stock: int


class ChatSearchResults(BaseModel):
    """Every product the agent's search matched, built from the database after the run."""

    query: str = Field(description="The search_products query that produced these matches.")
    total_matches: int
    products: list[ProductMatch]


class ChatReply(BaseModel):
    """The /api/chat response contract."""

    reply: str
    # Up to 4 specific recommendations, shown as small cards inside the chat.
    products: list[ProductCard] = Field(default_factory=list)
    # Set when the shopper asked to browse a type of item; the website shows these as a card grid.
    search_results: ChatSearchResults | None = None
    # Set when the request could mean several products; the chat shows these as "I mean this one" buttons.
    clarification_options: list[ProductCard] = Field(default_factory=list)


class HistoryMessage(BaseModel):
    """One saved chat_messages row, as the widget renders it."""

    id: int
    role: Literal["user", "assistant"]
    content: str
    products: list[ProductCard] = Field(default_factory=list)
    created_at: str


class ChatHistory(BaseModel):
    messages: list[HistoryMessage]


# ---------- Agent output (what the LLM must return) ----------


class AgentReply(BaseModel):
    """Structured output the agent returns; the backend turns product_ids into ProductCards."""

    reply: str = Field(description="The message shown to the shopper. Plain text, no markdown, usually 1-4 short sentences.")
    product_ids: list[str] = Field(
        default_factory=list,
        max_length=4,
        description="product_id values from tool results that the reply recommends, best first. Empty if none.",
    )
    clarification_options: list[str] = Field(
        default_factory=list,
        max_length=4,
        description=(
            "When the shopper's question is about ONE product but several real products match and you're asking "
            "which one they mean: 2-4 candidate product_ids from tool results. The website shows them as buttons. "
            "Leave product_ids empty when you use this."
        ),
    )
    show_search_results: bool = Field(
        default=False,
        description=(
            "True when the shopper asked to browse or find a type of item (e.g. 'what hoodies do you have?', "
            "'show me navy crewnecks under $60') and your last search_products call found matches: the website "
            "then shows every match as product cards. False for questions about one specific product's price, "
            "stock, size or description."
        ),
    )


# ---------- Tool results (what tools hand back to the LLM) ----------
# Every lookup result carries product_id + name so the model can tie numbers to the right product,
# and every number in these types comes straight from campus_customs.db.

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]


class SizeStock(BaseModel):
    size: str = Field(description="One of XS, S, M, L, XL, XXL.")
    quantity: int = Field(description="Units on hand for this size. 0 means sold out.")
    in_stock: bool


class ProductSummary(BaseModel):
    """One search hit: enough to pick a product and get its product_id for the other tools."""

    product_id: str
    name: str
    garment_type: str
    price: float
    colors: list[str]
    total_stock: int
    short_description: str


class SearchResults(BaseModel):
    """Result of search_products. When nothing matches, `note` says so and `suggestions` offers real alternatives."""

    query: str
    total_matches: int = Field(description="How many products match in total; `products` holds only the top few.")
    min_price: float | None = Field(default=None, description="Lowest price across ALL matches, not just `products`.")
    max_price: float | None = Field(default=None, description="Highest price across ALL matches, not just `products`.")
    products: list[ProductSummary]
    note: str | None = Field(default=None, description="Guidance when the search found nothing or the search budget is used up.")
    suggestions: list[ProductSummary] = Field(default_factory=list, description="Real in-stock products to offer instead.")


class ProductInfo(BaseModel):
    """Result of get_product_info: what the item is."""

    product_id: str
    name: str
    garment_type: str
    colors: list[str]
    description: str = Field(description="Full catalogue description, safe to quote or paraphrase.")


class PriceLookup(BaseModel):
    """Result of get_price."""

    product_id: str
    name: str
    price: float = Field(description="Price in US dollars. The same for every size.")
    currency: Literal["USD"] = "USD"


class StockLookup(BaseModel):
    """Result of get_stock: stock for every size of one product."""

    product_id: str
    name: str
    total_stock: int = Field(description="Sum of quantity over all sizes.")
    sizes: list[SizeStock] = Field(description="Every size in XS..XXL order, including sold-out sizes.")
    available_sizes: list[str]
    sold_out_sizes: list[str]
    alternatives: list[Alternative] = Field(
        default_factory=list, description="Only when every size is sold out: similar products that are in stock."
    )


class Alternative(BaseModel):
    """A similar product that IS in stock in the size the shopper wanted."""

    product_id: str
    name: str
    price: float
    size: str
    quantity_in_size: int
    why_similar: str = Field(description="Short reason, e.g. 'also a crewneck, also navy'.")


class SizeStockLookup(BaseModel):
    """Result of check_size_stock: one size of one product."""

    product_id: str
    name: str
    size: str = Field(description="The size that was checked, normalized (e.g. 'medium' -> 'M').")
    quantity: int
    in_stock: bool
    other_available_sizes: list[str] = Field(description="Other sizes with stock, to suggest if this one is sold out.")
    alternatives: list[Alternative] = Field(
        default_factory=list,
        description="Only when this size is sold out: up to 3 similar products that have this size in stock.",
    )


class NeedsClarification(BaseModel):
    """Returned when a product name fits several real products. Ask the shopper which one; don't pick."""

    needs_clarification: Literal[True] = True
    asked_for: str
    total_matches: int
    candidates: list[ProductSummary] = Field(description="The best 2-4 real matches to offer as options.")
    instruction: str


class LookupFailed(BaseModel):
    """Returned instead of a result when the product or size can't be found, so the model never guesses."""

    error: str
    suggestions: list[ProductSummary] = Field(default_factory=list, description="Closest real products to offer instead.")


# ---------- Per-message agent state ----------


@dataclass
class LookupLog:
    """Agent deps for one chat message: every price and stock number the tools returned.

    The output validator in agent.py only lets the reply mention numbers recorded here,
    so prices and stock counts can't be invented or carried over stale from earlier turns.
    """

    prices: set[float] = field(default_factory=set)
    quantities: set[int] = field(default_factory=set)
    # Searches done for this message; search_products stops after MAX_SEARCHES_PER_MESSAGE.
    searches: int = 0
    # The most recent search that found something: its query and every matching product_id, best first.
    last_search_query: str | None = None
    last_search_ids: list[str] = field(default_factory=list)

    def record_price(self, price: float) -> None:
        self.prices.add(round(price, 2))

    def record_quantities(self, *quantities: int) -> None:
        self.quantities.update(quantities)

    def allow_shopper_numbers(self, text: str) -> None:
        for number in re.findall(r"\d+(?:\.\d{1,2})?", text):
            self.record_price(float(number))
            if "." not in number:
                self.record_quantities(int(number))


@dataclass
class CustomerContext:
    """The logged-in customer, from the verified session token. Never includes password data."""

    first_name: str
    last_name: str
    email: str
    member_since: str


@dataclass
class ViewedProduct:
    """The product page the shopper has open, looked up in the database from the page's product_id."""

    product_id: str
    name: str


@dataclass
class ChatDeps(LookupLog):
    """Agent deps for one chat message: who is chatting, what page they're on, plus the lookup log."""

    customer: CustomerContext | None = None
    viewed_product: ViewedProduct | None = None
    page_kind: str = "other"
    page_category: str | None = None
