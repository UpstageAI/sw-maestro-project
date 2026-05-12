"""One-off: remove orphan unanswered turns from existing sessions.

Caused by the pre-fix BE bug where /sessions submit pre-allocated a follow-up
turn that FE then ignored when pivoting to a switchSeed (uncertain/incorrect
answer paths). Survivors clutter analysis history as ghost questions.

Strategy: for each session, keep the *last* unanswered turn (it's the active
question the user is supposed to answer) and delete all earlier unanswered
turns. Answered turns are never touched.
"""

from sqlalchemy import select

from app.storage.db import SessionLocal
from app.storage.models import Turn, Session


def main() -> None:
    with SessionLocal() as s:
        sessions = s.execute(select(Session)).scalars().all()
        total_deleted = 0
        for sess in sessions:
            turns = (
                s.execute(
                    select(Turn)
                    .where(Turn.session_id == sess.id)
                    .order_by(Turn.seq)
                )
                .scalars()
                .all()
            )
            unanswered = [t for t in turns if t.answer is None]
            if len(unanswered) <= 1:
                continue
            to_delete = unanswered[:-1]
            print(
                f"session {sess.id}: {len(turns)} turns, "
                f"{len(unanswered)} unanswered, deleting {len(to_delete)}"
            )
            for t in to_delete:
                print(f"  - seq={t.seq} id={t.id} Q={(t.question or '')[:60]!r}")
                s.delete(t)
            total_deleted += len(to_delete)
        s.commit()
        print(f"\nTotal turns deleted: {total_deleted}")


if __name__ == "__main__":
    main()
