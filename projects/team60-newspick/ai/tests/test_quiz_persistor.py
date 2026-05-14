from pathlib import Path
from datetime import UTC, datetime
import json
import os

import asyncpg
import pytest
from testcontainers.postgres import PostgresContainer

from newspick_ai.graph.quiz_persistor import QuizPersistor


CONTRACT_SQL = (
    Path(__file__).parents[2] / "docs" / "contracts" / "db-init.sql"
)
os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")


@pytest.mark.asyncio
async def test_quiz_persistor_updates_article_quiz_payload():
    quizzes = [
        {
            "id": "quiz_001",
            "question": "AI가 기사 작성 시간을 줄인다.",
            "answer": True,
            "explanation": "기사에서는 AI가 작성 시간을 줄인다고 설명한다.",
        },
        {
            "id": "quiz_002",
            "question": "이 기사는 스포츠 경기 결과만 다룬다.",
            "answer": False,
            "explanation": "기사 주제는 AI 기술이다.",
        },
    ]
    state = {
        "articles": [
            {
                "id": "article_001",
                "quizzes": quizzes,
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
            "summarized",
        )
        await connection.close()

        pool = await asyncpg.create_pool(database_url)
        try:
            output = await QuizPersistor(pool).run(state)
            row = await pool.fetchrow(
                "SELECT quiz FROM articles WHERE id=$1",
                "article_001",
            )
        finally:
            await pool.close()

    payload = json.loads(row["quiz"])
    assert len(payload) == 2
    assert payload[0]["id"] == "quiz_001"
    assert payload[0]["answer"] is True
    assert payload[0]["explanation"] == "기사에서는 AI가 작성 시간을 줄인다고 설명한다."
    assert output["events"][0]["stage"] == "persist_quiz"
