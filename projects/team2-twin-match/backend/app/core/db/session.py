from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import config, is_local


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 declarative base. All ORM models inherit from this."""


def _ensure_sqlite_parent_dir(db_url: str) -> None:
    """Create parent directory for the SQLite file if missing.

    Required for environments (CI / fresh checkouts) that don't run `start.sh`,
    which otherwise prepares `./data/`. No-op for non-SQLite URLs and `:memory:`.
    """
    if not db_url.startswith("sqlite"):
        return
    db_path = db_url.split("///", 1)[-1]
    if not db_path or db_path.startswith(":"):
        return
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_parent_dir(config.DB_URL)


engine = create_async_engine(
    config.DB_URL,
    echo=is_local(),
    pool_pre_ping=True,
    future=True,
)

async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


@event.listens_for(engine.sync_engine, "connect")
def _enable_sqlite_fk(dbapi_connection, _):
    """Enforce foreign key constraints on SQLite (off by default)."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an AsyncSession per request."""
    async with async_session_factory() as session:
        yield session


async def ping_db() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))


async def init_db() -> None:
    """Create all tables. Called on application startup (MVP)."""
    # Import all models so SQLAlchemy registers them on `Base.metadata`.
    from app.models.db import (  # noqa: F401
        agent,
        chemistry,
        conversation,
        job,
        message,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    await engine.dispose()
