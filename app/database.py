import importlib
from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def create_tables() -> None:
    _ = importlib.import_module("app.db.models")
    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_reports_compatibility()


def _ensure_sqlite_reports_compatibility() -> None:
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    if "reports" not in inspector.get_table_names():
        return

    report_columns = {column["name"] for column in inspector.get_columns("reports")}
    if "run_id" not in report_columns:
        with engine.begin() as connection:
            _ = connection.execute(text("ALTER TABLE reports ADD COLUMN run_id VARCHAR"))

    inspector = inspect(engine)
    report_indexes = {index["name"] for index in inspector.get_indexes("reports")}
    if "ix_reports_run_id" not in report_indexes:
        with engine.begin() as connection:
            _ = connection.execute(
                text("CREATE UNIQUE INDEX IF NOT EXISTS ix_reports_run_id ON reports (run_id)")
            )
