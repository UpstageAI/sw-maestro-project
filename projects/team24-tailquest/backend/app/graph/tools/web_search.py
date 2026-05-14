"""Tavily web search fallback for knowledge_retriever_node.

Called only when:
  - settings.use_web_search is True
  - settings.tavily_api_key is non-empty
  - Chroma returned no chunks or all chunk scores < 0.5

Never raises — all errors are swallowed and an empty list is returned so the
graph always completes.
"""

from __future__ import annotations

import asyncio
import logging

from pydantic import BaseModel

from app.config import get_settings

logger = logging.getLogger(__name__)


class WebSearchHit(BaseModel):
    title: str
    url: str
    snippet: str
    score: float = 0.0


async def tavily_search(query: str, max_results: int = 5) -> list[WebSearchHit]:
    settings = get_settings()
    if not settings.tavily_api_key or not settings.use_web_search:
        return []

    import time as _time
    from app.log_format import stage

    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=settings.tavily_api_key)

        def _search() -> list[dict]:
            resp = client.search(
                query,
                search_depth="basic",
                max_results=max_results,
                include_answer=False,
            )
            return resp.get("results", [])

        stage("🌐 [TAVILY] search", query=query, max_results=max_results)
        t0 = _time.monotonic()
        results: list[dict] = await asyncio.to_thread(_search)
        stage(
            "⏱  [TAVILY] done",
            hits=len(results),
            elapsed=f"{_time.monotonic() - t0:.2f}s",
        )
        return [
            WebSearchHit(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=r.get("content", ""),
                score=float(r.get("score", 0.0)),
            )
            for r in results
        ]
    except Exception as exc:
        stage("✗ [TAVILY] failed", error=str(exc))
        logger.warning("tavily_search failed: %s", exc)
        return []
