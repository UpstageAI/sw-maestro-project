import json
import os
from typing import Any

import asyncpg

from newspick_ai.graph.state import RefreshState


class QuizPersistor:
    def __init__(self, pool: Any | None = None):
        self._pool = pool

    async def run(self, state: RefreshState) -> RefreshState:
        pool = self._pool or await asyncpg.create_pool(os.environ["DATABASE_URL"])
        close_pool = self._pool is None

        try:
            updated_ids, skipped_ids = await self._update_quizzes(pool, state)
        finally:
            if close_pool:
                await pool.close()

        return {
            "articles": state["articles"],
            "events": [
                *state["events"],
                {
                    "stage": "persist_quiz",
                    "message": f"{len(updated_ids)}건 퀴즈 저장",
                    "articleIds": updated_ids,
                    "count": len(updated_ids),
                    "skippedArticleIds": skipped_ids,
                },
            ],
        }

    async def _update_quizzes(
        self, pool: Any, state: RefreshState
    ) -> tuple[list[str], list[str]]:
        updated_ids = []
        skipped_ids = []

        async with pool.acquire() as connection:
            for article in state["articles"]:
                quizzes = article.get("quizzes")
                if not quizzes:
                    skipped_ids.append(article["id"])
                    continue

                status = await connection.execute(
                    """
                    UPDATE articles
                    SET quiz = $2::jsonb,
                        updated_at = now()
                    WHERE id = $1
                    """,
                    article["id"],
                    json.dumps(quizzes, ensure_ascii=False),
                )
                if status == "UPDATE 1":
                    updated_ids.append(article["id"])
                else:
                    skipped_ids.append(article["id"])

        return updated_ids, skipped_ids
