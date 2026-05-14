from __future__ import annotations

from ..store import store


def extract(symbol: str, query: str | None = None, k: int = 8) -> str:
    """store에서 종목 컨텍스트를 추출해 LLM 프롬프트로 쓸 수 있는 평문으로 반환."""
    chunks = store.get(symbol, query=query, k=k)
    if not chunks:
        return ""
    return "\n".join(f"- [{c.kind}] {c.text}" for c in chunks)
