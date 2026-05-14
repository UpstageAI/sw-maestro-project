from pathlib import Path
from datetime import UTC, datetime
import os

import asyncpg
import pytest
from testcontainers.postgres import PostgresContainer

from newspick_ai.graph.embedder import Embedder


CONTRACT_SQL = (
    Path(__file__).parents[2] / "docs" / "contracts" / "db-init.sql"
)
os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")


class FakeEmbeddingClient:
    def __init__(self):
        self.calls = []

    def embed_passage(self, text: str):
        self.calls.append(text)
        return [0.1, 0.2, 0.3, 0.4]


class FailingEmbeddingClient:
    def embed_passage(self, text: str):
        raise RuntimeError("too_many_requests")


class FakeAcquire:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def execute(self, *args):
        raise AssertionError("execute should not be called when embedding fails")


class FakePool:
    def acquire(self):
        return FakeAcquire()


@pytest.mark.asyncio
async def test_embedder_stores_passage_embedding_vector():
    fake = FakeEmbeddingClient()
    content = "본문 첫 문단입니다. 본문 둘째 문단입니다."
    state = {
        "articles": [
            {
                "id": "article_001",
                "content": content,
            }
        ],
        "events": [],
    }

    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        database_url = postgres.get_connection_url().replace(
            "postgresql+psycopg2://", "postgresql://"
        )
        connection = await asyncpg.connect(database_url)
        await connection.execute(CONTRACT_SQL.read_text(encoding="utf-8"))
        await connection.execute(
            "ALTER TABLE articles ALTER COLUMN embedding TYPE vector(4)"
        )
        await connection.execute(
            """
            INSERT INTO articles (
              id, url, title, source, category, published_at, status
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            "article_001",
            "https://example.com/a1",
            "첫 기사",
            "Example",
            "테크",
            datetime(2026, 5, 12, tzinfo=UTC),
            "summarized",
        )
        await connection.close()

        pool = await asyncpg.create_pool(database_url)
        try:
            output = await Embedder(pool, embedding_client=fake).run(state)
            row = await pool.fetchrow(
                "SELECT embedding::text AS embedding FROM articles WHERE id=$1",
                "article_001",
            )
        finally:
            await pool.close()

    assert fake.calls == [content]
    assert row["embedding"] == "[0.1,0.2,0.3,0.4]"
    assert output["events"][0]["stage"] == "embed"


@pytest.mark.asyncio
async def test_embedder_skips_article_when_embedding_client_fails():
    state = {
        "articles": [
            {
                "id": "article_001",
                "content": "본문 첫 문단입니다.",
            }
        ],
        "events": [],
    }

    output = await Embedder(
        FakePool(),
        embedding_client=FailingEmbeddingClient(),
    ).run(state)

    assert output["events"][0]["articleIds"] == []
    assert output["events"][0]["skippedArticleIds"] == ["article_001"]
