"""Solar embedding helpers.

Solar exposes asymmetric embedding models:
  - `solar-embedding-1-large-passage` for documents (ingest side)
  - `solar-embedding-1-large-query` for queries (retrieval side)

Use the matching model on each side for higher recall.

In `USE_MOCK_LLM=true` mode we return deterministic 384-dim float vectors derived
from a SHA-256 hash of the input — same text always produces the same vector, so
Chroma's cosine similarity still behaves sensibly within a single mock run.
"""

from __future__ import annotations

import hashlib
import struct
from typing import Iterable

from app.config import get_settings
from app.llm.solar import get_client

_BATCH_SIZE = 100
_MOCK_DIM = 384


def _mock_vector(text: str) -> list[float]:
    """Deterministic float vector derived from SHA-256 of the text.

    Repeats the digest enough times to fill 384 dims, then maps each byte
    to [-1.0, 1.0]. Same input → same output.
    """
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    needed_bytes = _MOCK_DIM * 4  # 4 bytes per float
    repeats = (needed_bytes // len(digest)) + 1
    blob = (digest * repeats)[:needed_bytes]
    floats: list[float] = []
    for i in range(_MOCK_DIM):
        # interpret 4 bytes as unsigned int → normalize to [-1, 1]
        (n,) = struct.unpack_from(">I", blob, i * 4)
        floats.append((n / 0xFFFFFFFF) * 2.0 - 1.0)
    return floats


def _batched(items: list[str], size: int) -> Iterable[list[str]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


async def embed_passages(texts: list[str]) -> list[list[float]]:
    """Embed document chunks with the passage-side model."""
    if not texts:
        return []
    settings = get_settings()
    if settings.use_mock_llm:
        return [_mock_vector(t) for t in texts]

    client = get_client()
    out: list[list[float]] = []
    for batch in _batched(texts, _BATCH_SIZE):
        res = await client.embeddings.create(
            model=settings.embedding_model_passage,
            input=batch,
        )
        out.extend(item.embedding for item in res.data)
    return out


async def embed_query(text: str) -> list[float]:
    """Embed a single search query with the query-side model."""
    settings = get_settings()
    if settings.use_mock_llm:
        return _mock_vector(text)

    client = get_client()
    res = await client.embeddings.create(
        model=settings.embedding_model_query,
        input=[text],
    )
    return res.data[0].embedding
