"""Sync CRUD over the sessions/turns tables.

Routers wrap each call with `await asyncio.to_thread(...)` so we don't block
the FastAPI event loop on SQLite I/O. All write helpers serialize JSON
payloads in-place before commit.

Identifier scheme:
  - session id: `s_<hex8>`
  - turn id:    `t_<hex8>`

`create_session` allocates a session row plus its first (seq=0) turn in one
transaction so the FE always gets a turn_id back from the seed call.
"""

from __future__ import annotations

import json
import secrets
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound

from app.storage.db import SessionLocal
from app.storage.models import Session, Turn


# ---------- id helpers ----------

def new_session_id() -> str:
    return f"s_{secrets.token_hex(4)}"


def new_turn_id() -> str:
    return f"t_{secrets.token_hex(4)}"


# ---------- JSON helpers ----------

def _dump(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, default=_json_default)


def _json_default(o: Any) -> Any:
    # Pydantic models
    if hasattr(o, "model_dump"):
        return o.model_dump(by_alias=False)
    if hasattr(o, "dict"):
        return o.dict()
    raise TypeError(f"unserializable type: {type(o)!r}")


def _load(text: str | None, default: Any) -> Any:
    if not text:
        return default
    try:
        return json.loads(text)
    except Exception:
        return default


# ---------- create / append ----------

def create_session(
    *,
    track: str,
    title: str,
    domains: list[str],
    keywords: list[str],
    material_ids: list[str],
    seed_question: str,
    seed_domain_label: str,
    seed_citations: list[dict[str, Any]] | None = None,
    user_id: str | None = None,
) -> tuple[str, str]:
    """Insert a new session + its seed turn (seq=0). Returns (session_id, turn_id)."""
    sid = new_session_id()
    tid = new_turn_id()
    now = time.time()

    with SessionLocal() as s:
        sess = Session(
            id=sid,
            user_id=user_id,
            track=track,
            title=(title or seed_question or "")[:200],
            domains_json=_dump(domains),
            keywords_json=_dump(keywords),
            material_ids_json=_dump(material_ids),
            created_at=now,
            updated_at=now,
            last_score=None,
        )
        seed_turn = Turn(
            id=tid,
            session_id=sid,
            seq=0,
            level="",
            source="seed",
            domain_label=seed_domain_label,
            question=seed_question,
            rationale="",
            answer=None,
            notes_json="[]",
            follow_ups_json="[]",
            retrieved_context_json="[]",
            citations_json=_dump(seed_citations or []),
            answer_quality="",
            explanation="",
            question_intent="",
            score=None,
            thread_id=None,
            created_at=now,
        )
        s.add(sess)
        s.add(seed_turn)
        s.commit()

    return sid, tid


def append_turn(
    *,
    session_id: str,
    question: str,
    domain_label: str = "",
    level: str = "",
    source: str = "",
    rationale: str = "",
    citations: list[dict[str, Any]] | None = None,
    thread_id: str | None = None,
) -> str:
    """Insert an empty turn (no answer yet) appended after the session's max seq.

    Used when the BE pre-allocates the next follow-up turn so the FE can later
    submit the user's answer against a known turn_id.
    """
    tid = new_turn_id()
    now = time.time()

    with SessionLocal() as s:
        # Confirm session exists, then compute next seq.
        sess = s.get(Session, session_id)
        if sess is None:
            raise NoResultFound(f"session not found: {session_id}")

        max_seq = s.execute(
            select(Turn.seq).where(Turn.session_id == session_id).order_by(Turn.seq.desc()).limit(1)
        ).scalar()
        next_seq = (max_seq + 1) if max_seq is not None else 0

        turn = Turn(
            id=tid,
            session_id=session_id,
            seq=next_seq,
            level=level,
            source=source,
            domain_label=domain_label,
            question=question,
            rationale=rationale,
            answer=None,
            notes_json="[]",
            follow_ups_json="[]",
            retrieved_context_json="[]",
            citations_json=_dump(citations or []),
            answer_quality="",
            explanation="",
            question_intent="",
            score=None,
            thread_id=thread_id,
            created_at=now,
        )
        sess.updated_at = now
        s.add(turn)
        s.commit()

    return tid


# ---------- cleanup orphan turns ----------

def delete_trailing_unanswered_turn(session_id: str) -> bool:
    """Remove the session's last turn iff it has no answer.

    Used when /sessions/seed is called on an existing session — the previous
    /sessions submit pre-allocated a follow-up turn (the BE's first candidate)
    so FE could submit against a known turn_id, but FE may have decided to
    pivot to a fresh seed instead (e.g., uncertain/incorrect answer triggers a
    domain switch). Without this cleanup the orphan follow-up survives in DB
    and surfaces in analysis history as a question the user never saw.

    Returns True when a turn was deleted.
    """
    with SessionLocal() as s:
        last = s.execute(
            select(Turn)
            .where(Turn.session_id == session_id)
            .order_by(Turn.seq.desc())
            .limit(1)
        ).scalar_one_or_none()
        if last is None or last.answer is not None:
            return False
        s.delete(last)
        s.commit()
    return True


# ---------- record answer (idempotent) ----------

def record_answer(
    *,
    session_id: str,
    turn_id: str,
    answer: str,
    notes: list[Any],
    follow_ups: list[Any],
    retrieved_context: list[Any],
    citations: list[Any],
    answer_quality: str,
    explanation: str,
    question_intent: str,
    score: int | None,
    thread_id: str | None,
) -> None:
    """Update an existing turn with answer + analysis + follow-ups + score.

    Idempotent: re-calling with the same turn_id overwrites prior values
    (used by /sessions/{thread_id}/feedback when the graph regenerates).
    """
    now = time.time()

    with SessionLocal() as s:
        turn = s.get(Turn, turn_id)
        if turn is None or turn.session_id != session_id:
            raise NoResultFound(
                f"turn not found in session: session={session_id} turn={turn_id}"
            )

        turn.answer = answer
        turn.notes_json = _dump(notes)
        turn.follow_ups_json = _dump(follow_ups)
        turn.retrieved_context_json = _dump(retrieved_context)
        turn.citations_json = _dump(citations)
        turn.answer_quality = answer_quality or ""
        turn.explanation = explanation or ""
        turn.question_intent = question_intent or ""
        turn.score = score
        if thread_id:
            turn.thread_id = thread_id

        sess = s.get(Session, session_id)
        if sess is not None:
            sess.updated_at = now
            if score is not None:
                sess.last_score = score

        s.commit()


# ---------- read ----------

def list_sessions(
    limit: int = 50,
    user_id: str | None = None,
) -> list[dict[str, Any]]:
    """Return sessions ordered by updated_at desc with a small derived header.

    If `user_id` is given, only that user's rows are returned. If None, returns
    all rows (kept for back-compat with admin/maintenance flows).
    """
    with SessionLocal() as s:
        stmt = select(Session).order_by(Session.updated_at.desc()).limit(limit)
        if user_id is not None:
            stmt = (
                select(Session)
                .where(Session.user_id == user_id)
                .order_by(Session.updated_at.desc())
                .limit(limit)
            )
        rows = s.execute(stmt).scalars().all()

        out: list[dict[str, Any]] = []
        for sess in rows:
            turn_count = s.execute(
                select(Turn.id).where(Turn.session_id == sess.id)
            ).all()
            out.append(
                {
                    "id": sess.id,
                    "user_id": sess.user_id,
                    "track": sess.track,
                    "title": sess.title,
                    "domains": _load(sess.domains_json, []),
                    "keywords": _load(sess.keywords_json, []),
                    "material_ids": _load(sess.material_ids_json, []),
                    "turn_count": len(turn_count),
                    "last_score": sess.last_score,
                    "created_at": sess.created_at,
                    "updated_at": sess.updated_at,
                }
            )
        return out


def update_session_title(session_id: str, title: str) -> bool:
    """Update only `title` (and updated_at) for one session. Returns True if found."""
    with SessionLocal() as s:
        sess = s.get(Session, session_id)
        if sess is None:
            return False
        sess.title = (title or "")[:200]
        sess.updated_at = time.time()
        s.commit()
        return True


def get_session(session_id: str) -> dict[str, Any] | None:
    """Return a session header + ordered list of turns, or None if missing."""
    with SessionLocal() as s:
        sess = s.get(Session, session_id)
        if sess is None:
            return None

        turn_rows = s.execute(
            select(Turn).where(Turn.session_id == session_id).order_by(Turn.seq.asc())
        ).scalars().all()

        turns = [
            {
                "id": t.id,
                "seq": t.seq,
                "level": t.level,
                "source": t.source,
                "domain_label": t.domain_label,
                "question": t.question,
                "rationale": t.rationale,
                "answer": t.answer,
                "notes": _load(t.notes_json, []),
                "follow_ups": _load(t.follow_ups_json, []),
                "retrieved_context": _load(t.retrieved_context_json, []),
                "citations": _load(t.citations_json, []),
                "answer_quality": t.answer_quality or "",
                "explanation": t.explanation or "",
                "question_intent": t.question_intent or "",
                "score": t.score,
                "thread_id": t.thread_id,
                "created_at": t.created_at,
            }
            for t in turn_rows
        ]

        return {
            "id": sess.id,
            "user_id": sess.user_id,
            "track": sess.track,
            "title": sess.title,
            "domains": _load(sess.domains_json, []),
            "keywords": _load(sess.keywords_json, []),
            "material_ids": _load(sess.material_ids_json, []),
            "turn_count": len(turns),
            "last_score": sess.last_score,
            "created_at": sess.created_at,
            "updated_at": sess.updated_at,
            "turns": turns,
        }


def delete_session(session_id: str) -> bool:
    """Delete a session row + cascading turns. Returns True if deleted."""
    with SessionLocal() as s:
        sess = s.get(Session, session_id)
        if sess is None:
            return False
        s.delete(sess)
        s.commit()
        return True
