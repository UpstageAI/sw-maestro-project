from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterable


@dataclass
class Chunk:
    symbol: str
    kind: str  # "quote" | "daily" | "summary"
    text: str
    meta: dict = field(default_factory=dict)


class ChunkStore:
    """심플한 in-memory 청크 스토어. 벡터 DB 자리에 끼우는 가벼운 대체.

    종목별로 청크를 보관하고, 질의어가 있으면 토큰 겹침 점수로 랭킹해 상위 k개를 반환한다.
    """

    def __init__(self) -> None:
        self._by_symbol: dict[str, list[Chunk]] = defaultdict(list)

    def add(self, chunk: Chunk) -> None:
        self._by_symbol[chunk.symbol].append(chunk)

    def add_many(self, chunks: Iterable[Chunk]) -> None:
        for c in chunks:
            self.add(c)

    def has(self, symbol: str) -> bool:
        return bool(self._by_symbol.get(symbol))

    def reset(self, symbol: str) -> None:
        self._by_symbol.pop(symbol, None)

    def get(self, symbol: str, query: str | None = None, k: int = 8) -> list[Chunk]:
        chunks = list(self._by_symbol.get(symbol, []))
        if not chunks:
            return []
        if not query:
            return chunks[:k]
        q_terms = _tokenize(query)
        if not q_terms:
            return chunks[:k]
        # summary/quote 청크에 가산점을 주어 핵심 요약이 상위에 오도록 함
        kind_bonus = {"summary": 2, "quote": 1, "daily": 0}
        scored: list[tuple[int, int, Chunk]] = []
        for idx, c in enumerate(chunks):
            text_lower = c.text.lower()
            score = sum(1 for t in q_terms if t in text_lower)
            score += kind_bonus.get(c.kind, 0) if score > 0 else 0
            scored.append((score, idx, c))
        scored.sort(key=lambda x: (-x[0], x[1]))
        return [c for _, _, c in scored[:k]]


def _tokenize(text: str) -> list[str]:
    """질의어를 부분 문자열 매칭용 토큰으로 분리. 한국어/영문 혼용에 견고하게."""
    cleaned = text.lower()
    for ch in ",.!?;:()[]{}\"'/\\":
        cleaned = cleaned.replace(ch, " ")
    return [t for t in cleaned.split() if t]


store = ChunkStore()
