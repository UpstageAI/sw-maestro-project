import json
import os
from typing import Any

import asyncpg

from newspick_ai.graph.state import RefreshState


class ArticleUpdater:
    def __init__(self, pool: Any | None = None):
        self._pool = pool

    async def run(self, state: RefreshState) -> RefreshState:
        pool = self._pool or await asyncpg.create_pool(os.environ["DATABASE_URL"])
        close_pool = self._pool is None

        try:
            updated_ids, skipped_ids = await self._update_articles(pool, state)
        finally:
            if close_pool:
                await pool.close()

        return {
            "articles": state["articles"],
            "events": [
                *state["events"],
                {
                    "stage": "update_article",
                    "message": f"{len(updated_ids)}건 요약 저장",
                    "articleIds": updated_ids,
                    "count": len(updated_ids),
                    "skippedArticleIds": skipped_ids,
                },
            ],
        }

    async def _update_articles(
        self, pool: Any, state: RefreshState
    ) -> tuple[list[str], list[str]]:
        updated_ids = []
        skipped_ids = []

        async with pool.acquire() as connection:
            for article in state["articles"]:
                status = await connection.execute(
                    """
                    UPDATE articles
                    SET raw_text = $2,
                        raw_text_status = $3,
                        summary = $4::jsonb,
                        keywords = $5::jsonb,
                        importance = $6,
                        context = $7,
                        importance_score = $8,
                        status = $9,
                        updated_at = now()
                    WHERE id = $1
                    """,
                    article["id"],
                    article["content"],
                    article.get("rawTextStatus"),
                    json.dumps(article["summary"], ensure_ascii=False),
                    json.dumps(article.get("keywords", []), ensure_ascii=False),
                    article.get("importance"),
                    article.get("context"),
                    article.get("importanceScore"),
                    article["status"],
                )
                if status == "UPDATE 1":
                    updated_ids.append(article["id"])
                else:
                    skipped_ids.append(article["id"])

        return updated_ids, skipped_ids
