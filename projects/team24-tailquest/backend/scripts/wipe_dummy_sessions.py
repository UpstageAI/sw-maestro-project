"""One-shot: wipe all sessions/turns rows for a clean slate.

Use cases:
  - Clear out QA/dev dummy data before user-scoped (user_id) data goes live.
  - Recover from a schema migration that added a column SQLAlchemy can't auto-apply
    on SQLite (`Base.metadata.create_all` won't ALTER existing tables).

Run from the backend directory:

    python -m scripts.wipe_dummy_sessions

For a stronger reset (drop + recreate so new columns appear), set
`RECREATE_SCHEMA=1` in the environment.
"""

from __future__ import annotations

import os

from app.storage.db import Base, SessionLocal, engine, init_db
from app.storage import models  # noqa: F401  — register models on Base


def main() -> None:
    if os.environ.get("RECREATE_SCHEMA") == "1":
        print("dropping tables…")
        Base.metadata.drop_all(engine)
    init_db()
    with SessionLocal() as s:
        s.query(models.Turn).delete()
        s.query(models.Session).delete()
        s.commit()
        print("wiped sessions/turns")


if __name__ == "__main__":
    main()
