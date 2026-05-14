-- 001_init.sql — initial schema
-- See docs/spec/02-data-model.md

CREATE TABLE IF NOT EXISTS places (
  place_id     TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS reviews (
  review_id        TEXT PRIMARY KEY,
  place_id         TEXT NOT NULL REFERENCES places(place_id),
  raw_text         TEXT NOT NULL,
  masked_text      TEXT,
  sentiment        TEXT,
  confidence       REAL,
  risk_flag        INTEGER DEFAULT 0,
  risk_reason      TEXT,
  created_at       TEXT NOT NULL,
  processed_at     TEXT,
  CHECK (sentiment IN ('positive', 'negative', 'neutral') OR sentiment IS NULL)
);
CREATE INDEX IF NOT EXISTS idx_reviews_place_created   ON reviews(place_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_reviews_place_sentiment ON reviews(place_id, sentiment);

CREATE TABLE IF NOT EXISTS review_categories (
  review_id   TEXT NOT NULL REFERENCES reviews(review_id) ON DELETE CASCADE,
  category    TEXT NOT NULL,
  confidence  REAL NOT NULL,
  PRIMARY KEY (review_id, category)
);
CREATE INDEX IF NOT EXISTS idx_categories_place ON review_categories(category);

CREATE TABLE IF NOT EXISTS replies (
  reply_id     TEXT PRIMARY KEY,
  review_id    TEXT NOT NULL REFERENCES reviews(review_id) ON DELETE CASCADE,
  draft_text   TEXT NOT NULL,
  drafter_used TEXT NOT NULL,
  final_text   TEXT,
  copied_at    TEXT,
  edited_at    TEXT,
  created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_replies_review ON replies(review_id);
