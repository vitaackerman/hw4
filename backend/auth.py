"""Create-account and login endpoints backed by the existing `users` table."""

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field, field_validator

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "campus_customs.db"

# Must match the seed data: "pbkdf2_sha256$<salt>$<hex digest>", salt used as UTF-8 text.
HASH_ALGORITHM = "pbkdf2_sha256"
HASH_ITERATIONS = 120_000
MIN_PASSWORD_LENGTH = 8
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
SESSION_TTL_SECONDS = 7 * 24 * 3600
SECRET_FILE = Path(__file__).resolve().parent / ".session_secret"

router = APIRouter(prefix="/api/auth", tags=["auth"])


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), HASH_ITERATIONS).hex()
    return f"{HASH_ALGORITHM}${salt}${digest}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, salt, _ = stored_hash.split("$")
    except ValueError:
        return False
    if algorithm != HASH_ALGORITHM:
        return False
    return hmac.compare_digest(hash_password(password, salt), stored_hash)


# Checked against when the email doesn't exist, so response time doesn't reveal which emails are registered.
_DUMMY_HASH = hash_password(secrets.token_hex(16))


class PublicUser(BaseModel):
    """The only user shape ever sent to the frontend. No password hash or salt."""

    id: int
    first_name: str
    last_name: str
    name: str
    email: str
    created_at: str


class AuthResponse(BaseModel):
    """Login/signup response: the public profile plus a signed session token for later requests."""

    user: PublicUser
    token: str


class RegisterRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    email: str = Field(max_length=254)
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=128)

    @field_validator("first_name", "last_name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("can't be blank")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not EMAIL_PATTERN.match(value):
            raise ValueError("isn't a valid email address")
        return value


class LoginRequest(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


# ---------- Session tokens ----------
# Stateless: "<base64 payload>.<base64 HMAC-SHA256>", payload = {"uid": <users.id>, "exp": <unix time>}.
# The server trusts only the user id inside a token it signed, never an id sent by the browser.


def _load_secret() -> bytes:
    if env_secret := os.getenv("SESSION_SECRET"):
        return env_secret.encode()
    if not SECRET_FILE.exists():
        # Generated once and kept (gitignored) so --reload restarts don't log everyone out.
        SECRET_FILE.write_text(secrets.token_hex(32))
        SECRET_FILE.chmod(0o600)
    return SECRET_FILE.read_text().strip().encode()


_SECRET = _load_secret()


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def create_session_token(user_id: int) -> str:
    payload = _b64(json.dumps({"uid": user_id, "exp": int(time.time()) + SESSION_TTL_SECONDS}).encode())
    signature = _b64(hmac.new(_SECRET, payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{signature}"


def read_session_token(token: str) -> int | None:
    """Returns the user id if the token is ours, untampered and unexpired; otherwise None."""
    try:
        payload, signature = token.split(".")
        expected = _b64(hmac.new(_SECRET, payload.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            return None
        data = json.loads(_unb64(payload))
        return int(data["uid"]) if data["exp"] > time.time() else None
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def to_public_user(row: sqlite3.Row) -> PublicUser:
    # Older rows may lack first/last name, so fall back to splitting the full name.
    first, _, last = row["name"].partition(" ")
    return PublicUser(
        id=row["id"],
        first_name=row["first_name"] or first,
        last_name=row["last_name"] or last,
        name=row["name"],
        email=row["email"],
        created_at=row["created_at"],
    )


def get_user(user_id: int) -> PublicUser | None:
    with closing(connect()) as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return to_public_user(row) if row else None


def optional_user(authorization: Annotated[str | None, Header()] = None) -> PublicUser | None:
    """FastAPI dependency: the logged-in user from 'Authorization: Bearer <token>', or None for guests.

    A token that is present but invalid or expired is a 401, so the frontend can log the user out.
    """
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    user_id = read_session_token(token) if scheme.lower() == "bearer" else None
    user = get_user(user_id) if user_id is not None else None
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Your session has expired. Please log in again.")
    return user


def required_user(user: Annotated[PublicUser | None, Depends(optional_user)]) -> PublicUser:
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Please log in first.")
    return user


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=AuthResponse)
def register(body: RegisterRequest) -> AuthResponse:
    with closing(connect()) as conn:
        if conn.execute("SELECT 1 FROM users WHERE lower(email) = ?", (body.email,)).fetchone():
            raise HTTPException(status.HTTP_409_CONFLICT, "An account with that email already exists. Try logging in.")
        try:
            with conn:
                cursor = conn.execute(
                    "INSERT INTO users (name, email, password_hash, first_name, last_name) VALUES (?, ?, ?, ?, ?)",
                    (
                        f"{body.first_name} {body.last_name}",
                        body.email,
                        hash_password(body.password),
                        body.first_name,
                        body.last_name,
                    ),
                )
        except sqlite3.IntegrityError:
            # Another request registered the same email between the check and the insert.
            raise HTTPException(status.HTTP_409_CONFLICT, "An account with that email already exists. Try logging in.")
        row = conn.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return AuthResponse(user=to_public_user(row), token=create_session_token(row["id"]))


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest) -> AuthResponse:
    with closing(connect()) as conn:
        row = conn.execute("SELECT * FROM users WHERE lower(email) = ?", (body.email,)).fetchone()
    if not verify_password(body.password, row["password_hash"] if row else _DUMMY_HASH) or row is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.")
    return AuthResponse(user=to_public_user(row), token=create_session_token(row["id"]))
