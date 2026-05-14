import pytest

from newspick_ai.graph.refresh_resetter import RefreshResetter


class FakeTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeConnection:
    def __init__(self):
        self.statements: list[str] = []

    def transaction(self):
        return FakeTransaction()

    async def execute(self, statement: str):
        self.statements.append(" ".join(statement.split()))


class FakeAcquire:
    def __init__(self, connection: FakeConnection):
        self._connection = connection

    async def __aenter__(self):
        return self._connection

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakePool:
    def __init__(self):
        self.connection = FakeConnection()

    def acquire(self):
        return FakeAcquire(self.connection)


@pytest.mark.asyncio
async def test_refresh_resetter_deletes_reports_and_articles_in_one_reset(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://newspick:test@localhost:5432/newspick")
    pool = FakePool()

    await RefreshResetter(pool=pool).run()

    assert pool.connection.statements == [
        "DELETE FROM daily_reports",
        "DELETE FROM articles",
    ]
