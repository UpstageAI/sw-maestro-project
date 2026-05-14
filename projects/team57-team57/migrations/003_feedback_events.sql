-- 003_feedback_events.sql — 사장 답글 수정/복사/수동추가 이력 audit
CREATE TABLE IF NOT EXISTS feedback_events (
    event_id     TEXT PRIMARY KEY,
    place_id     TEXT NOT NULL REFERENCES places(place_id),
    review_id    TEXT REFERENCES reviews(review_id) ON DELETE SET NULL,
    reply_id     TEXT REFERENCES replies(reply_id) ON DELETE SET NULL,
    event_type   TEXT NOT NULL,
    before_text  TEXT,
    after_text   TEXT,
    diff_hint    TEXT,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK (event_type IN ('copy', 'edit', 'manual_add', 'diff_hint_generated'))
);
CREATE INDEX IF NOT EXISTS idx_feedback_events_place_created
    ON feedback_events(place_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_feedback_events_review
    ON feedback_events(review_id);
