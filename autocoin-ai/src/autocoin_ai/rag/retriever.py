"""Keyword-matching RAG retriever for trader principles."""

from __future__ import annotations

import re
from typing import List

from autocoin_ai.traders import Principle, load_trader


def _tokenize(text: str) -> set[str]:
    return set(t.lower() for t in re.split(r"[\s,./·\-]+", text) if t)


def retrieve_relevant(trader_id: str, query: str, k: int = 5) -> List[Principle]:
    trader = load_trader(trader_id)
    query_tokens = _tokenize(query)

    scored: List[tuple[int, Principle]] = []
    for p in trader.principles:
        kw_tokens = _tokenize(" ".join(p.keywords))
        score = len(query_tokens & kw_tokens)
        scored.append((score, p))

    scored.sort(key=lambda x: (-x[0], x[1].chunk_id))
    return [p for _, p in scored[:k]]
