import json
import os
from datetime import date
from pathlib import Path

import asyncpg
import pytest
from testcontainers.postgres import PostgresContainer

from newspick_ai.report.persistor import DailyReport, DailyReportPersistor


CONTRACT_SQL = Path(__file__).parents[2] / "docs" / "contracts" / "db-init.sql"
os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")


@pytest.mark.asyncio
async def test_daily_report_persistor_upserts_same_report_date():
    report1 = DailyReport(
        date="2026-05-12",
        headline="첫 번째 헤드라인",
        summary="첫 번째 요약",
    )
    report2 = DailyReport(
        date="2026-05-12",
        headline="두 번째 헤드라인",
        summary="두 번째 요약",
    )

    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        database_url = postgres.get_connection_url().replace(
            "postgresql+psycopg2://", "postgresql://"
        )
        conn = await asyncpg.connect(database_url)
        await conn.execute(CONTRACT_SQL.read_text(encoding="utf-8"))
        await conn.close()

        pool = await asyncpg.create_pool(database_url)
        try:
            await DailyReportPersistor(pool).upsert(report1)
            await DailyReportPersistor(pool).upsert(report2)

            count = await pool.fetchval(
                "SELECT COUNT(*) FROM daily_reports WHERE report_date = $1",
                date.fromisoformat("2026-05-12"),
            )
            row = await pool.fetchrow(
                "SELECT briefing, report_updated_at, created_at FROM daily_reports WHERE report_date = $1",
                date.fromisoformat("2026-05-12"),
            )
        finally:
            await pool.close()

    assert count == 1
    assert json.loads(row["briefing"])["headline"] == "두 번째 헤드라인"
    assert row["report_updated_at"] >= row["created_at"]
