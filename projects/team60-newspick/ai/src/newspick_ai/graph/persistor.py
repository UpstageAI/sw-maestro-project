import os
from datetime import datetime
from typing import Any

import asyncpg

from newspick_ai.graph.state import RefreshState


class Persistor:
    def __init__(self, pool: Any | None = None):
        self._pool = pool

    async def run(self, state: RefreshState) -> RefreshState:
        pool = self._pool or await asyncpg.create_pool(os.environ["DATABASE_URL"])
        close_pool = self._pool is None

        try:
            persisted_ids = await self._upsert_articles(pool, state)
        finally:
            if close_pool:
                await pool.close()

        return {
            "articles": state["articles"],
            "persistedArticleIds": persisted_ids,
            "events": [
                *state["events"],
                {
                    "stage": "persist",
                    "message": f"{len(persisted_ids)}건 저장",
                    "articleIds": persisted_ids,
                    "count": len(persisted_ids),
                },
            ],
        }

    async def _upsert_articles(self, pool: Any, state: RefreshState) -> list[str]:
        persisted_ids = []
        async with pool.acquire() as connection:
            for article in state["articles"]:
                article_id = await connection.fetchval(
                    """
                    INSERT INTO articles (
                      id, url, title, source, category, published_at, status
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (url) DO UPDATE SET
                      title = EXCLUDED.title,
                      source = EXCLUDED.source,
                      category = EXCLUDED.category,
                      published_at = EXCLUDED.published_at,
                      status = EXCLUDED.status,
                      updated_at = now()
                    RETURNING id
                    """,
                    article["id"],
                    article["url"],
                    article["title"],
                    article["source"],
                    article["category"],
                    self._parse_published_at(article["publishedAt"]),
                    article.get("status", "collected"),
                )
                if article_id:
                    persisted_ids.append(article_id)

        return persisted_ids

    @staticmethod
    def _parse_published_at(value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
