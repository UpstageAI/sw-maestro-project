from pathlib import Path
from datetime import UTC, datetime
import json
import os

import asyncpg
import pytest
from testcontainers.postgres import PostgresContainer

from newspick_ai.graph.article_updater import ArticleUpdater


CONTRACT_SQL = (
    Path(__file__).parents[2] / "docs" / "contracts" / "db-init.sql"
)
os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")


@pytest.mark.asyncio
async def test_article_updater_updates_content_summary_and_status():
    summary = ["문장1.", "문장2.", "문장3."]
    state = {
        "articles": [
            {
                "id": "article_001",
                "content": "본문 첫 문단입니다. 본문 둘째 문단입니다.",
                "rawTextStatus": "description_only",
                "summary": summary,
                "keywords": ["AI", "뉴스"],
                "importance": "왜 중요한지 설명합니다.",
                "context": "배경 맥락입니다.",
                "importanceScore": 7,
                "status": "summarized",
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
            "첫 기사",
            "Example",
            "테크",
            datetime(2026, 5, 12, tzinfo=UTC),
            "collected",
        )
        await connection.close()

        pool = await asyncpg.create_pool(database_url)
        try:
            await ArticleUpdater(pool).run(state)
            row = await pool.fetchrow(
                """
                SELECT raw_text, summary, keywords, importance, context,
                       importance_score, raw_text_status, status
                FROM articles
                WHERE id=$1
                """,
                "article_001",
            )
        finally:
            await pool.close()

    assert row["raw_text"] == state["articles"][0]["content"]
    assert row["raw_text_status"] == "description_only"
    assert json.loads(row["summary"]) == summary
    assert json.loads(row["keywords"]) == ["AI", "뉴스"]
    assert row["importance"] == "왜 중요한지 설명합니다."
    assert row["context"] == "배경 맥락입니다."
    assert row["importance_score"] == 7
    assert row["status"] == "summarized"
