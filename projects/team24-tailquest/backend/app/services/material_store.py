"""SQLite-backed material registry.

Replaces the in-memory `_materials` dict in `app/api/materials.py` so the
status of every uploaded md/pdf/GitHub repo survives a backend restart.

The Chroma collection on disk is the durable embedding side; this module is
the metadata side (id, name, kind, status, chunks, error).

Sync SQLAlchemy — async API routes call these via `asyncio.to_thread`.
"""

from __future__ import annotations

import time
from typing import Any

from sqlalchemy import select

from app.storage.db import SessionLocal
from app.storage.models import Material


def _now() -> float:
    return time.time()


def _to_dict(m: Material) -> dict[str, Any]:
    """Serialize a Material row in the shape MaterialResponse expects."""
    return {
        "id": m.id,
        "user_id": m.user_id,
        "name": m.name,
        "kind": m.kind,
        "status": m.status,
        "chunks": m.chunks,
        "error": m.error,
    }


def list_materials(user_id: str | None = None) -> list[dict[str, Any]]:
    """Newest first so the upload list reads top-down.

    When `user_id` is given, only that user's rows are returned (the API
    layer always passes `current_user["id"]` post-auth-refactor). None means
    "no filter" — used by maintenance scripts only.
    """
    with SessionLocal() as s:
        stmt = select(Material).order_by(Material.created_at.desc())
        if user_id is not None:
            stmt = stmt.where(Material.user_id == user_id)
        rows = s.execute(stmt).scalars().all()
        return [_to_dict(m) for m in rows]


def get_material(material_id: str) -> dict[str, Any] | None:
    """Look up a single row regardless of owner. Ownership check is the
    API layer's responsibility (compare returned `user_id` to current user)."""
    with SessionLocal() as s:
        m = s.get(Material, material_id)
        if m is None:
            return None
        return _to_dict(m)


def create_material(
    *,
    material_id: str,
    name: str,
    kind: str,
    user_id: str,
    status: str = "indexing",
) -> dict[str, Any]:
    now = _now()
    with SessionLocal() as s:
        m = Material(
            id=material_id,
            user_id=user_id,
            name=name,
            kind=kind,
            status=status,
            chunks=0,
            error=None,
            created_at=now,
            updated_at=now,
        )
        s.add(m)
        s.commit()
        return _to_dict(m)


def update_material(
    material_id: str,
    *,
    status: str | None = None,
    chunks: int | None = None,
    error: str | None = None,
) -> dict[str, Any] | None:
    """Idempotent partial update. Returns the new row or None if not found."""
    with SessionLocal() as s:
        m = s.get(Material, material_id)
        if m is None:
            return None
        if status is not None:
            m.status = status
        if chunks is not None:
            m.chunks = chunks
        if error is not None:
            m.error = error
        m.updated_at = _now()
        s.commit()
        return _to_dict(m)


def delete_material(material_id: str) -> bool:
    with SessionLocal() as s:
        m = s.get(Material, material_id)
        if m is None:
            return False
        s.delete(m)
        s.commit()
        return True


def mark_indexing_as_failed(reason: str) -> int:
    """Boot-time recovery: any row stuck in `indexing` from a prior crashed
    process gets flagged as failed. Returns count flipped.

    Without this, the FE would poll forever on rows whose background worker
    died with the previous uvicorn process.
    """
    now = _now()
    with SessionLocal() as s:
        rows = (
            s.execute(select(Material).where(Material.status == "indexing"))
            .scalars()
            .all()
        )
        for m in rows:
            m.status = "failed"
            m.error = reason
            m.updated_at = now
        s.commit()
        return len(rows)
