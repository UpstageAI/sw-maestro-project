from __future__ import annotations

import os
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path("data/app.db")


def get_database_path() -> Path:
    configured = os.getenv("REVIEW_AGENT_DB_PATH")
    return Path(configured) if configured else DEFAULT_DB_PATH


def ensure_database_directory(db_path: Path | None = None) -> Path:
    target = db_path or get_database_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    target = ensure_database_directory(db_path)
    connection = sqlite3.connect(target)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection

