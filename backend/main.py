"""Campus Customs API: catalogue data, product images, accounts and the chat agent."""

import json
import logging
import sqlite3
import threading
from contextlib import closing
from pathlib import Path

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from agent import ChatNotConfigured, run_chat
from auth import PublicUser, optional_user, required_user
from auth import router as auth_router
from chat_store import agent_memory, load_history, save_exchange
from cutouts import CACHE_DIR as CUTOUT_CACHE
from cutouts import cutout_path, warm_cache
from models import ChatHistory, ChatReply, ChatRequest, CustomerContext

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "campus_customs.db"
SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]

app = FastAPI(title="Campus Customs API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],  # includes Authorization for session tokens
)
# Only data/products is exposed, so the database file itself is never served.
app.mount("/media/products", StaticFiles(directory=DATA_DIR / "products"), name="media")
app.include_router(auth_router)

# Build any missing product cutouts in the background so the first page load doesn't wait for them.
threading.Thread(target=warm_cache, daemon=True, name="cutout-cache").start()


@app.get("/media/cutouts/{stem}.webp")
def product_cutout(stem: str) -> FileResponse:
    """Transparent product cutout; 404 means 'use the original photo' (see cutouts.py)."""
    path = cutout_path(stem)
    if path is None:
        raise HTTPException(status_code=404, detail="No cutout for this product")
    return FileResponse(path, media_type="image/webp", headers={"Cache-Control": "public, max-age=86400"})

logger = logging.getLogger("campus_customs")

FIELD_LABELS = {
    "first_name": "First name",
    "last_name": "Last name",
    "email": "Email",
    "password": "Password",
    "message": "Message",
}


@app.exception_handler(RequestValidationError)
async def readable_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    # Turn Pydantic's error list into one sentence the frontend can show as-is.
    error = exc.errors()[0]
    field = FIELD_LABELS.get(str(error["loc"][-1]), "Input")
    if error["type"] == "string_too_short" and error["ctx"]["min_length"] == 1:
        message = f"{field} is required."
    elif error["type"] == "string_too_short":
        message = f"{field} must be at least {error['ctx']['min_length']} characters."
    elif error["type"] == "string_too_long":
        message = f"{field} must be at most {error['ctx']['max_length']} characters."
    elif error["type"] == "value_error":
        message = f"{field} {str(error['ctx']['error'])}."
    else:
        message = f"{field} is missing or invalid."
    return JSONResponse(status_code=422, content={"detail": message})


def connect() -> sqlite3.Connection:
    # Read-only: catalogue endpoints never modify the database (only auth.py writes, to users).
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def product_from_row(row: sqlite3.Row, inventory: list[dict]) -> dict:
    return {
        "product_id": row["product_id"],
        "name": row["name"],
        "garment_type": row["garment_type"],
        "description": row["description"],
        "colors": json.loads(row["colors"]),
        "search_tags": json.loads(row["search_tags"]),
        "price": row["price"],
        "image_url": f"/media/products/{Path(row['image_file_path']).name}",
        # False only when the cutout failed its quality check; the frontend then shows the photo.
        "has_cutout": not (CUTOUT_CACHE / f"{Path(row['image_file_path']).stem}.skip").exists(),
        "inventory": inventory,
        "total_stock": sum(item["quantity"] for item in inventory),
    }


def load_inventory(conn: sqlite3.Connection) -> dict[str, list[dict]]:
    by_product: dict[str, list[dict]] = {}
    for row in conn.execute("SELECT product_id, size, quantity FROM inventory"):
        by_product.setdefault(row["product_id"], []).append(
            {"size": row["size"], "quantity": row["quantity"]}
        )
    for sizes in by_product.values():
        sizes.sort(key=lambda s: SIZE_ORDER.index(s["size"]) if s["size"] in SIZE_ORDER else len(SIZE_ORDER))
    return by_product


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/products")
def list_products() -> list[dict]:
    with closing(connect()) as conn:
        inventory = load_inventory(conn)
        rows = conn.execute("SELECT * FROM catalogue ORDER BY name").fetchall()
    return [product_from_row(row, inventory.get(row["product_id"], [])) for row in rows]


@app.get("/api/products/{product_id}")
def get_product(product_id: str) -> dict:
    with closing(connect()) as conn:
        row = conn.execute("SELECT * FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Product not found")
        inventory = load_inventory(conn).get(product_id, [])
    return product_from_row(row, inventory)


@app.post("/api/chat", response_model=ChatReply)
async def chat(body: ChatRequest, user: Annotated[PublicUser | None, Depends(optional_user)]) -> ChatReply:
    customer = None
    history = body.history
    if user:
        customer = CustomerContext(
            first_name=user.first_name, last_name=user.last_name, email=user.email, member_since=user.created_at
        )
        # Logged-in memory comes from the database, not from whatever history the browser sends.
        history = agent_memory(user.id)
    try:
        reply = await run_chat(
            body.message, history, customer=customer, page=body.page, customer_id=user.id if user else None
        )
    except ChatNotConfigured as exc:
        logger.error("Chat is not configured: %s", exc)
        raise HTTPException(status_code=503, detail="The chat assistant isn't set up yet. Please try again later.")
    except Exception:
        # Model, network or Portkey failures: log the details here, send the shopper a friendly message.
        logger.exception("Chat agent failed")
        raise HTTPException(status_code=502, detail="Sorry, the chat assistant hit a snag. Please try again in a moment.")
    if user:
        save_exchange(user.id, body.message, reply)
    return reply


@app.get("/api/chat/history", response_model=ChatHistory)
def chat_history(user: Annotated[PublicUser, Depends(required_user)]) -> ChatHistory:
    """The logged-in customer's saved chat, oldest first. Only ever their own rows."""
    return ChatHistory(messages=load_history(user.id))
