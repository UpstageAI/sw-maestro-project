---
title: 02 — Data Model
related:
  - 00-overview.md
  - 01-langgraph-architecture.md
  - 05-personalization.md
last_updated: 2026-05-08
---

# Data Model

두 저장소를 사용합니다:

- **SQLite** — 관계 데이터 (places, reviews, replies, 분류 결과). PatternAgent의 SQL 집계 쿼리 대상.
- **LangGraph Memory Store** — 매장별 KV/문서 (메뉴·톤 샘플·피드백). cross-thread 영속.

분리 원칙: SQLite는 *append-only event log + indexed view*, Memory Store는 *mutable per-tenant state*.

## SQLite schema

DB 위치: `data/review_ops.db` (gitignored, `migrations/001_init.sql` 실행으로 생성).

```sql
-- 매장 (참조용 — 실제 메타는 Memory Store에 있음)
CREATE TABLE places (
  place_id     TEXT PRIMARY KEY,    -- e.g. "PLACE_001"
  display_name TEXT NOT NULL,       -- 매장 이름 (UI 노출용 캐시)
  created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 리뷰 원문 + 분류 결과 (review_categories와 다대다)
CREATE TABLE reviews (
  review_id        TEXT PRIMARY KEY,
  place_id         TEXT NOT NULL REFERENCES places(place_id),
  raw_text         TEXT NOT NULL,
  masked_text      TEXT,                 -- pii_mask 후
  sentiment        TEXT,                 -- 'positive' | 'negative' | 'neutral'
  confidence       REAL,                 -- 0.0 ~ 1.0
  risk_flag        INTEGER DEFAULT 0,    -- bool
  risk_reason      TEXT,
  created_at       TEXT NOT NULL,        -- 리뷰 발생 시각 (mock JSON에서 주입)
  processed_at     TEXT,                 -- graph 실행 완료 시각
  CHECK (sentiment IN ('positive', 'negative', 'neutral') OR sentiment IS NULL)
);
CREATE INDEX idx_reviews_place_created ON reviews(place_id, created_at DESC);
CREATE INDEX idx_reviews_place_sentiment ON reviews(place_id, sentiment);

-- 카테고리 다대다
CREATE TABLE review_categories (
  review_id   TEXT NOT NULL REFERENCES reviews(review_id) ON DELETE CASCADE,
  category    TEXT NOT NULL,    -- '맛' | '서비스' | '가격' | '대기시간' | '위생'
  confidence  REAL NOT NULL,    -- 카테고리별 confidence
  PRIMARY KEY (review_id, category)
);
CREATE INDEX idx_categories_place ON review_categories(category);

-- 답글 (draft + 사장 수정본)
CREATE TABLE replies (
  reply_id     TEXT PRIMARY KEY,
  review_id    TEXT NOT NULL REFERENCES reviews(review_id) ON DELETE CASCADE,
  draft_text   TEXT NOT NULL,         -- AI 초안
  drafter_used TEXT NOT NULL,         -- 'thanks' | 'apology' | 'apology_lowconf' | 'neutral'
  final_text   TEXT,                  -- 사장이 수정한 최종 (NULL이면 미수정 = draft 그대로 채택)
  copied_at    TEXT,                  -- 사장이 "복사" 버튼 누른 시각 (NULL이면 미채택)
  edited_at    TEXT,                  -- 사장이 수정한 시각
  created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_replies_review ON replies(review_id);
```

### Pattern 집계 쿼리 예시

```sql
-- 최근 4주 부정 리뷰의 카테고리별 빈도 TOP 3
SELECT rc.category, COUNT(*) AS freq
FROM review_categories rc
JOIN reviews r ON rc.review_id = r.review_id
WHERE r.place_id = ?
  AND r.sentiment = 'negative'
  AND r.created_at >= datetime('now', '-28 days')
GROUP BY rc.category
ORDER BY freq DESC
LIMIT 3;
```

이 쿼리는 SQL query tool ([`01-langgraph-architecture.md`](./01-langgraph-architecture.md) 참고)이 LLM에게 노출하는 함수의 내부 구현. LLM은 `query_review_stats(place_id, since, group_by)` 인터페이스만 호출.

## LangGraph Memory Store

LangGraph의 `Store` API를 사용. In-memory 또는 SQLite-backed (`InMemoryStore` / `AsyncSqliteStore`) 중 W1 D1에 결정 — **권장: `InMemoryStore` + 시작 시 `data/seed_places.json` 로드 + 종료 시 `data/store_dump.json` 저장**. 학습-only 단순화.

### Namespace 구조

```python
# 매장 메타 (단일)
store.put(
    namespace=(place_id, "metadata"),
    key="profile",
    value={
        "display_name": "...",
        "category": "카페" | "음식점" | ...,
        "menus": [{"name": "...", "price": ...}, ...],   # 5~10개
        "price_range": "₩₩",
        "tone_preference": "정중체" | "친근체" | "격식체",
        "address": "...",       # optional
        "completeness": 0.85,   # 채워진 필드 비율 (UI 진척도용)
    }
)

# 톤 샘플 (다수, append-only)
store.put(
    namespace=(place_id, "tone_samples"),
    key=sample_id,            # uuid
    value={
        "review_text": "...",  # 어떤 리뷰에 대한 답이었는지
        "ai_draft": "...",     # AI 초안
        "owner_final": "...",  # 사장이 수정한 최종
        "drafter_used": "apology",
        "created_at": "2026-..."
    }
)

# 피드백 / diff hint (다수, append-only)
store.put(
    namespace=(place_id, "feedback"),
    key=feedback_id,          # uuid
    value={
        "diff_hint": "사장은 더 짧은 종결어 선호, 이모티콘 삭제 경향",
        "based_on_sample_ids": [sample_id_1, sample_id_2],
        "generated_at": "2026-..."
    }
)
```

### 읽기 패턴 — `load_context` 노드

```python
# 매장 메타 1건
profile_items = store.search((place_id, "metadata"))
profile = profile_items[0].value if profile_items else {}

# 최근 톤 샘플 3건 (Drafter few-shot용)
sample_items = store.search((place_id, "tone_samples"), limit=3)
tone_samples = [item.value for item in sample_items]

# 최근 피드백 hint 1건
feedback_items = store.search((place_id, "feedback"), limit=1)
feedback_hints = [item.value["diff_hint"] for item in feedback_items]
```

`store.search`는 namespace prefix matching + `limit` 지원. 정렬은 default(추가 시간 역순)이라 별도 정렬 불필요.

### 쓰기 시점

- 매장 메타: 첫 진입 시 form 입력 직후 (또는 seed 자동 로드).
- 톤 샘플: 사장이 답글을 수정하고 "복사" 누른 시점 (`replies.edited_at`이 채워질 때).
- 피드백 / diff hint: 톤 샘플 append 후 비동기로 Haiku에게 "AI 원본 vs 사장 최종" diff를 한 줄로 요약 요청 → `feedback` namespace에 put.

상세 메커니즘은 [`05-personalization.md`](./05-personalization.md).

## 카테고리 처리 정책

PROPOSAL의 5대 카테고리 멀티라벨은 **유지하되 라우팅에는 사용하지 않음** (학습-only 결정):

- Classifier 출력에 `categories: list[str]` (멀티라벨 가능, 신뢰도별 정렬)이 포함됨.
- SQLite `review_categories` 테이블에 다대다로 저장 → PatternAgent가 SQL 집계.
- Drafter는 `categories[0]` (primary)을 prompt parameter로 받아 답글에 반영하지만 **노드 분기는 sentiment만**.

이 절충안의 장점·단점은 [`08-risks-and-deferrals.md`](./08-risks-and-deferrals.md) 참조.

## Seed 데이터 구조

`data/seed_places.json`:

```json
{
  "places": [
    {
      "place_id": "PLACE_001",
      "display_name": "예시 카페 A (성숙)",
      "metadata": { "category": "카페", "menus": [...], "tone_preference": "정중체", ... },
      "tone_samples": [
        { "review_text": "...", "ai_draft": "...", "owner_final": "...", ... },
        ... (3건)
      ],
      "feedback": [
        { "diff_hint": "...", ... }
      ]
    },
    {
      "place_id": "PLACE_002",
      "display_name": "예시 식당 B (신규)",
      "metadata": { "category": "음식점", "menus": [], "tone_preference": "정중체" },
      "tone_samples": [],
      "feedback": []
    }
  ]
}
```

W1 D1에 작성. 첫 실행 시 Memory Store에 자동 로드.
