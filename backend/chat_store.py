"""Saving and reloading logged-in customers' chats in the existing chat_messages table."""

import json
import sqlite3
from contextlib import closing
from pathlib import Path

from pydantic import ValidationError

from models import ChatReply, ChatTurn, HistoryMessage, ProductCard

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "campus_customs.db"
DISPLAY_LIMIT = 50  # messages the widget shows when a customer comes back
AGENT_LIMIT = 20  # most recent messages the agent gets as memory (matches MAX_HISTORY_MESSAGES)


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _cards(products_json: str | None) -> list[ProductCard]:
    # Seed rows store fuller product snapshots; ProductCard keeps only the fields the chat needs.
    cards: list[ProductCard] = []
    for item in json.loads(products_json or "[]"):
        try:
            cards.append(ProductCard.model_validate(item))
        except ValidationError:
            continue
    return cards


def load_history(user_id: int, limit: int = DISPLAY_LIMIT) -> list[HistoryMessage]:
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT * FROM (SELECT * FROM chat_messages WHERE user_id = ? ORDER BY id DESC LIMIT ?) ORDER BY id",
            (user_id, limit),
        ).fetchall()
    return [
        HistoryMessage(
            id=r["id"],
            role=r["role"],
            content=r["content"],
            products=_cards(r["products_json"]),
            created_at=r["created_at"],
        )
        for r in rows
        if r["role"] in ("user", "assistant")
    ]


def agent_memory(user_id: int) -> list[ChatTurn]:
    return [ChatTurn(role=m.role, content=m.content) for m in load_history(user_id, AGENT_LIMIT)]


def save_exchange(user_id: int, message: str, reply: ChatReply) -> None:
    """Store the shopper's message and the agent's reply together (same format as the seed rows)."""
    # Clarification options are saved as the reply's cards so "which one?" still makes sense on reload.
    cards = reply.products or reply.clarification_options
    products_json = json.dumps([card.model_dump() for card in cards])
    with closing(_connect()) as conn, conn:
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'user', ?, NULL)",
            (user_id, message),
        )
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'assistant', ?, ?)",
            (user_id, reply.reply, products_json),
        )
