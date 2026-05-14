-- 002_review_text_hash.sql — partial UNIQUE index on (place_id, raw_text_hash); backfill handled in Python.

ALTER TABLE reviews ADD COLUMN raw_text_hash TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS uq_reviews_place_hash
  ON reviews(place_id, raw_text_hash)
  WHERE raw_text_hash IS NOT NULL;
