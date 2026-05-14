import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime, date
from typing import Any

import asyncpg


@dataclass
class DailyReport:
    date: str  # "YYYY-MM-DD"
    headline: str
    summary: str
    timeline: list[dict] = field(default_factory=list)
    flow: list[dict] = field(default_factory=list)
    keywords: list[dict] = field(default_factory=list)
    article_ids: list[str] = field(default_factory=list)


class DailyReportPersistor:
    def __init__(self, pool: Any | None = None):
        self._pool = pool

    async def upsert(self, report: DailyReport) -> None:
        pool = self._pool or await asyncpg.create_pool(os.environ["DATABASE_URL"])
        close_pool = self._pool is None

        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO daily_reports (
                        report_date, report_updated_at, briefing,
                        flow, timeline, keywords
                    ) VALUES ($1, $2, $3::jsonb, $4::jsonb, $5::jsonb, $6::jsonb)
                    ON CONFLICT (report_date) DO UPDATE SET
                        report_updated_at = EXCLUDED.report_updated_at,
                        briefing          = EXCLUDED.briefing,
                        flow              = EXCLUDED.flow,
                        timeline          = EXCLUDED.timeline,
                        keywords          = EXCLUDED.keywords
                    """,
                    date.fromisoformat(report.date),
                    datetime.now(tz=UTC),
                    json.dumps({"headline": report.headline, "summary": report.summary}, ensure_ascii=False),
                    json.dumps(report.flow, ensure_ascii=False),
                    json.dumps(report.timeline, ensure_ascii=False),
                    json.dumps(report.keywords, ensure_ascii=False),
                )
        finally:
            if close_pool:
                await pool.close()
