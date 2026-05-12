"""One-off migration: backfill `users` rows for legacy `Session.user_id` strings.

Pre-auth, `Session.user_id` was a free-form string — sometimes an email
("dev.hibi@gmail.com"), sometimes a bare name ("taeho"). After Workstream A
introduced the `users` table, we need stub User rows for those legacy strings
so:

  1. Email-shaped legacy ids round-trip: when "dev.hibi@gmail.com" registers,
     `claim_orphan_sessions(new_id, email)` sweeps their old sessions
     (the existing /auth/register flow already does this, but only if the
     legacy string == the new email).

  2. Non-email legacy ids ("taeho") get a placeholder so the optional
     /auth/claim endpoint can attach them to a freshly-registered account.

Idempotent — re-running reports `0 created, N skipped`. Plaintext passwords
for stub rows are random and discarded (never logged); the user must register
fresh and use /auth/claim or the email-match auto-claim to inherit history.

Usage:
    python scripts/migrate_users.py --dry-run
    python scripts/migrate_users.py
"""

from __future__ import annotations

import argparse
import re
import secrets
import sys
import time
import uuid
from pathlib import Path
from typing import Any

# Allow `python scripts/migrate_users.py` from backend/ — add backend/ to path.
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

import bcrypt  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.storage.db import SessionLocal  # noqa: E402
from app.storage.models import Session as SessionRow  # noqa: E402
from app.storage.models import User  # noqa: E402


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _looks_like_email(value: str) -> bool:
    return bool(_EMAIL_RE.match(value or ""))


def _fabricate_password_hash() -> str:
    """Hash a one-shot random token. Plaintext is discarded immediately."""
    token = secrets.token_urlsafe(32)
    return bcrypt.hashpw(token.encode("utf-8"), bcrypt.gensalt(12)).decode("utf-8")


def _plan_for_legacy(legacy: str) -> dict[str, Any]:
    """Return the User row payload (sans password_hash) we'd insert for `legacy`."""
    if _looks_like_email(legacy):
        email = legacy.strip().lower()
    else:
        email = f"{legacy}@legacy.local".lower()
    return {
        "id": uuid.uuid4().hex,
        "email": email,
        "display_name": None,
        "legacy_user_id": legacy,
    }


def migrate(*, dry_run: bool) -> tuple[int, int]:
    """Returns (created, skipped). Commits unless dry_run."""
    created = 0
    skipped = 0

    with SessionLocal() as s:
        # Distinct legacy strings present in sessions.
        rows = s.execute(
            select(SessionRow.user_id)
            .where(SessionRow.user_id.is_not(None))
            .where(SessionRow.user_id != "")
            .distinct()
        ).all()
        legacy_strings = sorted({row[0] for row in rows if row[0]})

        if not legacy_strings:
            print("No legacy session.user_id values found — nothing to migrate.")
            return (0, 0)

        print(f"Found {len(legacy_strings)} distinct legacy user_id string(s).")

        for legacy in legacy_strings:
            # Idempotency check 1: already migrated by legacy_user_id.
            existing_by_legacy = s.execute(
                select(User).where(User.legacy_user_id == legacy)
            ).scalar_one_or_none()
            if existing_by_legacy is not None:
                print(f"  skip  legacy={legacy!r:30} (User row exists by legacy_user_id)")
                skipped += 1
                continue

            # Idempotency check 2: email-shaped + a User with that email already exists.
            if _looks_like_email(legacy):
                normalized_email = legacy.strip().lower()
                existing_by_email = s.execute(
                    select(User).where(User.email == normalized_email)
                ).scalar_one_or_none()
                if existing_by_email is not None:
                    print(
                        f"  skip  legacy={legacy!r:30} "
                        f"(registered user owns email — they'll auto-claim on register)"
                    )
                    skipped += 1
                    continue

            plan = _plan_for_legacy(legacy)
            print(
                f"  plan  legacy={legacy!r:30} -> "
                f"id={plan['id'][:8]}... email={plan['email']}"
            )

            if not dry_run:
                user = User(
                    id=plan["id"],
                    email=plan["email"],
                    password_hash=_fabricate_password_hash(),
                    display_name=plan["display_name"],
                    legacy_user_id=plan["legacy_user_id"],
                    created_at=time.time(),
                )
                s.add(user)
            created += 1

        if dry_run:
            print("\n[dry-run] no changes committed.")
        else:
            s.commit()

    return (created, skipped)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be created without committing.",
    )
    args = parser.parse_args()

    created, skipped = migrate(dry_run=args.dry_run)
    verb = "Would create" if args.dry_run else "Created"
    print(f"\n{verb} {created} user(s), skipped {skipped} already-present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
