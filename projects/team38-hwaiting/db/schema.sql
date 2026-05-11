-- =====================================================================
-- 노트북 추천 챗봇 — SQLite 스키마 (PRD US-005 / FR-7 / 부록 A)
--
-- 사용법:
--   sqlite3 db/laptops.db < db/schema.sql
--
-- 컬럼 정책 (부록 A 매트릭스 참조):
--   - 9개 스펙 슬롯 + 메타데이터(product_name, thumbnail_url, detail_url, crawled_at)
--   - 단위: weight_kg(kg), screen_inch(inch), ram_gb/storage_gb(GB),
--          price_krw(KRW), brightness_nits(nits), resolution("WxH" 문자열)
--   - 가격·CPU·램·저장 4컬럼은 NOT NULL (FR-6: 결측 시 적재 대상에서 제외)
--   - brightness_nits 만 NULL 허용 (OQ-7 / Node D `(IS NULL OR >= ?)`)
--   - detail_url UNIQUE → FR-8 의 UPSERT(`ON CONFLICT(detail_url) DO UPDATE`) 키
--
-- 인덱스: US-005 의 5개 컬럼(가격·무게·화면·램·저장)
-- =====================================================================

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS laptops (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name      TEXT    NOT NULL,
    screen_inch       REAL    NOT NULL,
    weight_kg         REAL    NOT NULL,
    os                TEXT    NOT NULL,
    resolution        TEXT    NOT NULL,            -- "1920x1080" 등 canonical WxH
    brightness_nits   INTEGER,                     -- NULL 허용 (목록 페이지 결측 잦음)
    cpu               TEXT    NOT NULL,
    ram_gb            INTEGER NOT NULL,
    storage_gb        INTEGER NOT NULL,
    price_krw         INTEGER NOT NULL,
    thumbnail_url     TEXT,
    detail_url        TEXT    NOT NULL UNIQUE,     -- UPSERT 키 (FR-8)
    crawled_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- 인덱스 (US-005): 자주 필터링되는 5개 컬럼
CREATE INDEX IF NOT EXISTS idx_laptops_price_krw   ON laptops(price_krw);
CREATE INDEX IF NOT EXISTS idx_laptops_weight_kg   ON laptops(weight_kg);
CREATE INDEX IF NOT EXISTS idx_laptops_screen_inch ON laptops(screen_inch);
CREATE INDEX IF NOT EXISTS idx_laptops_ram_gb      ON laptops(ram_gb);
CREATE INDEX IF NOT EXISTS idx_laptops_storage_gb  ON laptops(storage_gb);
