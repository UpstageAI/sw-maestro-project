"""Sync CRUD over the `users` table.

Routers wrap each call with `await asyncio.to_thread(...)` so we don't block
the FastAPI event loop on SQLite I/O. Mirrors the pattern in `session_store`.

Identifier scheme:
  - user id: 32-char hex (`uuid.uuid4().hex`)

Password storage uses bcrypt cost=12. Email is stored lower-cased and is the
unique key; lookups are case-insensitive on the input side.

Orphan-session claim:
  When a user registers with email "alice@x.com" and we observe pre-existing
  `sessions.user_id == "alice@x.com"` rows (or any legacy cookie value the
  caller provides), `claim_orphan_sessions(new_user_id, legacy_user_id_string)`
  reassigns those rows to the freshly minted user id. Returns rowcount.
"""

from __future__ import annotations

import time
import uuid
from typing import Any

import bcrypt
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.storage.db import SessionLocal
from app.storage.models import Session as SessionRow
from app.storage.models import User


# ---------- id helpers ----------

def _new_user_id() -> str:
    return uuid.uuid4().hex


# ---------- password helpers ----------

def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(12)).decode("utf-8")


def verify_password(user: dict, password: str) -> bool:
    """Compare plaintext against the user's stored bcrypt hash."""
    stored = (user or {}).get("password_hash") or ""
    if not stored:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), stored.encode("utf-8"))
    except ValueError:
        # Malformed hash on disk — treat as auth failure rather than 500.
        return False


# ---------- row → dict ----------

def _user_to_dict(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "email": user.email,
        "password_hash": user.password_hash,
        "display_name": user.display_name,
        "legacy_user_id": user.legacy_user_id,
        "created_at": user.created_at,
    }


# ---------- create / read ----------

def create_user(
    email: str,
    password: str,
    display_name: str | None = None,
) -> dict[str, Any]:
    """Insert a new user. Email is normalized to lowercase.

    Raises ValueError("이미 가입된 이메일입니다.") on uniqueness violation.
    """
    normalized_email = (email or "").strip().lower()
    uid = _new_user_id()
    now = time.time()

    user = User(
        id=uid,
        email=normalized_email,
        password_hash=_hash_password(password),
        display_name=(display_name or None),
        legacy_user_id=None,
        created_at=now,
    )
    try:
        with SessionLocal() as s:
            s.add(user)
            s.commit()
            s.refresh(user)
            return _user_to_dict(user)
    except IntegrityError as exc:
        raise ValueError("이미 가입된 이메일입니다.") from exc


def get_by_email(email: str) -> dict[str, Any] | None:
    """Case-insensitive lookup by email."""
    normalized = (email or "").strip().lower()
    if not normalized:
        return None
    with SessionLocal() as s:
        row = s.execute(
            select(User).where(User.email == normalized)
        ).scalar_one_or_none()
        return _user_to_dict(row) if row is not None else None


def get_by_id(user_id: str) -> dict[str, Any] | None:
    if not user_id:
        return None
    with SessionLocal() as s:
        row = s.get(User, user_id)
        return _user_to_dict(row) if row is not None else None


def get_by_legacy_user_id(legacy: str) -> dict[str, Any] | None:
    """Find the stub User created by migrate_users.py for a legacy user_id."""
    if not legacy:
        return None
    with SessionLocal() as s:
        row = s.execute(
            select(User).where(User.legacy_user_id == legacy)
        ).scalar_one_or_none()
        return _user_to_dict(row) if row is not None else None


def clear_legacy_marker(user_id: str) -> None:
    """Null out `legacy_user_id` on a User row after its sessions are claimed.

    Prevents repeated /auth/claim calls from re-routing through the stub row.
    """
    if not user_id:
        return
    with SessionLocal() as s:
        s.execute(
            update(User).where(User.id == user_id).values(legacy_user_id=None)
        )
        s.commit()


# ---------- claim orphan sessions ----------

def claim_orphan_sessions(new_user_id: str, legacy_user_id_string: str) -> int:
    """Reassign sessions whose user_id == legacy_user_id_string to new_user_id.

    Used right after register/login so a user keeps their pre-account history
    when they previously identified by email or by the legacy "userId-<rand>"
    cookie. Returns affected rowcount.
    """
    if not new_user_id or not legacy_user_id_string:
        return 0
    if new_user_id == legacy_user_id_string:
        return 0
    with SessionLocal() as s:
        result = s.execute(
            update(SessionRow)
            .where(SessionRow.user_id == legacy_user_id_string)
            .values(user_id=new_user_id)
        )
        s.commit()
        return result.rowcount or 0
