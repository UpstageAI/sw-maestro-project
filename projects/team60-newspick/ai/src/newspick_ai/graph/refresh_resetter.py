from typing import Any

import asyncpg

from newspick_ai.env import require_environment


class RefreshResetter:
    def __init__(self, pool: Any | None = None):
        self._pool = pool

    async def run(self) -> None:
        env = require_environment(("DATABASE_URL",))
        pool = self._pool or await asyncpg.create_pool(env["DATABASE_URL"])
        close_pool = self._pool is None

        try:
            await self._delete_demo_data(pool)
        finally:
            if close_pool:
                await pool.close()

    async def _delete_demo_data(self, pool: Any) -> None:
        async with pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute("DELETE FROM daily_reports")
                await connection.execute("DELETE FROM articles")
