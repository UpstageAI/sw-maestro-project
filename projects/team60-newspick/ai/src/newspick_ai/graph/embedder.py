import logging
import os
from typing import Any, Protocol

import asyncpg

from newspick_ai.graph.state import RefreshState
from newspick_ai.solar.embeddings import SolarEmbeddingClient


logger = logging.getLogger(__name__)


class EmbeddingClient(Protocol):
    def embed_passage(self, text: str) -> list[float]:
        ...


class Embedder:
    def __init__(
        self,
        pool: Any | None = None,
        embedding_client: EmbeddingClient | None = None,
    ):
        self._pool = pool
        self._embedding_client = embedding_client or SolarEmbeddingClient()

    async def run(self, state: RefreshState) -> RefreshState:
        pool = self._pool or await asyncpg.create_pool(os.environ["DATABASE_URL"])
        close_pool = self._pool is None

        try:
            embedded_ids, skipped_ids = await self._embed_articles(pool, state)
        finally:
            if close_pool:
                await pool.close()

        return {
            "articles": state["articles"],
            "events": [
                *state["events"],
                {
                    "stage": "embed",
                    "message": f"{len(embedded_ids)}건 임베딩 저장",
                    "articleIds": embedded_ids,
                    "count": len(embedded_ids),
                    "skippedArticleIds": skipped_ids,
                },
            ],
        }

    async def _embed_articles(
        self, pool: Any, state: RefreshState
    ) -> tuple[list[str], list[str]]:
        embedded_ids = []
        skipped_ids = []

        async with pool.acquire() as connection:
            for article in state["articles"]:
                try:
                    vector = self._embedding_client.embed_passage(article["content"])
                except Exception as exc:
                    logger.warning("임베딩 생성 실패 [%s]: %s", article.get("id"), exc)
                    skipped_ids.append(article["id"])
                    continue
                status = await connection.execute(
                    """
                    UPDATE articles
                    SET embedding = $2::vector,
                        updated_at = now()
                    WHERE id = $1
                    """,
                    article["id"],
                    _format_vector(vector),
                )
                if status == "UPDATE 1":
                    embedded_ids.append(article["id"])
                else:
                    skipped_ids.append(article["id"])

        return embedded_ids, skipped_ids


def _format_vector(vector: list[float]) -> str:
    return "[" + ",".join(str(value) for value in vector) + "]"
