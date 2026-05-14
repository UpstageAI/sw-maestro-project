# 데모 시나리오 3종 (액션 사양)

> 발표 영상에 들어가는 시나리오 3종. 각 시나리오는 *interactive* 흐름 (사용자 입력 → 출력 변화) 으로 구성되며, 프론트엔드 화면(Streamlit) 안에서 백엔드 동작(graph trace)이 동시에 노출됩니다.
>
> **사전 조건**: `make reset && make seed && make run` (localhost:8501 자동 오픈). `.env` 의 `UPSTAGE_API_KEY` 가 설정되어 있어야 함 (https://console.upstage.ai 에서 발급).

---

## 시나리오 1 — 마감 후 리뷰 5건 정리 (메인 graph)

**길이**: 약 1:25 (Solar API 기준 — 5 review × ~5s = ~25s 처리, narration 1분 합산)
**노출 surface**: Conditional Router · Memory Store · Streaming · (간접) Tool use 없음

### 액션 시퀀스

| # | 화면 액션 | 기대 출력 | 노출 surface / 학습 포인트 |
|---|---|---|---|
| 1 | 사이드바 라디오 → **`예시 카페 A (PLACE_001)`** 선택 | 메인 타이틀 `📝 예시 카페 A` 갱신 | — |
| 2 | 사이드바 `🍽️ 메뉴 7개` expander 클릭 | 아메리카노·라떼·치즈케이크 등 7개 가격 포함 리스트 | Memory Store `(place_id, "metadata")` |
| 3 | 사이드바 `🎭 톤 샘플 3개` expander 클릭 | 3개 카드: 출처(🌱 시드)·drafter·카테고리·리뷰/답글 미리보기 | Memory Store `(place_id, "tone_samples")` |
| 4 | 사이드바 `🔁 새 리뷰 5건 가져오기` 클릭 | 메인 상단 진행 패널 등장: `⏱ 새 리뷰 5건 처리 — 예상 ~2:05 (초기 추정)` + 진행률 바 + 노드 단계 로그 expander | Streaming 트리거 |
| 5 | (자동) 진행률 바가 매초 차오름 | `0:01 / ~2:05` → `0:15 / ~2:05` ... | 1초 tick (daemon thread) |
| 6 | (자동) 노드 단계 로그에 한 줄씩 누적 | `[REV_001_PLACE_001] ✓ load_context (6ms) — 메타 1 · 톤샘플 3 · 피드백 1`<br/>`✓ pii_mask (0ms)` ... | 노드별 timing |
| 7 | 약 5초 후 첫 카드 등장 (Solar 기준) | `### 📨 REV_001_PLACE_001` + 분류 카드(`😟 부정`, conf 0.95, `대기시간`) + 답글 카드 | Router 분기 결과 |
| 8 | 첫 카드의 `🔍 graph trace (6 steps)` 펼침 (default 펼쳐짐) | 표 6행: load_context / pii_mask / classifier / route_by_sentiment / apology_drafter / memory_save | 백엔드 동작 가시화 |
| 9 | 표에서 `📜 #3 classifier — prompt/응답 미리보기` toggle ON | system prompt 200자 + user prompt + 응답 JSON | LLM 호출 내부 노출 |
| 10 | `🔀 #4 route_by_sentiment — 분기 결정` toggle ON | `다음 노드: apology_drafter`, `임계값: 0.7`, `입력: {sentiment: negative, confidence: 0.95}` | Conditional Router 결정 근거 |
| 11 | 5건 모두 처리 완료 | 진행 패널 `✅ 새 리뷰 5건 처리 — 총 0:25 소요 (평균 0:05/스텝)` + 진행률 100% | ETA moving average 갱신 |
| 12 | 첫 부정 리뷰 카드의 `✏️ 수정` 클릭 | 답글 텍스트 영역 진입 | — |
| 13 | 답글 끝 부분 `다시 한번 방문해주시면 더 나은 모습 보여드리겠습니다.` 살짝 다듬어 → `💾 저장 + 톤 학습` 클릭 | 짧은 진행 패널 (~3초): `톤 학습 (diff hint) — 예상 ~3초` → `Memory Store에 톤 샘플 append` → `Solar 호출 — diff hint 생성 중` → `✅ 완료` | Memory Store write + diff hint LLM 호출 |
| 14 | 사이드바 `🎭 톤 샘플` expander 갱신 확인 | 4건으로 늘어남, 새 샘플 출처 `✏️ 수정` | Memory Store mutation |

### 발표자 narration (~1:25 분량)

- (0:25) "여기는 카페 A의 미처리 리뷰들입니다. 사이드바에서 매장 메뉴 7개와 과거 톤 샘플 3개를 미리 확인할 수 있어요."
- (0:35) "5건 가져오기 클릭. Solar API 라 진행률이 빠르게 차오릅니다. 5초 후 첫 카드 등장."
- (1:05) "graph trace 표에서 classifier 가 약 2초 걸려 negative, 신뢰도 0.95, 카테고리 대기시간 결과를 확인."
- (1:30) "Router 분기 결정도 trace에 남습니다. 신뢰도 0.95가 임계값 0.7보다 크니 apology_drafter 로 분기했죠."
- (1:40) "답글을 다듬어 저장하면 Memory Store 톤 샘플 풀에 추가되고 백그라운드로 Solar 가 차이를 한 줄로 요약, 다음 답글 prompt 에 hint 로 주입됩니다."

---

## 시나리오 2 — 주말 누적 분석 (batch graph + Tool use)

**길이**: 약 0:45 (Solar 기준 — batch graph ~10s + narration 35s)
**노출 surface**: Tool use (SQL query, LLM-driven bind_tools) · Streaming

### 액션 시퀀스

| # | 화면 액션 | 기대 출력 | 노출 surface |
|---|---|---|---|
| 1 | 사이드바 `📊 TOP 3 + 체크리스트 새로고침` 클릭 | 진행 패널: `⏱ TOP 3 + 체크리스트 — 예상 ~10초` | Streaming |
| 2 | (자동) batch graph 실행 | 노드 단계 로그: `✓ load_meta` → `✓ pattern.llm_decide` → `✓ pattern.sql_tool` → `✓ pattern.llm_summarize` → `✓ checklist` | — |
| 3 | 약 10초 후 결과 카드 등장 | 좌: `🔝 TOP 3 반복 불만 (최근 4주)` 1.대기시간 7회 / 2.위생 5회 / 3.가격 3회 · 우: `✅ 이번 주 점검 체크리스트` 5개 | Pattern + Checklist |
| 4 | `🔍 batch graph trace (5 steps)` expander 펼침 | 표 5행: load_meta / pattern.llm_decide / pattern.sql_tool / pattern.llm_summarize / checklist | — |
| 5 | `📜 #2 pattern.llm_decide — prompt/응답` toggle ON | system + user prompt + 응답에 `tool_calls=[{name: query_review_stats, args: {place_id, group_by: category, days: 28}}]` 노출 | **Tool use — LLM이 args 결정** |
| 6 | `🗃️ #3 pattern.sql_tool — SQL 호출` toggle ON | `tool: query_review_stats`, `args: {LLM이 결정한 args}`, `result: [{category: 대기시간, freq: 7}, ...]` | Tool 실행 결과 |
| 7 | `📜 #4 pattern.llm_summarize — prompt/응답` toggle ON | tool 결과를 받아 자연어로 정리한 LLM 두 번째 호출 | LLM 후처리 |
| 8 | `📜 #5 checklist — prompt/응답` toggle ON | TOP 3 + 매장 메뉴/가격대 input + items 5개 JSON 출력 | LLM structured output |

### 발표자 narration (~0:45)

- (1:50) "이제 TOP 3 + 체크리스트를 누르면 별도 batch graph 가 약 10초 만에 끝납니다."
- (2:00) "최근 4주 부정 카테고리 TOP 3 — 대기시간 7회, 위생 5회, 가격 3회. 매장 메뉴까지 반영한 체크리스트 5개."
- (2:15) "trace 를 보면 LLM 이 먼저 query_review_stats tool 호출을 *결정* 했고, args 도 LLM 이 직접 정했어요."
- (2:25) "그 결과를 받아 자연어로 정리한 게 두 번째 LLM 호출. ChatUpstage.bind_tools 로 OpenAI 호환 tool calling 그대로 동작."

---

## 시나리오 3 — 매장 톤 학습 비교 (Memory Store namespace)

**길이**: 약 1:00 (Solar 기준 — form 입력 30s + 1 review 처리 ~10s + 매장 전환)
**노출 surface**: Memory Store namespace · 사장 답글 직접 추가 form

### 액션 시퀀스

| # | 화면 액션 | 기대 출력 | 노출 surface |
|---|---|---|---|
| 1 | 사이드바 라디오 → **`예시 식당 B (PLACE_002)`** 선택 | 메인 타이틀 `📝 예시 식당 B` 갱신 | namespace 격리 (`(PLACE_002, *)`) |
| 2 | 사이드바 `🍽️ 메뉴 0개` 펼침 | `(메뉴 미입력 — Drafter 가 generic 답글 생성)` | metadata 빈약 |
| 3 | 사이드바 `🎭 톤 샘플 0개` 펼침 | `(톤 샘플 없음 — '+ 사장님 답글 직접 추가' 로 시드하거나 답글 [복사]/[수정] 으로 누적)` | empty namespace |
| 4 | 사이드바 `➕ 사장님 답글 직접 추가` expander 펼침 | form: 리뷰 원문 / 사장님 답글 / 카테고리 / 답글 종류 | — |
| 5 | form 입력:<br/>- 리뷰 원문: `"음식 양 진짜 많아서 좋아요"`<br/>- 사장님 답글: `"맛있게 드셨다니 정말 감사해요! 다음에 또 들러주세요 :)"`<br/>- 카테고리: `맛`<br/>- 답글 종류: `thanks` | — | — |
| 6 | `➕ 톤 샘플 추가` 클릭 | 토스트 `톤 샘플 추가됨` + `🎭 톤 샘플 1개` 갱신 (출처 `✍️ 수동 추가`) | Memory Store write (manual source) |
| 7 | 사이드바 `🔁 새 리뷰 5건 가져오기` 클릭 → graph 실행 (~25초) | 5건 처리, 답글에 새 톤 샘플의 친근한 어투(`드셨다니 감사해요`) 일부 반영 | Drafter few-shot 동작 |
| 8 | 사이드바 라디오 → **`예시 카페 A (PLACE_001)`** 로 다시 전환 | `🎭 톤 샘플 4개` (이전 시나리오 1에서 +1된 상태 보존) | namespace 격리 검증 |

### 발표자 narration (~1:00)

- (2:35) "이번엔 매장을 식당 B 로 전환. 신규 매장이라 메뉴 0개, 톤 샘플 0개입니다."
- (2:43) "사장님이 과거 작성하셨던 답글을 form 으로 시드. 리뷰와 답글, 카테고리, drafter 종류 입력하고 추가."
- (3:00) "톤 샘플 1개로 갱신, 출처가 '수동 추가' 로 표시됩니다."
- (3:10) "새 리뷰를 처리하면 Drafter prompt 에 이 톤 샘플이 자동 주입돼서 답글이 사장 톤에 맞게 나옵니다."
- (3:25) "다시 카페 A 로 돌아가도 톤 샘플 4개 그대로. Memory Store 가 매장끼리 자동 격리됩니다."

---

## 회고 (5막)

**길이**: 약 25초
**노출 surface**: 코드 한 줄 — `graph = build_graph()`

### 발표자 narration

- (3:35) "이 프로젝트는 노드 7개, conditional edge 1개, tool 1개로 구성된 LangGraph 그래프입니다."
- (3:43) "Upstage Solar API 와 langchain-upstage 로 한국어 답글이 자연스럽고, 16만원 free credit 으로 비용 부담 없이 학습·발표 모두 처리합니다."
- (3:50) "Router · Memory Store · Streaming · Tool use 네 surface 가 모두 살아 있고, 진행 패널과 graph trace 가 백엔드 동작을 프론트엔드 안에서 그대로 노출합니다."
- (4:00) (끝)

---

## 참고 — 노출 surface 표 (시나리오별 매핑)

| Surface | 시나리오 1 | 시나리오 2 | 시나리오 3 |
|---|---|---|---|
| Conditional Router | ✅ trace 표 + toggle | — | — |
| Memory Store | ✅ load/save trace | — | ✅ namespace 격리 + manual seed |
| Streaming | ✅ 진행 패널 + 노드 로그 | ✅ batch 진행 패널 | ✅ fetch 진행 패널 |
| Tool use | — | ✅ SQL query tool | — |

3개 시나리오로 4 surface 모두 노출.
