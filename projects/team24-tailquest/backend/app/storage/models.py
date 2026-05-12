"""SQLAlchemy ORM models for chat session history.

Two tables:
  - sessions: one row per chat session (= FE routing key)
  - turns: one row per (question, optional answer) pair within a session

Mappings:
  - sessions.id 1 ↔ turns.session_id N
  - turns.thread_id is the LangGraph checkpointer key, scoped to that single
    turn — different turns within the same session get distinct thread_ids.
  - JSON columns store list[dict] / list[str] payloads as TEXT (sqlite); we
    serialize/deserialize by hand in session_store.py.
"""

from __future__ import annotations

import time

from sqlalchemy import (
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.storage.db import Base


def _now() -> float:
    return time.time()


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    track: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False, default="")

    # JSON-encoded list[str]
    domains_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    keywords_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    material_ids_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    created_at: Mapped[float] = mapped_column(Float, nullable=False, default=_now)
    updated_at: Mapped[float] = mapped_column(Float, nullable=False, default=_now)
    last_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    turns: Mapped[list["Turn"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Turn.seq",
    )


class Material(Base):
    """RAG ingestion material — md upload, pdf upload, or GitHub markdown crawl.

    Persisted alongside the Chroma collection so the metadata (name, status,
    chunks count, error) survives backend restarts. The Chroma side already
    persists embeddings to disk; this table is the missing piece for the
    materials list UI to show the right status after a reboot.

    Status transitions are owned by the API layer (`app/api/materials.py`):
      - "indexing" — set on POST, the background worker mutates to ready/failed
      - "ready"    — embeddings written, count populated
      - "failed"   — error string explains why; chunks=0
    """

    __tablename__ = "materials"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    # Owner of this material. Nullable so legacy rows (uploaded before the auth
    # refactor) survive — they show up as "orphans" not visible to any user
    # until manually reassigned via SQL or a future claim flow.
    user_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False, default="")
    kind: Mapped[str] = mapped_column(String, nullable=False)  # md | pdf | github
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="indexing"
    )  # indexing | ready | failed
    chunks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[float] = mapped_column(Float, nullable=False, default=_now)
    updated_at: Mapped[float] = mapped_column(Float, nullable=False, default=_now)


class User(Base):
    """Registered user account.

    Independent from `Session.user_id` — that column stays nullable Text with
    no FK so SQLite (no ALTER FK) and existing rows keep working. The link is
    enforced application-side: on login/register we set `Session.user_id`
    to `User.id`. Pre-existing sessions whose `user_id` was the legacy
    "userId-<random>" cookie value can be claimed via
    `user_store.claim_orphan_sessions(new_id, legacy_id)`.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # uuid hex
    email: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    legacy_user_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    created_at: Mapped[float] = mapped_column(Float, nullable=False, default=_now)


class Turn(Base):
    __tablename__ = "turns"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)

    level: Mapped[str] = mapped_column(String, nullable=False, default="")
    source: Mapped[str] = mapped_column(String, nullable=False, default="")
    domain_label: Mapped[str] = mapped_column(String, nullable=False, default="")
    question: Mapped[str] = mapped_column(Text, nullable=False, default="")
    rationale: Mapped[str] = mapped_column(Text, nullable=False, default="")

    answer: Mapped[str | None] = mapped_column(Text, nullable=True)

    # JSON-encoded payloads
    notes_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    follow_ups_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    retrieved_context_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    citations_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    answer_quality: Mapped[str] = mapped_column(String, nullable=False, default="")
    explanation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    question_intent: Mapped[str] = mapped_column(Text, nullable=False, default="")
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    thread_id: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[float] = mapped_column(Float, nullable=False, default=_now)

    session: Mapped[Session] = relationship(back_populates="turns")
