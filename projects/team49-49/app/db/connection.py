from pathlib import Path
import sqlite3


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def resolve_sqlite_path(database_url: str) -> str:
    """Convert an `ICH_DATABASE_URL` value to an absolute on-disk path.

    Accepts both `sqlite:///` URIs and raw filesystem paths. Relative paths
    are anchored to the project root so launching a worker from a sub-folder
    (e.g. a LangGraph dev server inside `graphs/<name>/`) does not silently
    create a fresh, empty database next to the worker.
    """
    raw_path = database_url.removeprefix("sqlite:///") if database_url.startswith("sqlite:///") else database_url
    path = Path(raw_path)
    return str(path if path.is_absolute() else PROJECT_ROOT / path)


def connect_sqlite(path: str | Path) -> sqlite3.Connection:
    db_path = Path(path)
    if db_path.parent and str(db_path.parent) not in ("", "."):
        db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection
