# review-ops-agent

> 소상공인 리뷰 응대 및 반복 불만 분석 AI Agent — 매장 컨텍스트를 기억해 점점 '우리 가게답게' 답글을 쓰고, 누적된 부정 리뷰에서 반복 불만을 뽑아 점검 체크리스트까지 만드는 멀티 Agent 시스템.

LangGraph 위에 multi-tenant Memory를 영속하고, 감정·신뢰도 기반 conditional Router로 답글 Drafter를 분기하며, SQL query tool로 다세션 반복 불만을 집계합니다.

**SOMA 17기 · 57조** — 박세민, 박세원, 박준하, 유혁진, 윤성민

---

## 상태

🟢 **구현 완료 · 데모 영상 제출 준비 중** — Upstage Solar API + Docker.

- 전체 spec: [`docs/spec/`](./docs/spec/)
- 원본 기획서: [`PROPOSAL.md`](./PROPOSAL.md)
- 데모 자료: [`docs/demo/`](./docs/demo/)

---

## 어떻게 구현하나

### 입력 → 처리 → 출력

```
Mock JSON 리뷰
  → Streamlit "fetch batch" 버튼
  → graph.stream() 1 review = 1 invocation
  → 답글 초안 + 분류 카드
  → [복사] / [수정 후 저장]
  → 매장 톤 학습 (다음 호출에 반영)
```

리뷰 한 건이 들어오면 LangGraph 그래프가 다음 노드를 차례로 통과합니다:

1. **load_context** — Memory Store에서 매장 메타·과거 답글 톤 샘플·피드백 hint를 읽어 state에 주입
2. **pii_mask** — 전화·이메일·계좌를 정규식으로 마스킹 (LLM에 raw PII 노출 방지)
3. **classifier** — Solar Pro 2로 감정·카테고리(멀티라벨)·신뢰도·risk_flag를 한 번에 JSON 출력
4. **route_by_sentiment** — 감정과 신뢰도로 4갈래 conditional 분기
5. **drafter** (긍/부/부저신뢰도/중 4종 중 1개 실행) — 매장 톤 + 톤 샘플 few-shot + diff hint를 prompt에 자동 주입
6. **memory_save** — 사장이 답글 수정·복사 시 톤 샘플을 Memory Store에 append

별도 **batch 그래프**가 주1회 (수동 트리거) 다세션 분석을 수행:

1. **pattern_aggregator** — SQL query tool을 호출하여 최근 4주 부정 카테고리 TOP 3를 집계
2. **checklist_generator** — TOP 3와 매장 메뉴·가격대를 보고 점검 To-Do 3~5개 생성

---

## 신경 쓴 점

| 영역 | 설계 |
|---|---|
| **개인화** | 매장 메뉴·과거 답글 톤 샘플·사장 수정 이력을 Memory Store에 namespace 분리하여 영속. 모든 Drafter 호출 시 자동 주입. |
| **점진 학습** | 사장이 답글 수정할 때마다 (1) 수정본을 톤 샘플 풀에 추가, (2) AI 원본 vs 사장 수정본 차이를 Solar로 한 줄 요약하여 다음 호출 prompt에 hint로 주입. |
| **다세션 분석** | 분류 결과를 SQLite에 다대다 정규화로 저장 (`reviews` ⇆ `review_categories`). 4주 윈도우 SQL 집계로 반복 불만을 데이터로 가시화. |
| **multi-tenant** | 매장별 데이터 격리. Memory Store는 `(place_id, kind)` tuple namespace, SQL은 모든 쿼리에 `place_id` 조건. |
| **민감정보 보호** | 전화번호·이메일·계좌 등 PII는 Classifier 이전 단계에서 정규식 마스킹. SQLite에는 마스킹된 본문만 저장. |
| **안전성** | 욕설·법적 위험 표현 감지 시 Classifier가 `risk_flag` 출력 → 부정·저신뢰도 흐름으로 분기되어 *보수적 prompt* 사용 (구체적 약속·정책 변경 표현 회피). |
| **비용** | 전 노드 Solar Pro 2 (Upstage). SOMA 발급 16만원 free credit 으로 학습·평가·데모 모두 충분. 골든셋 결과에 따라 일부 노드 mini 다운그레이드 검토. |
| **재현성** | mock 리뷰·시드 데이터는 frozen JSON. DB는 `make seed` 한 번에 초기화. 발표 직전 깨끗한 상태로 reset 가능. |

---

## Agent 주요 요소

### Node — 9개

| 종류 | 노드 | 역할 |
|---|---|---|
| Memory I/O | `load_context`, `memory_save` | Cross-thread Memory Store read/write |
| 전처리 | `pii_mask` | 정규식 마스킹 (LLM 호출 없음) |
| LLM 분류 | `classifier` | Solar Pro 2, structured JSON 출력 (`response_format=json_schema`) |
| LLM 생성 | `thanks_drafter` / `apology_drafter` / `apology_drafter_lowconf` / `neutral_drafter` | 4종 — 매장 톤·few-shot·hint 주입 |
| Batch | `pattern_aggregator`, `checklist_generator` | SQL tool 호출 + 자유 생성 |
| Chat (별도 graph) | `agent` + `tools` (ReAct) | 매장 비서 — 5개 tool (read+write) 로 사장님 자연어 요청 처리. UI 우측 하단 💬 floating button → dialog. |

### Edge

| 종류 | 위치 |
|---|---|
| 일반 edge | START → load_context → pii_mask → classifier, drafter → memory_save → END |
| **Conditional edge** | `route_by_sentiment` 분기 함수가 감정 × 신뢰도 → 4 Drafter 중 1개 선택 |

분기 함수:

```python
def route_by_sentiment(state: ReviewState) -> str:
    if state["sentiment"] == "positive":  return "thanks_drafter"
    if state["sentiment"] == "neutral":   return "neutral_drafter"
    if state["confidence"] >= 0.7:        return "apology_drafter"
    return "apology_drafter_lowconf"
```

### Tool calling

```python
@tool
def query_review_stats(place_id: str, group_by: Literal["category", "sentiment"], days: int = 28) -> str:
    """Aggregate review categories for a place. Returns JSON of {key: count}."""
```

- `pattern_aggregator` 노드가 `ChatUpstage.bind_tools([query_review_stats])` 로 LLM 에게 도구를 노출 → LLM이 args 를 결정해 호출 → 결과를 받아 자연어로 TOP 3 정리. trace 가 *decide → sql_tool → summarize* 3단계로 분할.
- 안전: `group_by`는 enum whitelist만 허용. raw SQL은 tool 내부에서 parameterized query.

### Memory

LangGraph의 cross-thread `Store` API. `(place_id, kind)` tuple namespace로 매장별 격리.

| Namespace | 내용 | 쓰기 시점 |
|---|---|---|
| `(place_id, "metadata")` | 매장명·업종·메뉴 5~10개·가격대·답글 톤 선호 | 첫 진입 또는 seed 자동 로드 |
| `(place_id, "tone_samples")` | 사장이 채택/수정한 답글 누적 (최근 N건이 Drafter few-shot으로) | 답글 [복사] 또는 [수정 저장] 시 append |
| `(place_id, "feedback")` | AI 원본 vs 사장 수정본 diff를 Solar 가 요약한 hint | 톤 샘플 추가 후 비동기 |

### Streaming

`graph.stream(..., stream_mode='updates')`로 노드 단위 변경분만 받아 Streamlit 사이드바의 그래프 진행 패널에 ✓/⏳/⏸ 아이콘으로 노출. 평가자가 "어느 노드가 지금 동작 중인가"를 시각적으로 추적 가능.

---

## 데모 시나리오

### 시나리오 1 — 마감 후 리뷰 5건 정리 (메인 graph)

> 저녁 9시. 카페 A 사장은 사이드바에서 "예시 카페 A"를 선택하고 **새 리뷰 5건 가져오기** 버튼을 누른다.

- 그래프가 1건씩 처리하며 사이드바에 노드 진행이 ✓로 차례로 켜진다 (`load_context → pii_mask → classifier → route_by_sentiment → apology_drafter → memory_save`).
- 5건 처리 후 메인에 카드가 5개 쌓임 — 각 카드에 (a) 분류 결과, (b) 답글 초안, (c) [복사]/[수정] 버튼.
- 부정 리뷰 카드 1개의 답글을 사장이 살짝 다듬어 [수정 저장]. → 톤 샘플 append + 비동기 diff hint 생성.
- 마지막 부정 리뷰에서는 직전 수정한 톤이 prompt에 반영되어 답글 톤이 자연스럽게 갱신됨.

**핵심 포인트**: 노드 단위 streaming, conditional Router 분기, Memory Store write.

### 시나리오 2 — 주말 누적 분석 (batch graph)

> 일요일 밤. 사장은 **TOP 3 + 체크리스트 새로고침** 버튼을 누른다.

- batch graph가 시작 → `pattern_aggregator`가 SQL query tool을 호출 → 최근 4주 부정 카테고리 빈도를 집계 → "대기시간 12회 / 위생 5회 / 가격 3회" 결과를 자연어로 정리.
- `checklist_generator`가 TOP 3와 매장 메뉴·가격대를 보고 점검 To-Do 3~5개 생성: "피크타임 인력 1명 추가 검토", "빨대 제공 동선 점검" 등.
- UI 메인 영역의 TOP 3 카드 + 체크리스트 카드가 갱신.

**핵심 포인트**: Tool calling, multi-step batch graph, SQL 집계와 LLM 자유 생성의 결합.

### 시나리오 4 — 채팅 비서 (별도 chat agent)

> 사장은 우측 하단 💬 매장 비서 버튼을 클릭. dialog 모달에서 자연어로 요청.

- "오늘 새 리뷰 5건 분석해줘" → `analyze_new_reviews(5)` tool 호출 → main graph 5번 실행 → 결과 요약 token streaming
- "이번 주 반복 불만" → `get_top_complaints()` → batch graph
- "내 메뉴랑 톤 샘플 알려줘" → `get_store_info()` → 즉시 답
- "이 답글 톤 샘플로 추가해줘 — [리뷰] / [내 답글]" → `add_owner_reply(...)` → Memory Store write

**핵심 포인트**: `langgraph.prebuilt.create_react_agent` ReAct loop, 5개 tool (read+write), token streaming, 매장별 closure 격리.

### 시나리오 3 — 매장 톤 학습 (개인화 효과 비교)

> 사장이 사이드바에서 매장을 "예시 식당 B (신규)"로 전환한 뒤, 카페 A와 동일한 부정 리뷰("주말 대기가 너무 길어요")를 처리한다.

- 식당 B에는 톤 샘플이 0건 → Drafter prompt에 few-shot 블록이 비어있고 매장 메타도 빈약 → 답글이 generic·교과서적.
- 매장을 카페 A로 다시 전환하면 동일 리뷰에 대한 답글이 톤 샘플 3건 + diff hint를 반영하여 *카페 A의 평소 톤*에 가깝게 생성됨.
- 두 결과를 나란히 보여 "Memory Store가 매장별로 격리되어 다른 답글이 나온다"는 multi-tenant + 개인화 효과를 동시 시연.

**핵심 포인트**: Memory Store namespace 격리, tone_samples few-shot 효과, diff hint 누적.

---

## 기술 스택

| 영역 | 선택 |
|---|---|
| 언어 / 런타임 | Python 3.11 |
| Agent 프레임워크 | LangGraph + LangChain (core) + `langchain-upstage` |
| LLM 호출 | Upstage Solar API (`openai` SDK + `base_url=https://api.upstage.ai/v1`) |
| 모델 | Solar Pro 2 전 노드 (한국어 강점, Ko-MT-Bench 81.0) |
| 인증 | `UPSTAGE_API_KEY` (Upstage 콘솔 16만원 free credit) |
| 구조화 출력 | `response_format={"type": "json_schema", ...}` (OpenAI 호환 schema validation) |
| UI | Streamlit (단일 프로세스) |
| 저장소 | SQLite (관계 데이터) + LangGraph Memory Store (매장별 KV, JSON dump 영속) |
| 컨테이너화 | Dockerfile + docker-compose (`make docker-up`) |
| 패키징 | uv + Makefile |
| 테스트 | pytest + 자체 골든셋 50건 (5명 cross-label, Fleiss kappa) |

---

## Quick Start

### 옵션 A — 로컬 실행

```bash
# 1. 환경 변수 설정 (Upstage 콘솔에서 API 키 발급, https://console.upstage.ai)
cp .env.example .env
# .env 에서 UPSTAGE_API_KEY 입력

# 2. 의존성
uv sync

# 3. 시드 데이터 + DB 초기화 (매장 2개 + mock 리뷰 ~42건)
make seed

# 4. 1 review end-to-end 검증 (graph stream + batch graph)
make smoke

# 5. Streamlit 실행
make run                # localhost:8501

# 부속: Graph 다이어그램 (Mermaid)
make graph-diagram
```

#### Mock 모드 (오프라인 데모/CI)

`UPSTAGE_API_KEY` 가 비어있거나 `REVIEW_OPS_LLM=mock` 이면 모든 Solar 호출이 결정론적 더미 응답으로 자동 대체됩니다 — 네트워크 없이 그래프 회귀 테스트 가능.

```bash
REVIEW_OPS_LLM=mock make smoke   # 또는 unset UPSTAGE_API_KEY && make run
```

⚠️ Mock 모드의 채팅 비서는 stub 한 줄만 응답합니다 (실제 ReAct 루프는 실 키 필요).

### 옵션 B — Docker

```bash
# 1. .env 준비 (옵션 A 와 동일)
cp .env.example .env
# UPSTAGE_API_KEY 입력

# 2. 컨테이너 빌드 + 시작
make docker-build
make docker-up           # → http://localhost:8501

# 3. 시드 (컨테이너 안에서)
make docker-seed

# 4. (옵션) smoke test
make docker-smoke

# 5. 종료
make docker-down
```

`docker-compose.yml` 은 `./data` 와 `./migrations` 를 볼륨 마운트해 SQLite + Memory Store dump 가 호스트와 동기화됩니다.

---

## 핵심 KPI

| 지표 | 목표값 |
|---|---|
| 분류 정확도 (골든셋 50건) | ≥ 85% |
| 답글 사용 의향 | ≥ 70% |
| 처리 시간 단축 | 직접 처리 대비 1/3 이하 |
| 다세션 반복 불만 TOP 3 정합성 | 3개 중 2개 이상 일치 |
| 사용성 (무가이드 5분 이내 완료) | ≥ 80% |
| 개인화 체감 (입력 전/후 비교) | ≥ 60% |

---

## Spec 색인

- [00 — Overview](./docs/spec/00-overview.md)
- [01 — LangGraph Architecture](./docs/spec/01-langgraph-architecture.md)
- [02 — Data Model](./docs/spec/02-data-model.md)
- [03 — Input & Runtime](./docs/spec/03-input-and-runtime.md)
- [04 — UX & Streaming](./docs/spec/04-ux-and-streaming.md)
- [05 — Personalization & Feedback Loop](./docs/spec/05-personalization.md)
- [06 — Models & Evaluation](./docs/spec/06-models-and-evaluation.md)
- [07 — Team & Demo](./docs/spec/07-team-and-demo.md)
- [08 — Risks & Deferrals](./docs/spec/08-risks-and-deferrals.md)
- [CHANGES — Diff from PROPOSAL.md v2](./docs/spec/CHANGES-FROM-PROPOSAL.md)

---

## 학습 회고

- [LangGraph 학습 회고](./docs/LANGGRAPH-LEARNING.md) — 핵심 개념 6가지 + 구현하며 마주친 고민 10가지. 같은 팀·다음 LangGraph 프로젝트 시작할 사람 대상.

---

## 데모 자료

발표 영상 녹화·편집을 위한 일체.

- [시나리오 3종 (액션 사양)](./docs/demo/scenarios.md) — 시나리오별 step-by-step 액션 + 기대 출력 + 노출 surface
- [영상 대본 (5막 · 6:30)](./docs/demo/script.md) — 시간/화면/narration/자막 매핑
- [한글 자막 SRT](./docs/demo/subtitles.srt) — DaVinci Resolve · VLC import 가능
- [녹화 가이드](./docs/demo/recording-guide.md) — OBS 셋업 + 사전 준비 + 편집 + fallback

---

## 라이선스

미정 (SOMA 17기 교육 목적 프로젝트).
