from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from psycopg import AsyncConnection
from psycopg.rows import dict_row

from app.config import settings


@asynccontextmanager
async def get_db_connection() -> AsyncIterator[AsyncConnection]:
    if not settings.database_url:
        raise RuntimeError("Database URL is not configured.")

    connection = await AsyncConnection.connect(
        settings.database_url,
        row_factory=dict_row,
    )
    try:
        yield connection
    finally:
        await connection.close()


async def check_database_connection() -> dict[str, str]:
    async with get_db_connection() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                """
                select
                    current_database() as database,
                    current_schema() as schema,
                    version() as version
                """
            )
            row = await cursor.fetchone()

    return {
        "database": str(row["database"]),
        "schema": str(row["schema"]),
        "version": str(row["version"]),
    }
