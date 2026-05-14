"""One-off: rebuild the SQLite `materials` table from existing Chroma
collections, optionally assigning to a specific user.

Before per-user scoping, material metadata was global. After the auth
refactor, each row needs a `user_id`. This script enumerates Chroma
collections matching `user_<material_id>`, looks up the count, and inserts
a `Material` row with status='ready' assigned to the user identified by
`--email <email>`. Without `--email`, rows get `user_id=NULL` (invisible
to all users until manually claimed).

Names default to the material_id since the original filename was lost when
the in-memory dict was wiped — the user can rename via UI later (when that
ships) or via SQL.
"""

from __future__ import annotations

import argparse
import time

from sqlalchemy import select

from app.services import user_store
from app.storage.chroma import _get_client  # noqa: PLC2701
from app.storage.db import SessionLocal
from app.storage.models import Material, User


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--email",
        help="Assign backfilled materials to this user (must already be registered).",
    )
    args = parser.parse_args()

    user_id: str | None = None
    if args.email:
        with SessionLocal() as s:
            owner = s.execute(
                select(User).where(User.email == args.email.lower())
            ).scalar_one_or_none()
        if owner is None:
            raise SystemExit(
                f"user not found: {args.email}. Register first via /auth/register."
            )
        user_id = owner.id
        print(f"assigning to {owner.email} ({user_id[:12]}..)")
    else:
        print("no --email — rows will be unassigned (invisible to all users)")

    client = _get_client()
    collections = client.list_collections()
    user_collections = [c for c in collections if c.name.startswith("user_")]
    if not user_collections:
        print("no user_* Chroma collections to backfill")
        return

    now = time.time()
    inserted = 0
    skipped = 0
    with SessionLocal() as s:
        for col in user_collections:
            material_id = col.name.removeprefix("user_")
            existing = s.get(Material, material_id)
            if existing is not None:
                skipped += 1
                continue
            count = col.count()
            row = Material(
                id=material_id,
                user_id=user_id,
                name=material_id,
                kind="github",  # heuristic — most legacy orphans were github
                status="ready" if count > 0 else "failed",
                chunks=count,
                error=None if count > 0 else "Chroma 컬렉션이 비어있어 재추가 권장",
                created_at=now,
                updated_at=now,
            )
            s.add(row)
            inserted += 1
            print(f"  + {material_id}: {count} chunks")
        s.commit()
    print(f"\nbackfilled {inserted} materials, skipped {skipped} already present")


if __name__ == "__main__":
    main()
