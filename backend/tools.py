"""Agent tools. All read-only lookups against data/campus_customs.db.

Each tool records the prices and stock numbers it returns in the run's LookupLog,
so agent.py can reject replies that mention numbers no tool returned.
"""

import json
import re
import sqlite3
from contextlib import closing
from pathlib import Path

from pydantic_ai import RunContext

from models import (
    SIZE_ORDER,
    Alternative,
    ChatSearchResults,
    LookupFailed,
    LookupLog,
    NeedsClarification,
    PriceLookup,
    ProductCard,
    ProductMatch,
    ProductInfo,
    ProductSummary,
    SearchResults,
    SizeStock,
    SizeStockLookup,
    StockLookup,
)

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "campus_customs.db"
MAX_SEARCHES_PER_MESSAGE = 3
# The page grid can show up to this many matches; the model only ever sees `limit` of them.
MAX_PAGE_RESULTS = 48
CATEGORIES_WE_CARRY = "hoodies, crewnecks, tees, quarter-zips, and jackets & fleece"

# Shopper words -> words that actually appear in the catalogue.
SYNONYMS = {
    "hoodie": ["hoodie", "hooded"],
    "hoodies": ["hoodie", "hooded"],
    "sweatshirt": ["sweatshirt", "crewneck", "hoodie", "hooded"],
    "crew": ["crewneck", "crew"],
    "tee": ["t-shirt", "tee"],
    "tees": ["t-shirt", "tee"],
    "shirt": ["t-shirt", "shirt"],
    "quarterzip": ["quarter-zip", "1/4 zip", "1-4 zip"],
    "jacket": ["jacket", "fleece"],
    "grey": ["gray"],
}
STOPWORDS = {"a", "an", "the", "any", "do", "you", "have", "i", "want", "some", "something", "for", "me", "in", "with", "and", "or", "of", "show", "looking", "yale", "one", "is", "it"}

# Shopper size words -> database sizes.
SIZE_ALIASES = {
    "xs": "XS", "xsmall": "XS", "extrasmall": "XS",
    "s": "S", "sm": "S", "small": "S",
    "m": "M", "med": "M", "medium": "M",
    "l": "L", "lg": "L", "large": "L",
    "xl": "XL", "xlarge": "XL", "extralarge": "XL",
    "xxl": "XXL", "2xl": "XXL", "xxlarge": "XXL", "2xlarge": "XXL", "extraextralarge": "XXL",
}


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _short(description: str, limit: int = 140) -> str:
    return description if len(description) <= limit else description[:limit].rsplit(" ", 1)[0] + "…"


def _sizes_for(conn: sqlite3.Connection, product_id: str) -> list[SizeStock]:
    rows = conn.execute("SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)).fetchall()
    sizes = [SizeStock(size=r["size"], quantity=r["quantity"], in_stock=r["quantity"] > 0) for r in rows]
    return sorted(sizes, key=lambda s: SIZE_ORDER.index(s.size) if s.size in SIZE_ORDER else len(SIZE_ORDER))


def _total_stock_by_product(conn: sqlite3.Connection) -> dict[str, int]:
    return {r["product_id"]: r["total"] for r in conn.execute("SELECT product_id, SUM(quantity) AS total FROM inventory GROUP BY product_id")}


def _summary(row: sqlite3.Row, total_stock: int) -> ProductSummary:
    return ProductSummary(
        product_id=row["product_id"],
        name=row["name"],
        garment_type=row["garment_type"],
        price=row["price"],
        colors=json.loads(row["colors"]),
        total_stock=total_stock,
        short_description=_short(row["description"]),
    )


def category_of(garment_type: str) -> str:
    """Same grouping as the website's category chips (frontend api.ts categoryOf)."""
    t = garment_type.lower()
    if "quarter-zip" in t:
        return "quarter-zip"
    if "hood" in t:
        return "hoodie"
    if "jacket" in t or "fleece" in t:
        return "jacket"
    if ("crew" in t and "t-shirt" not in t) or "mockneck" in t:
        return "crewneck"
    return "tee"


def normalize_size(size: str) -> str | None:
    key = re.sub(r"[\s\-_.]", "", size.lower())
    return SIZE_ALIASES.get(key)


def _term_options(word: str) -> list[str]:
    if word in SYNONYMS:
        return SYNONYMS[word]
    # Plurals: "crewnecks" -> "crewneck", "jackets" -> "jacket" (+ its synonyms).
    if len(word) > 3 and word.endswith("s"):
        singular = word[:-1]
        return SYNONYMS.get(singular, [singular])
    return [word]


def _query_terms(query: str) -> list[list[str]]:
    text = query.lower().replace("quarter zips", "quarterzip").replace("quarter zip", "quarterzip").replace("quarter-zip", "quarterzip")
    words = [w for w in re.findall(r"[a-z0-9/-]+", text) if w not in STOPWORDS]
    return [_term_options(w) for w in words]


def _search(query: str, max_price: float | None = None, in_stock_only: bool = True, limit: int | None = 6) -> list[ProductSummary]:
    """All matches best-first; limit=None returns every match (used for the page's result grid)."""
    terms = _query_terms(query)
    with closing(_connect()) as conn:
        totals = _total_stock_by_product(conn)
        rows = conn.execute("SELECT * FROM catalogue").fetchall()

    scored: list[tuple[int, ProductSummary]] = []
    for row in rows:
        summary = _summary(row, totals.get(row["product_id"], 0))
        if max_price is not None and summary.price > max_price:
            continue
        if in_stock_only and summary.total_stock == 0:
            continue
        name = row["name"].lower()
        haystack = " ".join([name, row["product_id"], row["garment_type"], row["colors"], row["search_tags"], row["description"]]).lower()
        # Every term must match somewhere; matches in the name count extra.
        score = 0
        for options in terms:
            if not any(option in haystack for option in options):
                break
            score += 1 + 2 * any(option in name for option in options)
        else:
            scored.append((score, summary))

    scored.sort(key=lambda item: (-item[0], -item[1].total_stock))
    ranked = [summary for _, summary in scored]
    return ranked if limit is None else ranked[: max(1, limit)]


def _name_has_all_terms(name: str, terms: list[list[str]]) -> bool:
    name = name.lower()
    return bool(terms) and all(any(option in name for option in options) for options in terms)


def _fallback_suggestions(text: str, limit: int = 3) -> list[ProductSummary]:
    """In-stock products of the same kind the shopper named ("unicorn hoodie" -> hoodies), else best sellers."""
    for word in re.findall(r"[a-z-]+", text.lower()):
        options = _term_options(word)
        if any(o in ("hoodie", "hooded", "crewneck", "t-shirt", "quarter-zip", "jacket", "fleece", "tee") for o in options):
            if hits := _search(word, in_stock_only=True, limit=limit):
                return hits
    return _search("", in_stock_only=True, limit=limit)


def _resolve(conn: sqlite3.Connection, product: str) -> sqlite3.Row | NeedsClarification | LookupFailed:
    """Find ONE catalogue row: exact product_id, exact name, or a name that clearly fits only one product."""
    text = product.strip()
    row = conn.execute("SELECT * FROM catalogue WHERE product_id = ?", (text.lower(),)).fetchone()
    row = row or conn.execute("SELECT * FROM catalogue WHERE lower(name) = ?", (text.lower(),)).fetchone()
    if row:
        return row
    matches = _search(text, in_stock_only=False, limit=None)
    if not matches:
        return LookupFailed(
            error=f"Campus Customs doesn't have a product matching {product!r}. Say so, and offer these in-stock suggestions.",
            suggestions=_fallback_suggestions(text),
        )
    # Clear winner: exactly one product has every word of the request in its own name.
    terms = _query_terms(text)
    named = [m for m in matches if _name_has_all_terms(m.name, terms)]
    pick = matches[0] if len(matches) == 1 else (named[0] if len(named) == 1 else None)
    if pick:
        return conn.execute("SELECT * FROM catalogue WHERE product_id = ?", (pick.product_id,)).fetchone()
    return NeedsClarification(
        asked_for=product,
        total_matches=len(matches),
        candidates=(named or matches)[:4],
        instruction=(
            "Several real products fit this. Don't pick one. Ask the shopper which they mean in one short question, "
            "and put 2-4 of these candidates' product_ids in clarification_options."
        ),
    )


def _record_suggestions(log: LookupLog, failed: LookupFailed | NeedsClarification) -> LookupFailed | NeedsClarification:
    for suggestion in failed.suggestions if isinstance(failed, LookupFailed) else failed.candidates:
        log.record_price(suggestion.price)
        log.record_quantities(suggestion.total_stock)
    return failed


def _alternatives(conn: sqlite3.Connection, row: sqlite3.Row, size: str | None, limit: int = 3) -> list[Alternative]:
    """Similar products (same category) that have stock in `size` (or any size), best match first."""
    category = category_of(row["garment_type"])
    colors = {c.lower() for c in json.loads(row["colors"])}
    tags = {t.lower() for t in json.loads(row["search_tags"])}
    stock: dict[str, dict[str, int]] = {}
    for r in conn.execute("SELECT product_id, size, quantity FROM inventory"):
        stock.setdefault(r["product_id"], {})[r["size"]] = r["quantity"]

    scored = []
    for other in conn.execute("SELECT * FROM catalogue WHERE product_id != ?", (row["product_id"],)):
        if category_of(other["garment_type"]) != category:
            continue
        sizes = stock.get(other["product_id"], {})
        quantity = sizes.get(size, 0) if size else sum(sizes.values())
        if quantity == 0:
            continue
        shared_colors = colors & {c.lower() for c in json.loads(other["colors"])}
        shared_tags = tags & {t.lower() for t in json.loads(other["search_tags"])}
        reason = f"also a {category}" + (f", also {sorted(shared_colors)[0]}" if shared_colors else "")
        scored.append((2 * len(shared_colors) + len(shared_tags), quantity, other, reason))

    scored.sort(key=lambda item: (-item[0], -item[1]))
    return [
        Alternative(
            product_id=other["product_id"],
            name=other["name"],
            price=other["price"],
            size=size or "any",
            quantity_in_size=quantity,
            why_similar=reason,
        )
        for _, quantity, other, reason in scored[:limit]
    ]


def _record_alternatives(log: LookupLog, alternatives: list[Alternative]) -> list[Alternative]:
    for alt in alternatives:
        log.record_price(alt.price)
        log.record_quantities(alt.quantity_in_size)
    return alternatives


# ---------- Agent tools ----------


def search_products(
    ctx: RunContext[LookupLog], query: str, max_price: float | None = None, in_stock_only: bool = True, limit: int = 6
) -> SearchResults:
    """Find products by keywords like garment type, color, college or theme. Use this first to get product_id values.

    Args:
        query: Shopper's words, e.g. "navy hoodie", "the game", "branford quarter zip". Use "" to browse everything.
        max_price: Optional price ceiling in US dollars.
        in_stock_only: Skip products with zero stock in every size.
        limit: Maximum number of products to return (1-10).
    """
    ctx.deps.searches += 1
    if ctx.deps.searches > MAX_SEARCHES_PER_MESSAGE:
        return SearchResults(
            query=query,
            total_matches=0,
            products=[],
            note="Search limit reached for this message. Stop searching and answer with the results you already have.",
        )

    matches = _search(query, max_price, in_stock_only, limit=None)
    results = matches[: max(1, min(limit, 10))]
    if matches:
        # Remember every match for the website's result grid (agent.py reads this after the run).
        ctx.deps.last_search_query = query
        ctx.deps.last_search_ids = [m.product_id for m in matches[:MAX_PAGE_RESULTS]]
        # "We have 27 available" is a match count, so the reply check must allow it.
        ctx.deps.record_quantities(len(matches))
    suggestions: list[ProductSummary] = []
    note = None
    if not results:
        # Offer real, well-stocked items so the model has something true to suggest instead of searching again.
        suggestions = [p for p in _fallback_suggestions(query) if max_price is None or p.price <= max_price][:3]
        note = (
            f"Nothing in the catalogue matches {query!r}. Campus Customs only carries {CATEGORIES_WE_CARRY}. "
            "Do not search again with other wording; tell the shopper we don't have it and offer the suggestions."
        )
    for result in results + suggestions:
        ctx.deps.record_price(result.price)
        ctx.deps.record_quantities(result.total_stock)
    # The model only sees the top few products, so give it the true range over every match.
    low = min((m.price for m in matches), default=None)
    high = max((m.price for m in matches), default=None)
    for bound in (low, high):
        if bound is not None:
            ctx.deps.record_price(bound)
    return SearchResults(
        query=query,
        total_matches=len(matches),
        min_price=low,
        max_price=high,
        products=results,
        note=note,
        suggestions=suggestions,
    )


def get_product_info(ctx: RunContext[LookupLog], product: str) -> ProductInfo | NeedsClarification | LookupFailed:
    """Get the full description, garment type and colors of one product.

    Args:
        product: A product_id from search_products (preferred) or the product's exact name.
    """
    with closing(_connect()) as conn:
        row = _resolve(conn, product)
    if isinstance(row, (LookupFailed, NeedsClarification)):
        return _record_suggestions(ctx.deps, row)
    return ProductInfo(
        product_id=row["product_id"],
        name=row["name"],
        garment_type=row["garment_type"],
        colors=json.loads(row["colors"]),
        description=row["description"],
    )


def get_price(ctx: RunContext[LookupLog], product: str) -> PriceLookup | NeedsClarification | LookupFailed:
    """Get the current price of one product. Call this before stating any price.

    Args:
        product: A product_id from search_products (preferred) or the product's exact name.
    """
    with closing(_connect()) as conn:
        row = _resolve(conn, product)
    if isinstance(row, (LookupFailed, NeedsClarification)):
        return _record_suggestions(ctx.deps, row)
    ctx.deps.record_price(row["price"])
    return PriceLookup(product_id=row["product_id"], name=row["name"], price=row["price"])


def get_stock(ctx: RunContext[LookupLog], product: str) -> StockLookup | NeedsClarification | LookupFailed:
    """Get stock for every size of one product: total units, per-size quantities, and which sizes are sold out.

    Args:
        product: A product_id from search_products (preferred) or the product's exact name.
    """
    with closing(_connect()) as conn:
        row = _resolve(conn, product)
        if isinstance(row, (LookupFailed, NeedsClarification)):
            return _record_suggestions(ctx.deps, row)
        sizes = _sizes_for(conn, row["product_id"])
        total = sum(s.quantity for s in sizes)
        alternatives = _alternatives(conn, row, None) if total == 0 else []
    ctx.deps.record_quantities(total, *(s.quantity for s in sizes))
    _record_alternatives(ctx.deps, alternatives)
    return StockLookup(
        product_id=row["product_id"],
        name=row["name"],
        total_stock=total,
        sizes=sizes,
        available_sizes=[s.size for s in sizes if s.in_stock],
        sold_out_sizes=[s.size for s in sizes if not s.in_stock],
        alternatives=alternatives,
    )


def check_size_stock(ctx: RunContext[LookupLog], product: str, size: str) -> SizeStockLookup | NeedsClarification | LookupFailed:
    """Check stock for one specific size of one product. Use whenever the shopper names a size.

    Args:
        product: A product_id from search_products (preferred) or the product's exact name.
        size: The shopper's size, e.g. "M", "medium", "xl", "2XL".
    """
    normalized = normalize_size(size)
    if normalized is None:
        return LookupFailed(error=f"{size!r} isn't a size we carry. Sizes are {', '.join(SIZE_ORDER)}.")
    with closing(_connect()) as conn:
        row = _resolve(conn, product)
        if isinstance(row, (LookupFailed, NeedsClarification)):
            return _record_suggestions(ctx.deps, row)
        sizes = _sizes_for(conn, row["product_id"])
        match = next((s for s in sizes if s.size == normalized), None)
        quantity = match.quantity if match else 0
        # Sold out in this size: find similar products that do have it, so the shopper isn't left at a dead end.
        alternatives = _alternatives(conn, row, normalized) if quantity == 0 else []
    ctx.deps.record_quantities(quantity)
    _record_alternatives(ctx.deps, alternatives)
    return SizeStockLookup(
        product_id=row["product_id"],
        name=row["name"],
        size=normalized,
        quantity=quantity,
        in_stock=quantity > 0,
        other_available_sizes=[s.size for s in sizes if s.in_stock and s.size != normalized],
        alternatives=alternatives,
    )


AGENT_TOOLS = [search_products, get_product_info, get_price, get_stock, check_size_stock]


def product_cards(product_ids: list[str]) -> list[ProductCard]:
    """Not an agent tool: turns the agent's recommended ids into cards, dropping any id not in the catalogue."""
    unique_ids = list(dict.fromkeys(product_ids))
    if not unique_ids:
        return []
    with closing(_connect()) as conn:
        placeholders = ",".join("?" * len(unique_ids))
        rows = {r["product_id"]: r for r in conn.execute(f"SELECT * FROM catalogue WHERE product_id IN ({placeholders})", unique_ids)}
        totals = _total_stock_by_product(conn)
    return [
        ProductCard(
            product_id=pid,
            name=rows[pid]["name"],
            price=rows[pid]["price"],
            image_url=f"/media/products/{Path(rows[pid]['image_file_path']).name}",
            total_stock=totals.get(pid, 0),
        )
        for pid in unique_ids
        if pid in rows
    ]


def search_results_payload(query: str, product_ids: list[str]) -> ChatSearchResults:
    """Not an agent tool: builds the page's result grid from the ids search_products recorded, fresh from the DB."""
    with closing(_connect()) as conn:
        placeholders = ",".join("?" * len(product_ids))
        rows = {r["product_id"]: r for r in conn.execute(f"SELECT * FROM catalogue WHERE product_id IN ({placeholders})", product_ids)}
        totals = _total_stock_by_product(conn)
    matches = [
        ProductMatch(
            product_id=pid,
            name=rows[pid]["name"],
            garment_type=rows[pid]["garment_type"],
            price=rows[pid]["price"],
            image_url=f"/media/products/{Path(rows[pid]['image_file_path']).name}",
            short_description=_short(rows[pid]["description"], 110),
            colors=json.loads(rows[pid]["colors"]),
            total_stock=totals.get(pid, 0),
        )
        for pid in product_ids
        if pid in rows
    ]
    return ChatSearchResults(query=query, total_matches=len(matches), products=matches)


def find_product_name(product_id: str) -> str | None:
    """Not an agent tool: the catalogue name for an exact product_id, or None."""
    with closing(_connect()) as conn:
        row = conn.execute("SELECT name FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()
    return row["name"] if row else None
