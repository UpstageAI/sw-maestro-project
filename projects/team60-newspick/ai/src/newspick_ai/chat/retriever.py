import os

import asyncpg


class ArticleRetriever:
    def __init__(self, repository=None):
        self._repo = repository or PgvectorRepository()

    async def retrieve(self, vector: list[float], top_k: int = 5) -> list[dict]:
        results = await self._repo.search_by_embedding(vector, limit=top_k)
        return sorted(results, key=lambda x: -x["score"])[:top_k]


class PgvectorRepository:
    def __init__(self, pool=None):
        self._pool = pool

    async def search_by_embedding(self, vector: list[float], limit: int) -> list[dict]:
        pool = self._pool or await asyncpg.create_pool(os.environ["DATABASE_URL"])
        close_pool = self._pool is None
        vector_str = "[" + ",".join(str(v) for v in vector) + "]"
        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT id, title, source, published_at,
                           (1 - (embedding <=> $1::vector)) AS score
                    FROM articles
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> $1::vector
                    LIMIT $2
                    """,
                    vector_str,
                    limit,
                )
                return [
                    {
                        "id": row["id"],
                        "title": row["title"],
                        "source": row["source"],
                        "publishedAt": row["published_at"].isoformat(),
                        "score": float(row["score"]),
                    }
                    for row in rows
                ]
        finally:
            if close_pool:
                await pool.close()
