"""Embedding-cache based persona retrieval for LLM selection."""

from __future__ import annotations

import hashlib
import json
import math
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from langchain_upstage import UpstageEmbeddings

from schemas import ServicePlanInput, TargetUserPersonaCard

DEFAULT_CACHE_PATH = Path(__file__).parent.parent / "data" / "personas" / "persona_cards.selected.embeddings.json"
EMBEDDING_MODEL = "solar-embedding-1-large"

_MISSING_SCORE = float("-inf")


def _join_nonempty(parts: Sequence[str | None]) -> str:
    return "\n".join(part.strip() for part in parts if part and part.strip())


def brief_selection_text(brief: ServicePlanInput) -> str:
    return _join_nonempty([
        brief.title,
        brief.target,
        brief.description,
        "\n".join(brief.key_features),
        brief.concerns,
        brief.raw_text,
    ])


def persona_selection_text(card: TargetUserPersonaCard) -> str:
    return _join_nonempty([
        card.age_group,
        card.sex,
        card.occupation,
        card.region,
        card.one_line_summary,
        card.life_context,
        "\n".join(card.user_goals),
        "\n".join(card.pain_points),
        "\n".join(card.positive_triggers),
        "\n".join(card.negative_triggers),
    ])


def persona_text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if not left or len(left) != len(right):
        return 0.0

    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def _load_embedding_cache(cache_path: Path) -> dict[str, tuple[str, list[float]]]:
    raw = json.loads(cache_path.read_text(encoding="utf-8"))
    cache: dict[str, tuple[str, list[float]]] = {}

    for item in raw.get("items", []):
        card_id = item.get("card_id")
        text_hash = item.get("text_hash")
        embedding = item.get("embedding")
        if isinstance(card_id, str) and isinstance(text_hash, str) and isinstance(embedding, list):
            cache[card_id] = (text_hash, [float(value) for value in embedding])

    return cache


def _embed_query(text: str) -> list[float]:
    embeddings = UpstageEmbeddings(
        model=EMBEDDING_MODEL,
        timeout=60.0,
        max_retries=1,
    )
    return embeddings.embed_query(text)


def rank_personas_for_brief(
    brief: ServicePlanInput,
    pool: Sequence[TargetUserPersonaCard],
    *,
    cache_path: Path = DEFAULT_CACHE_PATH,
    embed_query: Callable[[str], list[float]] | None = None,
) -> list[TargetUserPersonaCard]:
    cards = list(pool)
    if not cards:
        return []

    cache_path = Path(cache_path)
    if not cache_path.exists():
        return cards

    try:
        cache = _load_embedding_cache(cache_path)
    except Exception as exc:
        print(f"[persona_retrieval] embedding cache load failed: {exc!r}", file=sys.stderr, flush=True)
        return cards

    if not cache:
        return cards

    cached_embeddings: list[list[float] | None] = []
    matched_count = 0
    for card in cards:
        cached = cache.get(card.card_id)
        if cached is None:
            cached_embeddings.append(None)
            continue

        expected_hash, card_embedding = cached
        if expected_hash != persona_text_hash(persona_selection_text(card)):
            cached_embeddings.append(None)
            continue

        matched_count += 1
        cached_embeddings.append(card_embedding)

    if matched_count == 0:
        return cards

    try:
        query_embedding = (embed_query or _embed_query)(brief_selection_text(brief))
    except Exception as exc:
        print(f"[persona_retrieval] query embedding failed: {exc!r}", file=sys.stderr, flush=True)
        return cards

    if not query_embedding:
        return cards

    scored: list[tuple[float, int, TargetUserPersonaCard]] = []
    for index, (card, card_embedding) in enumerate(zip(cards, cached_embeddings, strict=True)):
        score = (
            cosine_similarity(query_embedding, card_embedding)
            if card_embedding is not None
            else _MISSING_SCORE
        )
        scored.append((score, index, card))

    return [card for _, _, card in sorted(scored, key=lambda item: (-item[0], item[1]))]
