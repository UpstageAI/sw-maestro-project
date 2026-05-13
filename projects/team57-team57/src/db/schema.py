from __future__ import annotations

from pathlib import Path

from src.db.connection import get_connection

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS stores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    business_type TEXT NOT NULL,
    menu_items_json TEXT NOT NULL DEFAULT '[]',
    price_range TEXT NOT NULL DEFAULT '',
    reply_tone TEXT NOT NULL DEFAULT '정중체',
    reply_samples_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS review_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    raw_input_text TEXT NOT NULL,
    FOREIGN KEY (store_id) REFERENCES stores(id)
);

CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    store_id INTEGER NOT NULL,
    original_text TEXT NOT NULL,
    masked_text TEXT NOT NULL,
    sentiment TEXT,
    sentiment_confidence REAL,
    categories_json TEXT NOT NULL DEFAULT '[]',
    menu_tags_json TEXT NOT NULL DEFAULT '[]',
    generated_replies_json TEXT NOT NULL DEFAULT '[]',
    selected_reply TEXT,
    edited_reply TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES review_sessions(id),
    FOREIGN KEY (store_id) REFERENCES stores(id)
);

CREATE TABLE IF NOT EXISTS feedback_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id INTEGER NOT NULL,
    review_id INTEGER NOT NULL,
    feedback_type TEXT NOT NULL,
    before_value TEXT,
    after_value TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (store_id) REFERENCES stores(id),
    FOREIGN KEY (review_id) REFERENCES reviews(id)
);

CREATE INDEX IF NOT EXISTS idx_review_sessions_store_id ON review_sessions(store_id);
CREATE INDEX IF NOT EXISTS idx_reviews_store_id ON reviews(store_id);
CREATE INDEX IF NOT EXISTS idx_reviews_session_id ON reviews(session_id);
CREATE INDEX IF NOT EXISTS idx_feedback_events_store_id ON feedback_events(store_id);
CREATE INDEX IF NOT EXISTS idx_feedback_events_review_id ON feedback_events(review_id);
"""


def initialize_database(db_path: Path | None = None) -> None:
    with get_connection(db_path) as connection:
        connection.executescript(SCHEMA_SQL)
        connection.commit()


if __name__ == "__main__":
    initialize_database()
    print("Database schema initialized.")
