import os
from collections.abc import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./schedules.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _upgrade_sqlite_schema()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _upgrade_sqlite_schema() -> None:
    if not DATABASE_URL.startswith("sqlite"):
        return

    with engine.begin() as conn:
        columns = conn.execute(text("PRAGMA table_info(schedules)")).mappings().all()
        column_names = {column["name"] for column in columns}
        if "schedule_type" not in column_names:
            conn.execute(text("ALTER TABLE schedules ADD COLUMN schedule_type VARCHAR(80)"))
        if "google_event_id" not in column_names:
            conn.execute(text("ALTER TABLE schedules ADD COLUMN google_event_id VARCHAR(255)"))
