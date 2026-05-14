"""SQLAlchemy engine + session factory for the SQLite session/turn store.

Sync engine intentionally — async routers wrap calls with `asyncio.to_thread`.
Single SQLite file at `settings.sqlite_path`; `init_db()` is invoked once from
`main.py`'s lifespan.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


_settings = get_settings()
engine = create_engine(
    f"sqlite:///{_settings.sqlite_path}",
    connect_args={"check_same_thread": False},
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    """Create tables if missing. Idempotent — safe to call on every boot."""
    # Importing here ensures models register on Base.metadata before create_all.
    from app.storage import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
