"""Materials endpoints — RAG ingestion control surface.

Endpoints:
  POST   /materials/upload      — md/pdf upload (sync; one file is fast)
  POST   /materials/github      — start async GitHub repo ingest
  GET    /materials             — list all materials registered in this process
  GET    /materials/{id}        — single material (status polling)
  DELETE /materials/{id}        — drop the per-material Chroma collection

Material metadata is persisted in SQLite (`material_store`) so the status
of every uploaded md/pdf/GitHub repo survives a backend restart. The Chroma
collection on disk is the durable embedding side; this layer is the metadata
side.

On lifespan startup `material_store.mark_indexing_as_failed(...)` flips any
row left in `indexing` status by a previously-crashed process — without that,
the FE would poll forever on a worker that no longer exists.
"""

from __future__ import annotations

import asyncio
import logging
import re
import secrets
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile

from app.auth.deps import current_user
from app.config import get_settings
from app.graph.schema import (
    GithubIngestRequest,
    MaterialKind,
    MaterialResponse,
    MaterialStatus,
)
from app.ingestion.github import fetch_github_md
from app.ingestion.pipeline import parse_md, parse_pdf
from app.services import material_store
from app.storage import chroma

log = logging.getLogger(__name__)

router = APIRouter()


_MAX_MD_BYTES = 1_000_000          # 1MB
_MAX_PDF_BYTES = 10_000_000        # 10MB
_FILENAME_RE = re.compile(r"[^A-Za-z0-9._\-가-힣 ]")


def _new_material_id() -> str:
    return f"mat_{secrets.token_hex(4)}"


def _safe_filename(name: str) -> str:
    """Strip directory components and dangerous characters."""
    base = Path(name).name  # drops any path components
    base = _FILENAME_RE.sub("_", base)
    return base[:200] or "upload"


def _detect_kind(file_name: str) -> MaterialKind | None:
    lower = file_name.lower()
    if lower.endswith(".md") or lower.endswith(".markdown"):
        return "md"
    if lower.endswith(".pdf"):
        return "pdf"
    return None


def _row_to_response(row: dict | None) -> MaterialResponse:
    assert row is not None
    return MaterialResponse(
        id=row["id"],
        name=row["name"],
        kind=row["kind"],
        status=row["status"],
        chunks=row["chunks"],
        error=row.get("error") or "",  # schema requires str, DB stores nullable
    )


# ---------- endpoints ----------

# Materials are now scoped per-user. The DB has a nullable `user_id` column
# (legacy rows from before the scoping refactor have NULL and are invisible
# to all users). Every list/get/delete check ownership; the upload/github
# routes stamp the new row with the caller's user.id.


def _ensure_material_access(material_id: str, user_id: str) -> dict:
    """Load a material and 404 if it doesn't exist OR isn't owned by `user_id`.
    Returning 404 (not 403) on cross-user access avoids leaking the existence
    of other users' material ids."""
    row = material_store.get_material(material_id)
    if row is None or row.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="material을 찾을 수 없습니다.")
    return row


@router.post("/materials/upload", response_model=MaterialResponse)
async def upload_material(
    file: UploadFile,
    user: dict = Depends(current_user),
) -> MaterialResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="filename이 비어 있습니다.")

    kind = _detect_kind(file.filename)
    if kind is None:
        raise HTTPException(status_code=400, detail="md 또는 pdf 파일만 업로드 가능합니다.")

    raw = await file.read()
    limit = _MAX_MD_BYTES if kind == "md" else _MAX_PDF_BYTES
    if len(raw) > limit:
        raise HTTPException(
            status_code=400,
            detail=f"파일 크기 한도 초과 ({kind} 한도: {limit // 1_000_000}MB).",
        )

    safe_name = _safe_filename(file.filename)
    material_id = _new_material_id()
    await asyncio.to_thread(
        material_store.create_material,
        material_id=material_id,
        name=safe_name,
        kind=kind,
        user_id=user["id"],
        status="indexing",
    )

    # Optionally persist the original file to disk for debug/reference.
    settings = get_settings()
    upload_dir = Path(settings.materials_upload_dir)
    try:
        upload_dir.mkdir(parents=True, exist_ok=True)
        (upload_dir / f"{material_id}_{safe_name}").write_bytes(raw)
    except Exception as e:
        log.warning("failed to persist upload to disk: %s", e)

    try:
        if kind == "md":
            chunks = parse_md(raw.decode("utf-8", errors="replace"), safe_name)
        else:
            chunks = parse_pdf(raw, safe_name)
    except Exception as e:
        await asyncio.to_thread(
            material_store.update_material,
            material_id,
            status="failed",
            error=f"파싱 실패: {e}",
        )
        raise HTTPException(status_code=400, detail=f"파싱 실패: {e}") from e

    if not chunks:
        await asyncio.to_thread(
            material_store.update_material,
            material_id,
            status="failed",
            error="추출된 청크가 없습니다.",
        )
        raise HTTPException(status_code=400, detail="추출된 청크가 없습니다.")

    try:
        n = await chroma.upsert_chunks(material_id, chunks, is_public=False)
    except Exception as e:
        await asyncio.to_thread(
            material_store.update_material,
            material_id,
            status="failed",
            error=f"임베딩 저장 실패: {e}",
        )
        raise HTTPException(status_code=503, detail=f"임베딩 저장 실패: {e}") from e

    row = await asyncio.to_thread(
        material_store.update_material,
        material_id,
        status="ready",
        chunks=n,
    )
    return _row_to_response(row)


@router.post("/materials/github", response_model=MaterialResponse)
async def ingest_github(
    req: GithubIngestRequest,
    bg: BackgroundTasks,
    user: dict = Depends(current_user),
) -> MaterialResponse:
    material_id = _new_material_id()
    name = req.repo_url.rstrip("/").split("/")[-1] or req.repo_url
    row = await asyncio.to_thread(
        material_store.create_material,
        material_id=material_id,
        name=name,
        kind="github",
        user_id=user["id"],
        status="indexing",
    )
    bg.add_task(_run_github_ingest, material_id, req.repo_url)
    return _row_to_response(row)


async def _run_github_ingest(material_id: str, repo_url: str) -> None:
    """Background worker. Fetch → chunk per file → embed → upsert."""
    try:
        files = await fetch_github_md(repo_url)
    except Exception as e:
        log.exception("github fetch failed")
        msg = str(e)
        if "403" in msg and "rate limit" in msg.lower():
            msg = (
                "GitHub API 익명 호출 제한(60회/h)을 초과했습니다. "
                "backend/.env에 GITHUB_TOKEN=ghp_... 를 추가하면 5,000회/h로 늘어납니다."
            )
        await asyncio.to_thread(
            material_store.update_material,
            material_id,
            status="failed",
            error=f"GitHub 수집 실패: {msg}",
        )
        return

    if not files:
        await asyncio.to_thread(
            material_store.update_material,
            material_id,
            status="failed",
            error="md 파일을 찾지 못했습니다 (해당 리포에 .md가 없거나 비공개일 수 있음).",
        )
        return

    all_chunks: list[dict] = []
    for path, content in files:
        try:
            chunks = parse_md(content, file_name=path)
        except Exception as e:
            log.warning("md parse failed for %s: %s", path, e)
            continue
        all_chunks.extend(chunks)

    if not all_chunks:
        await asyncio.to_thread(
            material_store.update_material,
            material_id,
            status="failed",
            error="청크 생성 실패",
        )
        return

    try:
        n = await chroma.upsert_chunks(material_id, all_chunks, is_public=False)
    except Exception as e:
        log.exception("chroma upsert failed")
        await asyncio.to_thread(
            material_store.update_material,
            material_id,
            status="failed",
            error=f"임베딩 저장 실패: {e}",
        )
        return

    await asyncio.to_thread(
        material_store.update_material,
        material_id,
        status="ready",
        chunks=n,
    )


@router.get("/materials", response_model=list[MaterialResponse])
async def list_materials(
    user: dict = Depends(current_user),
) -> list[MaterialResponse]:
    rows = await asyncio.to_thread(material_store.list_materials, user["id"])
    return [_row_to_response(r) for r in rows]


@router.get("/materials/{material_id}", response_model=MaterialResponse)
async def get_material(
    material_id: str,
    user: dict = Depends(current_user),
) -> MaterialResponse:
    row = await asyncio.to_thread(_ensure_material_access, material_id, user["id"])
    return _row_to_response(row)


@router.delete("/materials/{material_id}", status_code=204)
async def delete_material(
    material_id: str,
    user: dict = Depends(current_user),
) -> None:
    await asyncio.to_thread(_ensure_material_access, material_id, user["id"])
    # Drop Chroma collection first; if that fails the metadata row stays
    # so the user can retry deletion.
    try:
        await chroma.delete_collection(material_id)
    except Exception as e:
        log.warning("chroma delete collection failed for %s: %s", material_id, e)
    await asyncio.to_thread(material_store.delete_material, material_id)
