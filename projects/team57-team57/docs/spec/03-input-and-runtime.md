---
title: 03 — Input & Runtime
related:
  - 00-overview.md
  - 01-langgraph-architecture.md
  - 02-data-model.md
  - 04-ux-and-streaming.md
last_updated: 2026-05-08
---

# Input & Runtime

## 입력 방식 — Mock JSON + 버튼 트리거

PROPOSAL의 "붙여넣기 + CSV 보조"도, 인터뷰 중간에 거론된 "Google Places API + cron"도 모두 **의도적으로 채택하지 않습니다** (학습-only 렌즈).

### 데이터 소스: `data/mock_reviews_<place_id>.json`

매장당 25~30건, 총 50~60건 사전 작성. 시간 분포는 최근 6주 (Pattern aggregator의 4주 윈도우가 동작 가능하도록 과거 4주 + 최근 2주).

```json
[
  {
    "review_id": "REV_001_PLACE_001",
    "review_text": "원두향이 정말 좋아요. 라떼 추천합니다 :)",
    "rating": 5,
    "created_at": "2026-04-12T18:34:00Z"
  },
  {
    "review_id": "REV_002_PLACE_001",
    "review_text": "주말 오후엔 자리가 너무 없어요. 30분 기다렸어요.",
    "rating": 2,
    "created_at": "2026-04-13T14:50:00Z"
  },
  ...
]
```

- `review_id`는 PLACE 기준 unique (PRIMARY KEY in SQLite).
- `rating`은 학습 시 *정답 라벨 힌트가 아닌 사용자 별점*으로만 사용 — Classifier에 prompt로 주입하지 않음 (sentiment를 별점으로 도출하면 학습 surface가 사라짐).

### 트리거: Streamlit "fetch batch" 버튼

```python
# Streamlit UI 흐름 (개념)
if st.button("새 리뷰 N건 가져오기"):
    new_reviews = mock_loader.fetch_next(place_id=current_place, n=5)
    for review in new_reviews:
        for chunk in graph.stream({...review...}, config={...}, stream_mode="updates"):
            update_progress_panel(chunk)
```

- 버튼 한 번에 N건 (기본 5건) 처리. cursor는 `data/cursor.json`에 매장별 마지막 처리된 review_id 저장.
- 시연 시 사장이 직접 버튼 누르며 graph 동작을 보임.

## 실행 환경 — Streamlit 단일 프로세스

PROPOSAL이나 인터뷰 중 거론된 "FastAPI 워커 + Streamlit UI 디커플드"는 **의도적으로 채택하지 않습니다**.

이유:
1. cron/async 트리거를 폐기 → FastAPI의 학습 가치(서버 분리)가 본 프로젝트에서 LangGraph 학습이 아닌 web 학습.
2. 단일 프로세스에서 graph.stream()이 자연스럽게 동작 (Streamlit re-run 모델 안에서 generator iterate).
3. 의존성·setup 단순화 → uv sync 한 번 + `streamlit run app.py` 한 줄.

### 옵션 A — 로컬

```bash
cp .env.example .env    # UPSTAGE_API_KEY 입력
uv sync
make seed
make run                # localhost:8501
```

### 옵션 B — Docker

```bash
cp .env.example .env
make docker-build
make docker-up
make docker-seed
# → http://localhost:8501
```

## LLM 호출 — Upstage Solar API

본 프로젝트는 **Upstage Solar API** (`solar-pro2`) 를 사용. SOMA 발급 16만원 free credit 으로 학습·평가·데모 모두 가능.

- 래퍼: `src/llm/upstage.py` — `complete_text_with_meta` / `complete_json_with_meta` (drop-in for cli.py).
- 클라이언트: `openai` SDK + `base_url="https://api.upstage.ai/v1"` (Solar 가 OpenAI 호환).
- Structured output: `response_format={"type": "json_schema", "json_schema": {"name", "schema", "strict": True}}` — schema 강제. classifier·checklist 노드에서 사용.
- Tool use: pattern 노드는 `langchain-upstage` 의 `ChatUpstage.bind_tools([query_review_stats])` 로 LLM-driven tool calling. trace 가 *decide → sql_tool → summarize* 3단계로 분할 노출.
- 한국어 성능: Solar Pro 2 가 Ko-MT-Bench 81.0 (창의 답글 강점). Drafter 의 톤 모방 자연스러움.
- 속도: API 호출 ~1-2s / 1 review main graph ~5s (claude CLI subprocess 대비 ~6배 빠름).
- 인증: `UPSTAGE_API_KEY` 환경변수. 콘솔 https://console.upstage.ai/docs/getting-started.

### 마이그레이션 이력

초기에는 `src/llm/cli.py` 가 `claude` CLI 를 subprocess 로 호출해 Claude Max 구독을 사용했으나, SOMA 가 발급한 16만원 Upstage Solar credit 도입으로 마이그레이션 (2026-05-10). git 히스토리 에 보존 — `src/llm/cli.py` 코드 자체는 제거됨.

## Multi-tenant — 코드 multi, demo single

코드 모든 데이터 접근은 `place_id`를 인자로 받습니다 (Memory Store namespace 학습 surface 확보). 데이터는 2매장 시드:

| place_id | display_name | 상태 | 용도 |
|---|---|---|---|
| `PLACE_001` | 예시 카페 A | 성숙 (메뉴 풀 + 톤 샘플 3건 + 피드백 1건) | demo 주인공, "쓸수록 똑똑해짐" 비교 시연 |
| `PLACE_002` | 예시 식당 B | 신규 (메뉴 비어있음, 톤 샘플 0) | sidebar 매장 전환 시연용, demo에서 비교 대조 |

Streamlit sidebar에 두 매장이 보이고, 사장은 한 매장씩 선택해서 처리. demo는 PLACE_001 위주.

## PII 마스킹

위치: `pii_mask` 노드 (Classifier 직전).

```python
import re

PHONE_RE  = re.compile(r"01[016789][-. ]?\d{3,4}[-. ]?\d{4}")
EMAIL_RE  = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
ACCOUNT_RE = re.compile(r"\b\d{2,4}-\d{2,6}-\d{2,8}\b")  # 한국 계좌 형식 휴리스틱

def mask_pii(text: str) -> str:
    text = PHONE_RE.sub("[전화번호]", text)
    text = EMAIL_RE.sub("[이메일]", text)
    text = ACCOUNT_RE.sub("[계좌]", text)
    return text
```

- 한국어 이름·특수명출은 정규식으로 못 잡음 — 의도적 한계, 학습 surface 외.
- 마스킹된 텍스트만 SQLite `reviews.masked_text`에 저장. `raw_text`도 보존 (회고 시 비교용 — 단 demo·스크린샷에서는 노출 금지).
- mask 후 Classifier 입력은 `masked_text`.

## 실행 흐름 (요약)

```
1. uv sync (의존성)
2. make seed   → seed_places.json + mock_reviews_*.json 로드
                 SQLite places, reviews 테이블 채움
                 Memory Store에 매장 메타·톤 샘플 자동 시드
3. make run    → streamlit 시작
4. UI:
   - sidebar에서 매장 선택
   - "새 리뷰 N건 가져오기" 버튼 클릭
   - 노드 진행 사이드바 + 답글 초안 메인에 표시
   - "복사" 버튼 또는 답글 수정 → tone_samples append
5. 주1회 (수동 트리거): "TOP 3 + 체크리스트 새로고침" 버튼
   - batch graph 실행 (pattern_aggregator → checklist_generator)
```

## 의도적으로 채택하지 않은 것 (요약)

| 후보 | 미채택 사유 |
|---|---|
| Google Places API | 5건 제약, 인증·결제 setup, 학습 surface가 GCP/REST로 흘러감 |
| 네이버 플레이스 크롤링 | ToS 회색, SOMA 평가 리스크 |
| cron / APScheduler | 학습 surface 아님 (수동 버튼이 demo에서 더 명확) |
| FastAPI 워커 | cron 폐기로 명분 소멸, web 학습은 LangGraph 학습이 아님 |
| CSV 업로드 | mock JSON으로 대체, 학습 surface 0 |
| LangGraph Cloud / Server | 등록·배포·비용 부담, 로컬 학습이면 불필요 |

상세 사유는 [`08-risks-and-deferrals.md`](./08-risks-and-deferrals.md).
