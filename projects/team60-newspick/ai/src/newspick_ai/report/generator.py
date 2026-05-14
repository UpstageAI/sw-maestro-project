import json
import os
from collections.abc import Callable
from dataclasses import asdict
from datetime import date, datetime
from zoneinfo import ZoneInfo

import asyncpg

from newspick_ai.report.briefing import BriefingGenerator
from newspick_ai.report.clustering import cluster_articles
from newspick_ai.report.keywords import KeywordGenerator
from newspick_ai.report.persistor import DailyReport, DailyReportPersistor
from newspick_ai.report.timeline_flow import TimelineFlowGenerator

SEOUL_TZ = ZoneInfo("Asia/Seoul")


def _default_now_provider() -> datetime:
    return datetime.now(SEOUL_TZ)


class DailyReportGenerator:
    def __init__(
        self,
        pool=None,
        *,
        now_provider: Callable[[], datetime] | None = None,
    ):
        self._pool = pool
        self._now_provider = now_provider or _default_now_provider
        self._briefing_gen = BriefingGenerator()
        self._keyword_gen = KeywordGenerator()
        self._timeline_gen = TimelineFlowGenerator()
        self._persistor = DailyReportPersistor(pool)

    async def generate(self, article_ids: list[str] | None = None) -> dict:
        seoul_today = self._now_provider().astimezone(SEOUL_TZ).date()
        report_date = seoul_today.isoformat()
        if not article_ids:
            article_ids = await self._fetch_today_article_ids(seoul_today)
        if not article_ids:
            return {"date": report_date}

        articles = await self._fetch_articles(article_ids)
        if not articles:
            return {"date": report_date}

        clustered = cluster_articles(articles)
        main_articles = _select_cluster_representatives(clustered)

        briefing = self._briefing_gen.generate(main_articles)
        keywords = self._keyword_gen.generate(main_articles)
        timeline_result = self._timeline_gen.generate(main_articles)

        report = DailyReport(
            date=report_date,
            headline=briefing.headline,
            summary=briefing.summary,
            timeline=[asdict(item) for item in timeline_result.timeline],
            flow=[asdict(step) for step in timeline_result.flow],
            keywords=[asdict(kw) for kw in keywords],
            article_ids=article_ids,
        )
        await self._persistor.upsert(report)
        return {"date": report_date}

    async def _fetch_today_article_ids(self, seoul_today: date) -> list[str]:
        pool = self._pool or await asyncpg.create_pool(os.environ["DATABASE_URL"])
        close_pool = self._pool is None
        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT id FROM articles
                    WHERE (published_at AT TIME ZONE 'Asia/Seoul')::date = $1
                      AND embedding IS NOT NULL
                    """,
                    seoul_today,
                )
                return [row["id"] for row in rows]
        finally:
            if close_pool:
                await pool.close()

    async def _fetch_articles(self, article_ids: list[str]) -> list[dict]:
        pool = self._pool or await asyncpg.create_pool(os.environ["DATABASE_URL"])
        close_pool = self._pool is None
        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT id, title, category, summary::text AS summary_text,
                           embedding::text AS embedding_text, published_at
                    FROM articles
                    WHERE id = ANY($1) AND embedding IS NOT NULL
                    """,
                    article_ids,
                )
                return [
                    {
                        "id": row["id"],
                        "title": row["title"],
                        "category": row["category"],
                        "summary": json.loads(row["summary_text"] or "[]"),
                        "embedding": _parse_vector(row["embedding_text"]),
                        "publishedAt": row["published_at"].isoformat(),
                    }
                    for row in rows
                ]
        finally:
            if close_pool:
                await pool.close()


def _parse_vector(vector_str: str) -> list[float]:
    return [float(x) for x in vector_str.strip("[]").split(",")]


def _select_cluster_representatives(clustered: list[dict]) -> list[dict]:
    cluster_map: dict[int, list[dict]] = {}
    noise: list[dict] = []
    for a in clustered:
        cid = a.get("clusterId")
        if cid is None:
            noise.append(a)
        else:
            cluster_map.setdefault(cid, []).append(a)

    representatives = [
        {**max(group, key=lambda x: x.get("publishedAt", "")), "sourceCount": len(group)}
        for group in cluster_map.values()
    ]
    if not representatives:
        return [{**a, "sourceCount": 1} for a in noise] or clustered
    return representatives
