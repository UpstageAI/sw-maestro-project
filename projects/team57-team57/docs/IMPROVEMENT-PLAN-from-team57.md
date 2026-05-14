# 개선 플랜 — team57에서 차용해 review-ops-agent 강화

> 비교 문서([COMPARISON-team57-vs-review-ops-agent.md](./COMPARISON-team57-vs-review-ops-agent.md))에서 발견한 **team57이 더 잘한 영역** 중, review-ops-agent의 LangGraph 정통성·Solar 베팅을 해치지 않으면서 **신뢰성·UX**를 끌어올리는 7개 항목.
>
> 범위: **P0 (안전망 5개) + UX 보강 (2개)**. 예상 작업량 2~3일.
>
> *제외*: Provider Protocol 추상화·LangGraph fallback·다중 입력 파싱은 현재 베팅 방향과 가치 대비 비용이 맞지 않아 P2로 지연 (부록 §A 참조).

---

## 결정의 기본 원칙

플랜의 각 항목은 다음 3가지 중 최소 하나를 만족해야 한다:

1. **현재 코드에 *없는* 안전망**을 추가 (있는 것을 다시 짜는 게 아니라)
2. LangGraph **노드/엣지/state reducer 정합성**을 깨지 않는다
3. Solar 단일 모델·SQLite+Memory Store 이중 백엔드 베팅을 **유지**한다

---

## P0 — 안전망 (5개)

### P0-1. Mock LLM provider — 데모/CI/오프라인 fallback

**갭**: `src/llm/upstage.py:43-48` 에서 `UPSTAGE_API_KEY` 미설정 시 `UpstageError`를 즉시 raise. team57은 `get_provider()` 우선순위에서 키 없으면 `MockProvider`로 자동 폴백 (`team57/src/llm/provider.py:43-74`).

**왜 도입**:
- SOMA 데모 당일 인터넷·API 키 문제 시 발표가 통째로 막힘. 단일 실패점.
- CI에서 LLM 호출 없이도 그래프 골격 회귀 테스트 가능
- LangGraph 학습자가 fork 받아 즉시 실행 가능 (현재는 API 키 없으면 Streamlit이 즉시 stop)

**무엇을**:
- `src/llm/upstage_mock.py` 신설 — `complete_text_with_meta`, `complete_json_with_meta` 의 결정론적 더미 응답
  - classifier: review_text 길이 hash로 sentiment 결정 (양수→positive, 음수 키워드 매칭→negative)
  - drafter: "[MOCK 답글] {tone} 톤으로 답변 생성됨" 같은 식별 가능한 placeholder
  - pattern.llm_summarize: 입력 카테고리 그대로 재포맷
- `src/llm/__init__.py` — env `REVIEW_OPS_LLM=mock` 또는 `UPSTAGE_API_KEY` 미설정 시 mock으로 라우팅
- `upstage.py`의 `complete_text_with_meta`, `complete_json_with_meta`, `pattern.py`의 `ChatUpstage(...)` 3곳에서 환경변수 분기

**Trade-off**:
- ⭕ 데모 안정성 + CI 가능 + onboarding 비용↓
- △ env 분기가 3곳 추가 — 한 곳에서 라우팅 (`src/llm/router.py`)으로 응집하면 완화

**완료 기준**:
- `unset UPSTAGE_API_KEY; make smoke` 가 통과
- UI에서 mock 모드 동작 시 사이드바에 "🟡 MOCK 모드" 뱃지 표시

**예상**: 4~6h

---

### P0-2. classifier per-review 실패 처리

**갭**: `src/graph/nodes/classifier.py:78-122` 에 try/except 없음. Solar API가 한 번 5xx 내면 `graph.stream()` 가 통째로 중단 → 그 다음 4건도 처리 못 함. team57은 `classifier.py:14-40` 에서 2회 재시도 후 review 단위 `status="analysis_failed"` 처리하고 다음 리뷰 계속 진행.

**왜 도입**:
- "새 리뷰 5건 가져오기" 한 클릭에 5건 처리 도중 1건만 실패해도 사장 입장에선 전부 실패로 보임
- 현재 chat agent의 `analyze_new_reviews` 도 `except Exception: processed.append({"error": str(e)})` 패턴을 이미 쓰고 있어 — *그래프 안과 밖이 fail mode가 다름*

**무엇을**:
- `classifier_node` 에 단일 retry (최대 2회) + 실패 시 state에 `classification_failed: True` 플래그
- `route_by_sentiment` 분기에 `"classification_failed"` 분기 추가 → `noop_drafter` (또는 기존 neutral_drafter로 우회) 후 `memory_save`로 빠지되 reply에 `"분류 실패 — 사장님이 직접 응대 권장"` placeholder
- `state.py:ReviewState` 에 `classification_failed: bool` 필드 추가

**Trade-off**:
- ⭕ 부분 실패 격리. 5건 중 1건 실패해도 4건은 정상 흐름
- △ 그래프 다이어그램에 "실패 분기"가 추가되어 발표 시 설명 한 줄 늘어남 — 다만 안전성 시연 포인트로 활용 가능
- △ `route_by_sentiment` 의 4분기가 5분기 되면서 `apology_lowconf` 와 의미 중첩 위험 → 별도 분기로 명확화

**완료 기준**:
- 가짜 API 500 주입 (mock에서 1건 실패하도록) → 5건 중 4건 정상 카드 생성
- 실패 카드에 "분류 실패" 뱃지 + 사장이 직접 답글 작성하는 UI 노출

**예상**: 3~4h

---

### P0-3. 비한국어 리뷰 필터

**갭**: `src/graph/nodes/pii_mask.py` 에서 raw_text를 그대로 통과. team57은 `input_parser.py:28-32` 에서 `contains_korean(masked)` 체크 → 영어/스팸 리뷰는 LLM 호출 전에 제외.

**왜 도입**:
- Solar Pro 2는 한국어 최적화. 영어 리뷰는 분류 품질도 떨어지고 token도 낭비
- 골든셋 평가가 한국어 기준이라 노이즈 유입 시 정확도 지표 오염

**무엇을**:
- `pii_mask_node` 에 한국어 비율 체크 추가 (`re.search(r"[가-힣]", masked_text)` 또는 비율 30% 이상)
- 통과 못 한 경우 state에 `lang_skip: True` 세팅 → conditional edge로 `noop` 노드 (또는 P0-2와 동일하게 classification_failed 경로 재활용)
- `node_log` 에 `transform` kind로 `"비한국어 — graph skip"` summary 기록

**Trade-off**:
- ⭕ LLM 호출 비용 절감 (한국어 매장 가정 하에)
- △ 한국어 + 영어 혼합 리뷰는 임계값 튜닝 필요 — 30%/50% 등으로 골든셋에 부정확 사례 없는지 확인

**완료 기준**:
- 영어 리뷰 mock 1건 주입 → classifier 호출 0, trace에 lang_skip 기록

**예상**: 2h

---

### P0-4. 중복 리뷰 감지

**갭**: `src/store/sqlite.py:53-63` `insert_raw_review` 는 `review_id` PK 충돌만 막을 뿐, *본문 중복* 은 그대로 적재. team57은 `input_parser.py:22-25` 에서 `normalize_whitespace` 후 `seen: set[str]` 으로 중복 제거.

**왜 도입**:
- mock JSON에서 같은 리뷰가 두 번 들어가면 LLM 호출 2회·집계 왜곡
- 외부 플랫폼 연동 시 (out-of-scope이지만 향후) crawler 중복은 흔한 시나리오

**무엇을**:
- `migrations/002_review_text_hash.sql` — `reviews` 테이블에 `raw_text_hash TEXT` 컬럼 + `UNIQUE (place_id, raw_text_hash)` 부분 인덱스
- `insert_raw_review` 에 SHA1(normalize(raw_text)) 계산해서 INSERT OR IGNORE
- seed 스크립트도 같은 normalize 통과

**Trade-off**:
- ⭕ 정확한 중복 탐지. 멱등한 seed
- △ migration 1개 추가 — 기존 DB는 `make docker-down && rm data/review_ops.db && make seed` 필요. README에 한 줄 명시
- △ 거의-중복 (오타 1자 차이)은 못 잡음. 임베딩까지 가면 P2

**완료 기준**:
- 같은 본문 리뷰 2건 시드 → DB에 1건만 들어감

**예상**: 2~3h

---

### P0-5. 위험 표현 후처리 safety net

**갭**: 드래프터 4종 (`drafters.py`) 모두 prompt-level guidance ("가격/할인 약속 금지")만으로 안전성 처리. team57은 `safety_tools.py:30-39` 에서 `RISKY_PHRASES = ("환불", "할인", "법적 책임", ...)` 후처리 치환 + `safety_notes` 로 trace.

**왜 도입**:
- prompt만 믿는 건 LLM 일탈 시 0% 안전성. *Defense in depth* 가 정통 LLM 앱 설계
- `risk_flag=true` 케이스만이 아니라 모든 sentiment에서 발생 가능 (긍정 리뷰에 "환불해드릴게요" 같은 본 적 없는 일탈)

**무엇을**:
- `src/graph/tools/safety_filter.py` — `filter_risky_phrases(text) -> tuple[str, list[str]]`
  - 치환 사전: `{"환불": "별도 안내", "할인": "별도 안내", "전액 보상": "개별 응대", "법적 책임": "(검토)", "100% 무료": "(검토)"}`
- 4개 drafter 노드의 `_draft()` 내부에서 `complete_text_with_meta` 결과 직후 적용
- state에 `safety_notes: list[str]` 필드 추가 — UI 카드에 "⚠️ 안전 필터 적용: 환불→별도 안내" 같은 줄 표시 (가시성이 평가 포인트)

**Trade-off**:
- ⭕ 결정론적 안전 baseline + 평가자에게 시연 포인트
- △ 자연스러운 답글에서 "별도 안내"로 어색해질 수 있음 → 사전을 짧게 유지, 치환 시 *반드시* trace에 노출해 사장이 인지 가능하게
- △ team57과 동일 사전을 그대로 쓰면 표절 시비. 카테고리는 같되 어휘는 review-ops-agent 컨텍스트에 맞게 재작성

**완료 기준**:
- "환불" 단어를 강제로 prompt 응답에 박은 mock 테스트 → 답글에 "별도 안내"로 치환되고 카드에 safety_notes 노출

**예상**: 2~3h

---

## UX 보강 (2개)

### UX-1. 원클릭 데모 리셋

**갭**: `src/ui/app.py:110-113` "데모 초기화" 버튼은 `db.reset_database()` 만 호출하고 사장이 다시 `make seed`를 수동 실행해야 함 → "DB 초기화 완료. 다시 `make seed`를 실행하세요." 토스트. team57은 `initialize_demo_store_tool` (`db_tools.py:129-175`) 가 reset + 매장 + 18개 시드 리뷰까지 한 번에 처리.

**왜 도입**:
- 발표 직전 깨끗한 상태로 복원할 때 터미널을 오가야 함 → 실시간 데모 흐름 깨짐
- 평가자가 fork 후 click 한 번에 시연 가능해야 onboarding 비용 0

**무엇을**:
- `src/scripts/seed.py` 의 시드 로직을 import 가능한 함수 `seed_all()` 로 리팩토링 (현재 `__main__` 만 있을 가능성 — 확인 후)
- `db.reset_database()` 호출 직후 `seed_all()` 같이 호출
- 토스트 메시지: "데모 리셋 완료 (매장 N개, 리뷰 M건 재시드)" → 페이지 자동 새로고침 (`st.rerun()`)

**Trade-off**:
- ⭕ 발표·시연 워크플로우 매끄러움
- △ 사용자가 매장 메타를 수동 편집한 상태가 있으면 한 클릭에 날아감 → 버튼에 `type="secondary"` + 2단계 confirm dialog

**완료 기준**:
- 버튼 한 번 클릭 → 5초 내 깨끗한 데모 상태 복원 + 페이지에 시드 매장 다시 등장

**예상**: 2h

---

### UX-2. feedback 감사 추적 테이블

**갭**: `migrations/001_init.sql` 의 `replies.copied_at/edited_at/final_text` 가 *최종 상태* 만 기록. 사장이 같은 답글을 여러 번 수정했을 때 변경 이력이 사라짐. team57의 `feedback_events` 테이블 (`schema.py:47-57`)은 `before_value`/`after_value` 별도 row로 누적.

**왜 도입**:
- "사장 수정 → diff hint 생성 → 다음 답글에 hint 주입" 이 review-ops-agent의 *핵심 개인화 루프*인데, 정작 hint 생성 이력이 SQLite에 안 남음 (memory store JSON dump에만 있음)
- 회고·평가 시 "어떤 수정이 hint로 이어졌나"를 SQL로 추적 가능해야 골든셋 분석이 쉬워짐
- multi-tenant 운영 시 "사장님 답글 수정 빈도" 같은 KPI 산출 가능

**무엇을**:
- `migrations/003_feedback_events.sql` — `feedback_events(id, place_id, review_id, reply_id, event_type, before_text, after_text, diff_hint, created_at)`
- `mark_reply_edited` (`sqlite.py:121-126`) 내부에서 변경 전 final_text를 before로 stash 후 INSERT INTO feedback_events
- chat agent의 `add_owner_reply` 도 같은 테이블에 `event_type="manual_add"` 로 기록
- `event_type` enum: `"copy" | "edit" | "manual_add" | "diff_hint_generated"`

**Trade-off**:
- ⭕ 영구 audit trail + 추후 hint 품질 분석 가능 + 정통 multi-tenant 패턴
- △ 테이블 1개·코드 3곳 수정 — 적당히 잘 짜야 함
- △ 사장이 같은 답글을 빈번히 수정하면 row 폭증 → place_id+created_at 인덱스 + 90일 retention 정책 추가는 P2

**완료 기준**:
- 답글 1건 2회 수정 → `feedback_events` 에 row 2개 적재. before/after 모두 보존
- 사이드바 expander "💾 최근 사장 수정 이력" 에 최근 5건 노출

**예상**: 3~4h

---

## 권장 실행 순서

의존성과 가치 곡선을 고려한 순서:

```
1. P0-1 (Mock provider) ─────┐
2. P0-3 (비한국어 필터)      ├─ Mock 위에서 통합 회귀 가능
3. P0-2 (classifier 실패 처리) ┘
                              ↓
4. P0-5 (위험 표현 후처리)  ── 사용자 가시 안전 시연
5. UX-1 (원클릭 리셋)       ── 데모 워크플로우 정리
                              ↓
6. P0-4 (중복 감지)         ── DB migration — DB 리셋과 같이
7. UX-2 (audit trail)       ── DB migration — DB 리셋과 같이
```

**근거**:
- P0-1을 가장 먼저 — 이후 모든 작업의 회귀 테스트가 mock 위에서 즉시 가능
- DB migration (P0-4, UX-2)은 마지막 — 한 번에 reset 하고 끝내야 개발 환경 흐름이 깨끗
- P0-5와 UX-1은 *사용자가 가시적으로 느끼는 변화* — 데모 영상에 직접 노출

**총 예상**: 18~26시간 (2~3일 풀타임 또는 4~5일 파트타임)

---

## 검증 시나리오 (P0 + UX 완료 후)

각 시연을 1번씩 통과해야 작업 완료:

1. **오프라인 데모** — 네트워크 차단 + `unset UPSTAGE_API_KEY` → 사이드바 🟡 MOCK 뱃지 + 5건 처리 + 카드 표시 정상
2. **부분 실패** — mock에서 review 3번째에 의도적 500 → 4건 카드 정상 + 1건 "분류 실패" 카드 + 사장 직접 입력 UI
3. **비한국어** — "Great coffee!" 영어 리뷰 → classifier 호출 0, lang_skip trace 1줄
4. **중복** — 같은 본문 리뷰 2건 seed → DB 1건, UI 1건
5. **위험 단어** — mock drafter에 "환불" 강제 박기 → 답글에 "별도 안내", 카드에 safety_notes 노출
6. **리셋** — 발표용 매장 수동 편집 + 리뷰 30건 처리 → "데모 리셋" 1클릭 → 5초 내 깨끗 + 시드 매장 복귀
7. **감사 추적** — 답글 1건을 3회 수정 → `feedback_events` 에 row 3개, 사이드바 이력 expander에 3건 표시

---

## 부록 §A — 의도적으로 P2로 미룬 항목

team57이 가지고 있지만 *지금* 도입 가치보다 비용이 큰 항목들:

| 항목 | team57 위치 | 왜 P2 (또는 영구 보류) |
|---|---|---|
| Provider Protocol 추상화 | `llm/provider.py:23-40` | review-ops-agent는 Solar 단일 베팅이 *의도된* 차별점. 다시 추상화하면 베팅의 의미 희석. mock fallback만으로 충분 |
| LangGraph fallback (`HAS_LANGGRAPH`) | `graph.py:17-23, 85-103` | review-ops-agent의 평가 기준이 LangGraph 정통성 시연 — fallback이 있으면 "실제로 LangGraph 위에서 동작하나?" 의심 여지 생김 |
| `_split_reviews` 다중 입력 파싱 | `input_parser.py:54-68` | review-ops-agent는 mock JSON에서 자동 fetch — 사용자 paste 입력 UI 자체가 없음. 향후 외부 플랫폼 연동 시 같이 들어가야 의미 |
| `_extract_keywords` 키워드 카운터 | `db_tools.py:113-126` | review-ops-agent는 이미 `query_review_stats` LLM tool calling 으로 더 정통한 방식 — 회귀 |
| 한 그래프 다건 처리 | `state.py` `parsed_reviews: list` | 1리뷰=1invocation 베팅이 streaming UI의 본질 — 회귀 |

---

## 부록 §B — 변경되는 파일 한눈에

P0+UX 완료 시 touch 되는 파일:

```
src/llm/upstage.py           — env 분기 추가 (P0-1)
src/llm/upstage_mock.py      — 신설 (P0-1)
src/llm/__init__.py          — router (P0-1)
src/graph/nodes/classifier.py — try/except + retry (P0-2)
src/graph/routes/sentiment.py — failed 분기 (P0-2)
src/graph/state.py            — classification_failed, lang_skip, safety_notes 필드 (P0-2,3,5)
src/graph/nodes/pii_mask.py   — 한국어 필터 (P0-3)
src/graph/tools/safety_filter.py — 신설 (P0-5)
src/graph/nodes/drafters.py   — safety_filter 호출 (P0-5)
src/store/sqlite.py           — hash dedupe + feedback_events insert (P0-4, UX-2)
src/scripts/seed.py           — seed_all() 함수화 (UX-1)
src/ui/app.py                 — MOCK 뱃지, 원클릭 리셋, 실패 카드, audit expander (P0-1, UX-1, P0-2, UX-2)
src/ui/components.py          — safety_notes 렌더 (P0-5)
migrations/002_review_text_hash.sql  — 신설 (P0-4)
migrations/003_feedback_events.sql   — 신설 (UX-2)
tests/test_mock_provider.py          — 신설 (P0-1)
tests/test_classifier_failure.py     — 신설 (P0-2)
tests/test_safety_filter.py          — 신설 (P0-5)
README.md                     — Mock 모드 안내 한 단락 (P0-1)
```

총 15개 파일 변경/신설. 신규 8개, 수정 7개.
