from datetime import date, datetime
from zoneinfo import ZoneInfo

from newspick_ai.report.generator import DailyReportGenerator


class _FakeConnection:
    def __init__(self, rows: list[dict] | None = None):
        self.rows = rows or []
        self.fetch_calls: list[tuple[str, tuple]] = []

    async def fetch(self, sql: str, *args):
        self.fetch_calls.append((sql, args))
        return list(self.rows)


class _FakeAcquireCtx:
    def __init__(self, connection: _FakeConnection):
        self._connection = connection

    async def __aenter__(self):
        return self._connection

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakePool:
    def __init__(self, connection: _FakeConnection):
        self._connection = connection

    def acquire(self):
        return _FakeAcquireCtx(self._connection)


async def test_generate_reports_seoul_date_when_utc_is_yesterday():
    just_after_seoul_midnight = datetime(
        2026, 5, 14, 0, 30, tzinfo=ZoneInfo("Asia/Seoul")
    )
    connection = _FakeConnection(rows=[])
    pool = _FakePool(connection)
    generator = DailyReportGenerator(
        pool=pool, now_provider=lambda: just_after_seoul_midnight
    )

    result = await generator.generate()

    assert result == {"date": "2026-05-14"}


async def test_fetch_today_article_ids_filters_by_seoul_calendar_day():
    just_after_seoul_midnight = datetime(
        2026, 5, 14, 0, 30, tzinfo=ZoneInfo("Asia/Seoul")
    )
    connection = _FakeConnection(rows=[])
    pool = _FakePool(connection)
    generator = DailyReportGenerator(
        pool=pool, now_provider=lambda: just_after_seoul_midnight
    )

    await generator.generate()

    assert connection.fetch_calls, "expected the generator to query today's article ids"
    sql, args = connection.fetch_calls[0]
    assert "AT TIME ZONE 'Asia/Seoul'" in sql
    assert args == (date(2026, 5, 14),)
