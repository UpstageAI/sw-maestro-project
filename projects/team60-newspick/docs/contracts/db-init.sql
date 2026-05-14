-- NewPick 초기 DB 스키마 (계약)
--
-- BOOT-000 에서 동결. BE 트랙은 이 파일을 그대로 backend/src/main/resources/db/migration/V1__init.sql 로 복사한다.
-- AI 트랙은 Testcontainers 의 init script 으로 그대로 사용한다.
-- 컬럼·타입 변경은 contract-update step 으로만 가능.

CREATE EXTENSION IF NOT EXISTS vector;

-- ─────────────────────────────────────────────────────────────────────
-- articles
-- ─────────────────────────────────────────────────────────────────────
CREATE TABLE articles (
  id                text PRIMARY KEY,
  url               text UNIQUE NOT NULL,
  title             text NOT NULL,
  source            text NOT NULL,
  category          text NOT NULL,
  published_at      timestamptz NOT NULL,
  raw_text          text,
  raw_text_status   text,             -- 'full_text' | 'description_only'
  summary           jsonb,            -- string[]
  keywords          jsonb,            -- string[]
  importance        text,
  context           text,
  importance_score  smallint,
  quiz              jsonb,            -- [{question, answer, explanation}, ...]
  embedding         vector(4096),     -- Solar embedding
  status            text NOT NULL,    -- 'collected' | 'summarized' | 'review_required' | 'skip' | 'description_only'
  retry_count       smallint NOT NULL DEFAULT 0,
  error             text,
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_articles_published_at ON articles (published_at DESC);
CREATE INDEX idx_articles_status       ON articles (status);
CREATE INDEX idx_articles_category     ON articles (category);

-- ─────────────────────────────────────────────────────────────────────
-- daily_reports
-- ─────────────────────────────────────────────────────────────────────
CREATE TABLE daily_reports (
  report_date       date PRIMARY KEY,
  report_updated_at timestamptz NOT NULL,
  briefing          jsonb NOT NULL,   -- {headline, summary}
  flow              jsonb NOT NULL,
  timeline          jsonb NOT NULL,
  keywords          jsonb NOT NULL,
  created_at        timestamptz NOT NULL DEFAULT now()
);

-- 향후 인덱스/halfvec 확장은 별도 V2__*.sql 로 추가
