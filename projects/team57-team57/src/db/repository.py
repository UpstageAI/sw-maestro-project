from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.db.connection import get_connection, get_database_path
from src.db.schema import initialize_database


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _json_loads(value: str | None, default: Any) -> Any:
    if not value:
        return default
    return json.loads(value)


@dataclass(slots=True)
class StoreRecord:
    id: int
    name: str
    business_type: str
    menu_items: list[str]
    price_range: str
    reply_tone: str
    reply_samples: list[str]
    created_at: str
    updated_at: str


@dataclass(slots=True)
class ReviewSessionRecord:
    id: int
    store_id: int
    created_at: str
    raw_input_text: str


@dataclass(slots=True)
class ReviewRecord:
    id: int
    session_id: int
    store_id: int
    original_text: str
    masked_text: str
    sentiment: str | None
    sentiment_confidence: float | None
    categories: list[str]
    menu_tags: list[str]
    generated_replies: list[str]
    selected_reply: str | None
    edited_reply: str | None
    status: str
    created_at: str


@dataclass(slots=True)
class FeedbackEventRecord:
    id: int
    store_id: int
    review_id: int
    feedback_type: str
    before_value: str | None
    after_value: str | None
    created_at: str


class ReviewAgentRepository:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or get_database_path()

    @classmethod
    def from_env(cls) -> "ReviewAgentRepository":
        return cls(get_database_path())

    def initialize(self) -> None:
        initialize_database(self.db_path)

    def upsert_store(
        self,
        *,
        store_id: int | None,
        name: str,
        business_type: str,
        menu_items: list[str],
        price_range: str,
        reply_tone: str,
        reply_samples: list[str],
    ) -> int:
        with get_connection(self.db_path) as connection:
            if store_id is None:
                cursor = connection.execute(
                    """
                    INSERT INTO stores (
                        name, business_type, menu_items_json, price_range, reply_tone, reply_samples_json
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        name,
                        business_type,
                        _json_dumps(menu_items),
                        price_range,
                        reply_tone,
                        _json_dumps(reply_samples),
                    ),
                )
                connection.commit()
                return int(cursor.lastrowid)

            connection.execute(
                """
                UPDATE stores
                SET name = ?, business_type = ?, menu_items_json = ?, price_range = ?,
                    reply_tone = ?, reply_samples_json = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    name,
                    business_type,
                    _json_dumps(menu_items),
                    price_range,
                    reply_tone,
                    _json_dumps(reply_samples),
                    store_id,
                ),
            )
            connection.commit()
            return store_id

    def get_store(self, store_id: int) -> StoreRecord | None:
        with get_connection(self.db_path) as connection:
            row = connection.execute("SELECT * FROM stores WHERE id = ?", (store_id,)).fetchone()
        return self._store_from_row(row) if row else None

    def list_stores(self) -> list[StoreRecord]:
        with get_connection(self.db_path) as connection:
            rows = connection.execute("SELECT * FROM stores ORDER BY id ASC").fetchall()
        return [self._store_from_row(row) for row in rows]

    def get_store_by_name(self, name: str) -> StoreRecord | None:
        with get_connection(self.db_path) as connection:
            row = connection.execute("SELECT * FROM stores WHERE name = ? ORDER BY id DESC LIMIT 1", (name,)).fetchone()
        return self._store_from_row(row) if row else None

    def create_review_session(self, *, store_id: int, raw_input_text: str) -> int:
        with get_connection(self.db_path) as connection:
            cursor = connection.execute(
                "INSERT INTO review_sessions (store_id, raw_input_text) VALUES (?, ?)",
                (store_id, raw_input_text),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def get_review_session(self, session_id: int) -> ReviewSessionRecord | None:
        with get_connection(self.db_path) as connection:
            row = connection.execute("SELECT * FROM review_sessions WHERE id = ?", (session_id,)).fetchone()
        return self._session_from_row(row) if row else None

    def create_review(
        self,
        *,
        session_id: int,
        store_id: int,
        original_text: str,
        masked_text: str,
        sentiment: str | None = None,
        sentiment_confidence: float | None = None,
        categories: list[str] | None = None,
        menu_tags: list[str] | None = None,
        generated_replies: list[str] | None = None,
        selected_reply: str | None = None,
        edited_reply: str | None = None,
        status: str = "pending",
    ) -> int:
        with get_connection(self.db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO reviews (
                    session_id, store_id, original_text, masked_text, sentiment,
                    sentiment_confidence, categories_json, menu_tags_json, generated_replies_json,
                    selected_reply, edited_reply, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    store_id,
                    original_text,
                    masked_text,
                    sentiment,
                    sentiment_confidence,
                    _json_dumps(categories or []),
                    _json_dumps(menu_tags or []),
                    _json_dumps(generated_replies or []),
                    selected_reply,
                    edited_reply,
                    status,
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def update_review_feedback(
        self,
        *,
        review_id: int,
        edited_reply: str | None = None,
        selected_reply: str | None = None,
        status: str | None = None,
    ) -> None:
        review = self.get_review(review_id)
        if review is None:
            raise ValueError(f"Review not found: {review_id}")

        next_edited_reply = edited_reply if edited_reply is not None else review.edited_reply
        next_selected_reply = selected_reply if selected_reply is not None else review.selected_reply
        next_status = status if status is not None else review.status

        with get_connection(self.db_path) as connection:
            connection.execute(
                """
                UPDATE reviews
                SET edited_reply = ?, selected_reply = ?, status = ?
                WHERE id = ?
                """,
                (next_edited_reply, next_selected_reply, next_status, review_id),
            )
            connection.commit()

    def get_review(self, review_id: int) -> ReviewRecord | None:
        with get_connection(self.db_path) as connection:
            row = connection.execute("SELECT * FROM reviews WHERE id = ?", (review_id,)).fetchone()
        return self._review_from_row(row) if row else None

    def list_reviews_by_store(self, store_id: int, *, limit: int | None = None) -> list[ReviewRecord]:
        sql = "SELECT * FROM reviews WHERE store_id = ? ORDER BY id DESC"
        params: list[Any] = [store_id]
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)

        with get_connection(self.db_path) as connection:
            rows = connection.execute(sql, tuple(params)).fetchall()
        return [self._review_from_row(row) for row in rows]

    def list_recent_edited_replies(self, store_id: int, *, limit: int = 5) -> list[str]:
        with get_connection(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT edited_reply
                FROM reviews
                WHERE store_id = ? AND edited_reply IS NOT NULL AND edited_reply != ''
                ORDER BY id DESC
                LIMIT ?
                """,
                (store_id, limit),
            ).fetchall()
        return [row["edited_reply"] for row in rows]

    def create_feedback_event(
        self,
        *,
        store_id: int,
        review_id: int,
        feedback_type: str,
        before_value: str | None,
        after_value: str | None,
    ) -> int:
        with get_connection(self.db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO feedback_events (
                    store_id, review_id, feedback_type, before_value, after_value
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (store_id, review_id, feedback_type, before_value, after_value),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def list_feedback_events(self, store_id: int) -> list[FeedbackEventRecord]:
        with get_connection(self.db_path) as connection:
            rows = connection.execute(
                "SELECT * FROM feedback_events WHERE store_id = ? ORDER BY id DESC",
                (store_id,),
            ).fetchall()
        return [self._feedback_from_row(row) for row in rows]

    def get_latest_store(self) -> StoreRecord | None:
        with get_connection(self.db_path) as connection:
            row = connection.execute("SELECT * FROM stores ORDER BY id DESC LIMIT 1").fetchone()
        return self._store_from_row(row) if row else None

    def clear_store_history(self, store_id: int) -> None:
        with get_connection(self.db_path) as connection:
            connection.execute(
                "DELETE FROM feedback_events WHERE store_id = ?",
                (store_id,),
            )
            connection.execute(
                "DELETE FROM reviews WHERE store_id = ?",
                (store_id,),
            )
            connection.execute(
                "DELETE FROM review_sessions WHERE store_id = ?",
                (store_id,),
            )
            connection.commit()

    def reset_all_data(self) -> None:
        with get_connection(self.db_path) as connection:
            connection.execute("DELETE FROM feedback_events")
            connection.execute("DELETE FROM reviews")
            connection.execute("DELETE FROM review_sessions")
            connection.execute("DELETE FROM stores")
            connection.execute("DELETE FROM sqlite_sequence")
            connection.commit()

    def count_stores(self) -> int:
        with get_connection(self.db_path) as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM stores").fetchone()
        return int(row["count"])

    def count_reviews(self) -> int:
        with get_connection(self.db_path) as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM reviews").fetchone()
        return int(row["count"])

    def count_reviews_by_store(self, store_id: int) -> int:
        with get_connection(self.db_path) as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM reviews WHERE store_id = ?",
                (store_id,),
            ).fetchone()
        return int(row["count"])

    def count_feedback_events(self) -> int:
        with get_connection(self.db_path) as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM feedback_events").fetchone()
        return int(row["count"])

    def count_feedback_events_by_store(self, store_id: int) -> int:
        with get_connection(self.db_path) as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM feedback_events WHERE store_id = ?",
                (store_id,),
            ).fetchone()
        return int(row["count"])

    def list_recent_reviews(self, *, limit: int = 5) -> list[ReviewRecord]:
        with get_connection(self.db_path) as connection:
            rows = connection.execute(
                "SELECT * FROM reviews ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._review_from_row(row) for row in rows]

    def list_recent_reviews_by_store(self, store_id: int, *, limit: int = 5) -> list[ReviewRecord]:
        with get_connection(self.db_path) as connection:
            rows = connection.execute(
                "SELECT * FROM reviews WHERE store_id = ? ORDER BY id DESC LIMIT ?",
                (store_id, limit),
            ).fetchall()
        return [self._review_from_row(row) for row in rows]

    def list_recent_feedback_events(self, *, limit: int = 5) -> list[FeedbackEventRecord]:
        with get_connection(self.db_path) as connection:
            rows = connection.execute(
                "SELECT * FROM feedback_events ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._feedback_from_row(row) for row in rows]

    def list_recent_feedback_events_by_store(self, store_id: int, *, limit: int = 5) -> list[FeedbackEventRecord]:
        with get_connection(self.db_path) as connection:
            rows = connection.execute(
                "SELECT * FROM feedback_events WHERE store_id = ? ORDER BY id DESC LIMIT ?",
                (store_id, limit),
            ).fetchall()
        return [self._feedback_from_row(row) for row in rows]

    @staticmethod
    def _store_from_row(row: Any) -> StoreRecord:
        return StoreRecord(
            id=row["id"],
            name=row["name"],
            business_type=row["business_type"],
            menu_items=_json_loads(row["menu_items_json"], []),
            price_range=row["price_range"],
            reply_tone=row["reply_tone"],
            reply_samples=_json_loads(row["reply_samples_json"], []),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _session_from_row(row: Any) -> ReviewSessionRecord:
        return ReviewSessionRecord(
            id=row["id"],
            store_id=row["store_id"],
            created_at=row["created_at"],
            raw_input_text=row["raw_input_text"],
        )

    @staticmethod
    def _review_from_row(row: Any) -> ReviewRecord:
        return ReviewRecord(
            id=row["id"],
            session_id=row["session_id"],
            store_id=row["store_id"],
            original_text=row["original_text"],
            masked_text=row["masked_text"],
            sentiment=row["sentiment"],
            sentiment_confidence=row["sentiment_confidence"],
            categories=_json_loads(row["categories_json"], []),
            menu_tags=_json_loads(row["menu_tags_json"], []),
            generated_replies=_json_loads(row["generated_replies_json"], []),
            selected_reply=row["selected_reply"],
            edited_reply=row["edited_reply"],
            status=row["status"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _feedback_from_row(row: Any) -> FeedbackEventRecord:
        return FeedbackEventRecord(
            id=row["id"],
            store_id=row["store_id"],
            review_id=row["review_id"],
            feedback_type=row["feedback_type"],
            before_value=row["before_value"],
            after_value=row["after_value"],
            created_at=row["created_at"],
        )
