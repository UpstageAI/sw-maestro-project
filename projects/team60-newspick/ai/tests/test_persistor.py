from pathlib import Path
import os

import asyncpg
import pytest
from testcontainers.postgres import PostgresContainer

from newspick_ai.graph.persistor import Persistor


CONTRACT_SQL = (
    Path(__file__).parents[2] / "docs" / "contracts" / "db-init.sql"
)
os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")


@pytest.mark.asyncio
async def test_persistor_inserts_one_empty_article_row():
    state = {
        "articles": [
            {
                "id": "article_001",
                "url": "https://example.com/a1",
                "title": "첫 기사",
                "source": "Example",
                "category": "tech",
                "publishedAt": "2026-05-12T00:00:00Z",
                "status": "collected",
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
        await connection.close()

        pool = await asyncpg.create_pool(database_url)
        try:
            output = await Persistor(pool).run(state)

            row = await pool.fetchrow(
                "SELECT id, url, status FROM articles WHERE id=$1",
                "article_001",
            )
        finally:
            await pool.close()

    assert row is not None
    assert row["id"] == "article_001"
    assert row["url"] == "https://example.com/a1"
    assert row["status"] == "collected"
    assert output["events"][0]["stage"] == "persist"
    assert output["events"][0]["count"] == 1
    assert output["persistedArticleIds"] == ["article_001"]


@pytest.mark.asyncio
async def test_persistor_updates_existing_article_for_same_url():
    state = {
        "articles": [
            {
                "id": "article_001",
                "url": "https://example.com/a1",
                "title": "수정된 제목",
                "source": "Updated",
                "category": "economy",
                "publishedAt": "2026-05-12T01:00:00Z",
                "status": "collected",
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
            """
            INSERT INTO articles (
              id, url, title, source, category, published_at, status
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            "article_001",
            "https://example.com/a1",
            "기존 제목",
            "Old",
            "politics",
            Persistor._parse_published_at("2026-05-12T00:00:00Z"),
            "collected",
        )
        await connection.close()

        pool = await asyncpg.create_pool(database_url)
        try:
            output = await Persistor(pool).run(state)

            row = await pool.fetchrow(
                "SELECT title, source, category FROM articles WHERE id=$1",
                "article_001",
            )
        finally:
            await pool.close()

    assert row["title"] == "수정된 제목"
    assert row["source"] == "Updated"
    assert row["category"] == "economy"
    assert output["events"][0]["count"] == 1
    assert output["events"][0]["articleIds"] == ["article_001"]
