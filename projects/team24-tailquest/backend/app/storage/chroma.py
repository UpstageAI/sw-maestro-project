"""Chroma persistence layer for RAG.

Collection layout:
  - `public`                    — service-provided shared corpus
  - `user_<material_id>`        — one collection per user-uploaded material

Search merges results from `public` and any user collections matching the
caller-supplied `material_ids`, then sorts by score (lower distance is better
in Chroma; we convert to a similarity-style score = 1 - distance).

Embeddings come from `app.llm.embeddings`. In USE_MOCK_LLM mode `search_chunks`
returns an empty list — the LangGraph retriever node has its own mock fallback
that produces realistic placeholder chunks, so we keep this side quiet.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import get_settings
from app.llm.embeddings import embed_passages, embed_query

log = logging.getLogger(__name__)

_PUBLIC_COLLECTION = "public"


def _user_collection_name(material_id: str) -> str:
    # Chroma collection names must be 3-63 chars, [a-z0-9._-], not start/end with .
    safe = material_id.replace("/", "_").lower()
    return f"user_{safe}"


# ---------- Module-level client (lazy singleton) ----------

_client: chromadb.api.ClientAPI | None = None


def _get_client() -> chromadb.api.ClientAPI:
    global _client
    if _client is None:
        settings = get_settings()
        Path(settings.chroma_persist_dir).mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False, allow_reset=False),
        )
    return _client


def _get_or_create(name: str):
    client = _get_client()
    # `get_or_create_collection` is the safe API: idempotent across requests.
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


# ---------- Public API ----------

async def upsert_chunks(
    material_id: str,
    chunks: list[dict],
    is_public: bool = False,
) -> int:
    """Embed and upsert chunks into the appropriate collection.

    `chunks` items: {text, file_name, heading, page?, ...}
    Returns the number of chunks inserted.
    """
    if not chunks:
        return 0

    texts = [c["text"] for c in chunks]
    embeddings = await embed_passages(texts)

    coll_name = _PUBLIC_COLLECTION if is_public else _user_collection_name(material_id)
    coll = _get_or_create(coll_name)

    ids = [f"{material_id}_{i}" for i in range(len(chunks))]
    metadatas: list[dict[str, Any]] = []
    for c in chunks:
        meta: dict[str, Any] = {
            "material_id": material_id,
            "file_name": c.get("file_name", ""),
            "heading": c.get("heading", ""),
            "source": "public" if is_public else "user",
        }
        if c.get("page") is not None:
            meta["page"] = int(c["page"])
        metadatas.append(meta)

    coll.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )
    return len(chunks)


async def search_chunks(
    query: str,
    material_ids: list[str],
    top_k: int = 5,
) -> list[dict]:
    """Search public + selected user collections, merge and rank by score.

    Returns: list of {text, source, file_name, heading, score}
    """
    settings = get_settings()
    if settings.use_mock_llm:
        # Let the LangGraph retriever node decide its own mock — keeps the
        # ingest path unmocked (Chroma still works) but avoids spurious hits.
        return []

    if not query.strip():
        return []

    q_emb = await embed_query(query)
    client = _get_client()

    # Always include the public collection.
    target_collections: list[str] = [_PUBLIC_COLLECTION]
    for mid in material_ids:
        target_collections.append(_user_collection_name(mid))

    existing_names = {c.name for c in client.list_collections()}

    merged: list[dict] = []
    for name in target_collections:
        if name not in existing_names:
            continue
        coll = client.get_collection(name=name)
        try:
            res = coll.query(
                query_embeddings=[q_emb],
                n_results=top_k,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:  # corrupted collection / empty / etc.
            log.warning("chroma query failed on %s: %s", name, e)
            continue

        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]

        for doc, meta, dist in zip(docs, metas, dists):
            score = 1.0 - float(dist) if dist is not None else 0.0
            merged.append({
                "text": doc,
                "source": (meta or {}).get("source", "user"),
                "file_name": (meta or {}).get("file_name", ""),
                "heading": (meta or {}).get("heading", ""),
                "score": score,
            })

    merged.sort(key=lambda x: x["score"], reverse=True)
    return merged[:top_k]


async def delete_collection(material_id: str) -> None:
    """Drop the per-material user collection. Idempotent."""
    client = _get_client()
    name = _user_collection_name(material_id)
    try:
        client.delete_collection(name=name)
    except Exception as e:
        # Already gone or never existed — fine.
        log.debug("delete_collection no-op for %s: %s", name, e)


# Eagerly initialize on module import so the persist directory exists before
# the first request hits us. Failures here surface at import time, not under load.
_get_client()
