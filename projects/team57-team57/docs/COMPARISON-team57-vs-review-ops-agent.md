# team57-team57 vs review-ops-agent — 구현 비교 문서

> 같은 "소상공인 리뷰 응대 AI Agent MVP" 도메인을 푼 두 코드베이스의 특징과 trade-off 비교.
> 참고 대상:
> - `team57-team57/` (이전 버전 / 박세원 외 origin 디렉토리 흔적, mock-first MVP)
> - `review-ops-agent/` (현재 SOMA 17기 57조 제출본, Upstage Solar 기반)

본 문서는 두 구현을 우열로 보지 않는다. **"어떤 제약·목표에 어떤 설계를 선택했는가"** 를 6개 축으로 정렬하여 trade-off를 드러낸다.

---

## 한눈 요약

| 축 | team57-team57 | review-ops-agent |
|---|---|---|
| 상태 모델 | `@dataclass(slots=True) ReviewAgentState` — 전체 필드 한 객체 | `TypedDict ReviewState`, `node_log: Annotated[..., add]` 부분 reducer |
| 그래프 토폴로지 | 단일 선형 그래프 (7노드, 1 입력 = 다건 리뷰) | 3그래프 분리 — main(8노드, 1리뷰=1 invocation) + batch + chat ReAct |
| 라우팅 | 입력 파싱 후 단일 conditional (parsed_reviews 유무) | sentiment×confidence 4갈래 conditional → Drafter 4종 |
| 메모리 | SQLite 단일 백엔드 — stores/sessions/reviews/feedback_events | SQLite(관계형 사실) + LangGraph `InMemoryStore`(매장별 KV) + JSON dump 영속 |
| LLM Provider | Provider Protocol 추상화 (Mock / OpenAI / Anthropic 3택) | Upstage Solar 단일, `response_format=json_schema` 강제 |
| Tool calling | 함수형 "tool-like" — Python 함수 직접 호출 | LangChain `@tool` + `bind_tools` — LLM이 args 결정 |
| LangGraph 의존성 | 선택적 (`HAS_LANGGRAPH` fallback 내장) | 필수, prebuilt ReAct까지 사용 |
| UX | Streamlit 단일 페이지, 일괄 분석 후 결과 카드 | Streamlit + `graph.stream(stream_mode="updates")` 진행 표시 + 💬 chat dialog |

---

## 1. 상태 모델

### team57-team57 — `dataclass(slots=True)` 단일 상태

`src/state.py`:
```python
@dataclass(slots=True)
class ReviewAgentState:
    store_id: int | None = None
    raw_input_text: str = ""
    parsed_reviews: list[dict[str, Any]] = field(default_factory=list)
    classified_reviews: list[dict[str, Any]] = field(default_factory=list)
    drafted_replies: list[dict[str, Any]] = field(default_factory=list)
    pattern_summary: dict[str, Any] = field(default_factory=dict)
    checklist: list[str] = field(default_factory=list)
    execution_log: list[str] = field(default_factory=list)
    backend_logs: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
```

각 노드는 `state` 전체를 받아 변경 후 반환. `_coerce_state()` 헬퍼로 LangGraph가 dict로 넘기는 경우와 dataclass인 경우를 양방향 변환.

### review-ops-agent — `TypedDict` + reducer

`src/graph/state.py`:
```python
class ReviewState(TypedDict, total=False):
    place_id: str
    review_id: str
    raw_text: str
    place_metadata: dict
    tone_samples: list[dict]
    masked_text: str
    sentiment: Literal["positive", "negative", "neutral"]
    confidence: float
    risk_flag: bool
    reply_draft: str
    drafter_used: str
    node_log: Annotated[list[NodeLogEntry], add]   # ← reducer
```

노드는 *delta dict*만 반환하고 LangGraph가 머지. `node_log`만 `add` reducer로 누적.

### Trade-off

| | team57 (dataclass) | review-ops-agent (TypedDict + reducer) |
|---|---|---|
| 가독성 | ⭕ IDE 자동완성·타입체크 강함. 필드 명세가 단일 위치에 모임 | △ `total=False`라 IDE가 누락 필드 경고를 안 줌 |
| 노드 시그니처 | △ 노드가 전체 state를 받음 → 결합도↑, 테스트 시 mock 데이터 풀세트 필요 | ⭕ 노드는 partial dict 반환만 책임 → 단위 테스트 용이 |
| LangGraph idiom | △ `_coerce_state` 어댑터가 항상 필요. LangGraph가 fallback 가능하도록 `HAS_LANGGRAPH` 분기 | ⭕ LangGraph가 권장하는 형태. `Annotated[..., add]`로 노드 trace 자동 누적 |
| 진입 비용 | ⭕ Python dataclass만 알면 충분 | △ TypedDict + Annotated + reducer 개념 학습 필요 |
| 다건 처리 | ⭕ `parsed_reviews: list`로 한 번에 다건. invocation 1회 | △ 1 review = 1 invocation. 다건은 외부에서 for-loop |

**핵심 차이**: team57은 "한 번에 다건 처리"를 state에 박아두었고, review-ops-agent는 "1 리뷰 1 그래프"로 분리해 invocation 단위 trace·streaming UI 갱신을 깔끔히 받는다. UX 우선이면 후자, 배치 처리 단순성이 우선이면 전자.

---

## 2. 그래프 토폴로지

### team57-team57 — 7노드 선형 + 단일 분기

```
START → input_parser ─?─→ context_loader → classifier → reply_drafter
                  └─empty→ END                        ↓
                                                  persistence → pattern → checklist → END
```

`src/graph.py` 의 `_route_after_input_parser` 하나만 conditional. 나머지는 직선. 파싱·분류·답글·DB저장·패턴·체크리스트가 모두 같은 그래프에서 1회 invocation에 순차 처리.

### review-ops-agent — 3개 그래프

#### Main graph (8노드, `src/graph/build.py`)
```
START → load_context → pii_mask → classifier
                                       │ route_by_sentiment
                                       ├─→ thanks_drafter
                                       ├─→ apology_drafter
                                       ├─→ apology_drafter_lowconf
                                       └─→ neutral_drafter
                                                ↓
                                          memory_save → END
```

#### Batch graph (`src/graph/build_batch.py`)
```
START → load_meta → pattern_aggregator(SQL tool) → checklist_generator → END
```

#### Chat graph (`src/graph/chat/agent.py`)
- `langgraph.prebuilt.create_react_agent` — ReAct loop 자동 처리
- 5개 tool (read+write), `place_id` closure 주입

### Trade-off

| | team57 (단일 그래프) | review-ops-agent (3그래프) |
|---|---|---|
| 인지 부하 | ⭕ 흐름 1개. README 그림과 코드가 1:1 | △ 어떤 그래프가 언제 실행되는지 별도 문서 필요 |
| 책임 분리 | △ 패턴 분석을 매 입력마다 수행 — 5건 처리 후 6번째에 다시 집계 호출 | ⭕ 실시간(main) ↔ 누적 분석(batch) ↔ 대화(chat) 분리. batch는 수동 트리거 |
| 비용 | ⭕ 단일 그래프 압축 | △ batch/chat의 추가 LLM 호출. 단 pattern_aggregator는 SQL 결과 보고 마무리만 LLM (`pattern.llm_decide → sql_tool → llm_summarize` 3 step) |
| LangGraph 학습 surface 노출 | △ conditional 1개, tool 함수 호출만 보임 | ⭕ conditional 4분기 + tool calling + prebuilt ReAct + cross-thread Store — LangGraph 핵심 6요소 전 surface 시연 |

**핵심 차이**: review-ops-agent는 "LangGraph의 가능한 모든 surface를 평가자에게 보여준다"는 발표/평가 맥락에 최적화. team57은 "한 사이클에 분석 결과를 모두 보여준다"는 사용자 시선 단순성에 최적화.

---

## 3. 분기 라우팅

### team57 — 입력 유무만 분기

```python
def _route_after_input_parser(state):
    return "context_loader" if normalized.parsed_reviews else "end"
```

분류 결과(감정·신뢰도)에 따른 분기는 없음. `reply_drafter` 한 노드가 sentiment를 받아 내부적으로 다른 prompt를 구성하여 LLM에 위임 (`provider.draft_reply(sentiment=...)`).

### review-ops-agent — 4분기 conditional router

```python
def route_by_sentiment(state):
    if sentiment == "positive": return "thanks_drafter"
    if sentiment == "neutral":  return "neutral_drafter"
    if confidence >= 0.7:       return "apology_drafter"
    return "apology_drafter_lowconf"
```

각 Drafter는 별도 노드·별도 prompt·별도 instruction. `apology_lowconf`는 "단정적 사과 회피, 사실 확인 요청" 같은 *보수적 prompt* 를 사용.

### Trade-off

| | team57 (1분기 + LLM 위임) | review-ops-agent (4분기 + 노드 분리) |
|---|---|---|
| 그래프 시각화 | △ 그래프 한 가닥 + 안에서 prompt 분기는 코드를 봐야 알 수 있음 | ⭕ Mermaid 다이어그램에 4갈래가 보임. trace에 어떤 Drafter가 동작했는지 노드명으로 기록 |
| 신뢰도 기반 안전성 | △ 신뢰도 임계값으로 prompt 톤을 약하게 만드는 로직이 없음 | ⭕ confidence < 0.7 → "단정 사과 회피, 정책·할인 약속 금지" 별도 prompt |
| 새 카테고리 추가 비용 | ⭕ prompt 분기만 추가하면 됨 | △ 노드 등록 + edge 매핑 + 분기 함수 수정 (그러나 안전한 변경) |
| LLM 자율성 | ⭕ LLM이 sentiment를 보고 알아서 톤을 결정 | △ 결정론적 분기. LLM은 글만 씀 |

**핵심 차이**: review-ops-agent는 "LLM에 판단을 맡기지 않는 안전 경로(low-confidence)"를 그래프 수준에서 명시했다. team57은 prompt에 위임하여 단순성을 챙겼다.

---

## 4. 메모리

### team57 — SQLite 단일 (`src/db/schema.py`, `repository.py`)

테이블 4개:
- `stores` — 매장 메타 + `reply_samples_json` (JSON 컬럼)
- `review_sessions` — 입력 배치 단위
- `reviews` — 분류·답글 결과. categories/menu_tags/generated_replies 모두 *JSON 컬럼*
- `feedback_events` — before/after 변경 추적

매장별 격리는 모든 쿼리에 `WHERE store_id = ?` 강제.

### review-ops-agent — 이중 백엔드

**SQLite (관계형 사실, `migrations/001_init.sql`)**
- `places`, `reviews`, `replies` 단순화
- `review_categories(review_id, category, confidence)` — **다대다 정규화** (team57은 JSON 컬럼)
- `idx_reviews_place_sentiment`, `idx_reviews_place_created` 등 매장별 집계용 인덱스

**LangGraph `InMemoryStore` (매장별 KV, `src/store/memory.py`)**
- Namespace = `(place_id, kind)`, kind ∈ `{metadata, tone_samples, feedback}`
- write 시점에 `data/store_dump.json` 으로 manual flush — process 재시작에도 살아남음

### Trade-off

| | team57 (SQLite-only) | review-ops-agent (SQLite + Store) |
|---|---|---|
| 스키마 단순성 | ⭕ 한 곳에 다 있음. SQL 한 번 짜면 끝 | △ "톤 샘플은 어디에, 통계는 어디에"가 두 곳 |
| 집계 쿼리 (반복 불만 TOP 3) | △ `categories_json` 을 Python에서 파싱 후 `Counter`로 집계 (`pattern.py:_extract_keywords`는 하드코딩 키워드 매칭) | ⭕ `review_categories` JOIN + `GROUP BY` 한 줄. 인덱스 활용 |
| Few-shot 동적 주입 | △ `reply_samples`는 stores 테이블에 통째로 박혀있음 (사장이 stored shape에 종속) | ⭕ `tone_samples` Namespace에 자유롭게 append. `(place_id, "tone_samples")` 쿼리 한 번으로 N개 가져옴 |
| LangGraph 학습 surface | △ Store API 안 씀 | ⭕ cross-thread Memory Store 시연 가능 (LangGraph 6대 요소 중 하나) |
| 데이터 일관성 | ⭕ ACID 트랜잭션 한 백엔드 | △ Store dump가 atomic하지 않음. JSON write 중단되면 lost |
| 운영 비용 | ⭕ 백업 1개 | △ `data/review_ops.db` + `data/store_dump.json` 둘 다 관리 |

**핵심 차이**: review-ops-agent는 "관계형으로 집계가 깔끔한 사실(리뷰·답글·분류)" 과 "namespace로 격리해 자유롭게 누적하는 컨텍스트(메타·톤·hint)" 를 두 백엔드로 분리했다. team57은 모든 것을 SQLite JSON 컬럼에 박아 단순성을 챙겼지만 집계 성능과 동적 push의 자유도가 떨어진다.

---

## 5. LLM Provider 및 구조화 출력

### team57 — Provider Protocol 추상화

`src/llm/provider.py`:
```python
class LLMProvider(Protocol):
    def classify_review(self, *, review_text, menu_items) -> ReviewClassification: ...
    def draft_reply(self, *, ...) -> ReplyDraft: ...

def get_provider() -> LLMProvider:
    # priority: env REVIEW_AGENT_LLM_PROVIDER → ANTHROPIC_API_KEY → OPENAI_API_KEY → Mock
```

`Mock`/`OpenAI`/`Anthropic` 3구현. 구조화 출력은 각 provider 내부 책임 (코드에선 dataclass 반환).

### review-ops-agent — Upstage Solar 단일 + JSON Schema 강제

`src/graph/nodes/classifier.py`:
```python
CLASSIFIER_SCHEMA = {
    "type": "object",
    "properties": {
        "sentiment": {"type": "string", "enum": ["positive", "negative", "neutral"]},
        "categories": {"type": "array", "items": {...}, "maxItems": 3},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "risk_flag": {"type": "boolean"},
    },
    ...
}
complete_json_with_meta(prompt=..., schema=CLASSIFIER_SCHEMA, model="solar-pro2")
```

Solar API의 `response_format={"type": "json_schema", ...}` 로 server-side 스키마 강제.

### Trade-off

| | team57 (다중 provider Protocol) | review-ops-agent (Solar 전용 + json_schema) |
|---|---|---|
| 멀티 provider 유연성 | ⭕ API 키 없을 때 Mock 자동 fallback | △ Solar API 키 필수. Mock 없음 |
| 한국어 품질 | △ provider 선택에 따라 다름 | ⭕ Solar Pro 2 (Ko-MT-Bench 81.0) 한국어 강점 |
| 구조화 출력 안정성 | △ LLM 응답 파싱 책임이 provider 구현에 분산 | ⭕ enum/min/max/maxItems 등 schema validation server-side 보장 |
| 비용 | ⭕ Mock으로 무료 테스트 가능 | ⭕ SOMA 16만원 free credit으로 충분 (선언) |
| 데모 안정성 | ⭕ 인터넷 없어도 동작 | △ 외부 API 의존 |
| 교체 비용 | ⭕ Provider 추가 = 클래스 하나 작성 | △ Solar 외 모델로 바꾸려면 schema 호환성 검증 필요 |

**핵심 차이**: team57은 "MVP 시연 안정성"을 위해 Mock fallback을 둔 보수적 설계. review-ops-agent는 "한국어 + JSON Schema 안정성"을 위해 단일 provider에 베팅. 후자는 발표용으로 결과 품질이 깔끔하지만 인터넷·API 키가 단일 실패점.

---

## 6. Tool calling

### team57 — 함수형 tool (Python 직접 호출)

`src/tools/db_tools.py`:
```python
def load_negative_review_patterns_tool(repo, store_id) -> dict:
    reviews = repo.list_reviews_by_store(store_id)
    ...
    return {"category_counts": ..., "keyword_counts": ...}
```

LLM은 args를 결정하지 않음. 노드(`pattern_agent_node`)가 직접 함수를 부른다.
README가 이를 "tool-like function"이라 표현.

### review-ops-agent — LangChain `@tool` + `bind_tools`

`src/graph/tools/sql_query.py`:
```python
@tool
def query_review_stats(
    place_id: str,
    group_by: Literal["category", "sentiment"] = "category",
    days: int = 28,
) -> str:
    """매장의 최근 N일 리뷰 통계를 집계합니다."""
    ...
```

그리고 `pattern_agent_node`:
```python
llm = ChatUpstage(model="solar-pro2").bind_tools([query_review_stats])
decide = llm.invoke(msgs)         # Step 1: LLM이 tool_calls를 결정
raw_result = query_review_stats.invoke(tc["args"])   # Step 2: 실행
final = llm.invoke(msgs + [tool_result])             # Step 3: LLM이 자연어 정리
```

3단계 trace (`pattern.llm_decide → sql_tool → llm_summarize`)로 *LLM의 결정 → tool 실행 → LLM의 요약* 가 백엔드 로그에 분리되어 기록.

### Trade-off

| | team57 (함수 직접 호출) | review-ops-agent (LLM-driven tool calling) |
|---|---|---|
| LangGraph "Tool calling" surface | △ tool calling 진짜 의미(LLM이 args 결정)는 아님 | ⭕ OpenAI 호환 tool 스펙. trace로 LLM 결정 과정 확인 가능 |
| 안전성 | ⭕ args가 코드로 박힘 | ⭕ enum whitelist(`Literal`)로 args 제한, parameterized SQL |
| 결정성 | ⭕ 100% 결정론적 | △ LLM이 args를 잘못 결정할 가능성 (실제로 fallback path 마련됨) |
| 발표/평가 적합성 | △ "tool calling 했어요"라 말하기 어색 | ⭕ "LLM이 SQL을 호출하는 trace를 보세요" 시연 가능 |
| 채팅 agent로 확장 | △ ReAct loop를 직접 구현해야 함 | ⭕ `create_react_agent` 한 줄. 5 tool 즉시 노출 |

**핵심 차이**: team57의 "tool-like function"은 추상화일 뿐 LLM이 tool 호출 결정을 내리지 않는다. review-ops-agent는 진짜 LLM-driven tool calling을 사용해 batch 그래프와 chat agent 모두에서 시연한다. 단순성 vs. agent 정통성의 trade-off.

---

## 7. PII 마스킹과 안전성

| | team57 | review-ops-agent |
|---|---|---|
| 위치 | `input_parser` 노드에서 함께 처리 | 별도 `pii_mask` 노드 (transform kind) |
| 패턴 | 휴대폰·이메일·`\d{6,}` (긴 숫자 일반) | 휴대폰(`01[016789]`)·이메일·계좌(`\d{2,4}-\d{2,6}-\d{2,8}`) |
| 위험 표현 필터 | ✅ `RISKY_PHRASES = ("환불", "할인", "법적 책임", ...)` → 답글에서 "별도 안내"로 치환 (`safety_tools.filter_risky_reply_phrases`) | △ 후처리 치환은 없음. 대신 classifier가 `risk_flag`를 출력하고 *prompt 수준에서* 회피 (apology_lowconf instruction) |
| 비한국어 필터 | ✅ `contains_korean(masked)` 체크 | ❌ 없음 |

**핵심 차이**: team57이 *후처리(string replace)* 방식, review-ops-agent가 *prompt-level guidance* 방식. 후처리는 결정성이 높지만 부자연스러운 답글이 나올 위험, prompt-level은 자연스럽지만 LLM 일탈 가능성이 있다.

---

## 8. UX·Streaming·관찰가능성

### team57

- Streamlit 단일 페이지 (`app.py`)
- "분석 시작" → 일괄 처리 → 결과 카드 표시
- 백엔드 trace: `execution_log: list[str]` + `backend_logs: list[dict]` — 노드별 입력/출력 요약, db_saved 여부 (`logging_utils.append_backend_log`)
- streaming 없음

### review-ops-agent

- Streamlit + `graph.stream(stream_mode="updates")` → 사이드바에 노드 진행 ✓/⏳/⏸ 아이콘
- 별도 chat dialog (💬 floating button) — `langgraph.prebuilt.create_react_agent` token-streaming
- `node_log: Annotated[..., add]` reducer로 노드별 trace 자동 누적 → UI가 `render_node_trace`로 표시 (kind별 prompt/SQL preview까지)

### Trade-off

| | team57 | review-ops-agent |
|---|---|---|
| 구현 비용 | ⭕ 단순. UI도 표/카드만 | △ stream_mode 2종, reducer, render 컴포넌트 |
| 발표 시 시각성 | △ "처리 끝났다" 한 순간 | ⭕ 노드 ✓ 차례로 켜짐 — LangGraph 진행이 눈에 보임 |
| 채팅 UX | ❌ 없음 | ⭕ 자연어로 매장 운영 요청 가능 |
| 사장님 학습 비용 | ⭕ 버튼 클릭 1회 | △ 채팅·인박스·체크리스트 등 surface가 많음 |

---

## 9. 종합 비교 — 어떤 상황에서 어느 쪽이 더 나은가

| 상황 | 추천 |
|---|---|
| API 키 없이 데모 안정성 확보 | **team57** (Mock fallback) |
| LangGraph 학습·평가용 surface 풀시연 | **review-ops-agent** |
| 단일 개발자가 1~2일에 MVP 만들기 | **team57** (단일 그래프, 단일 DB) |
| 4주 이상 운영 + 매장 톤 점진 학습 | **review-ops-agent** (Memory Store + diff hint feedback loop) |
| 한국어 답글 품질이 가장 중요 | **review-ops-agent** (Solar Pro 2) |
| 멀티 provider 전환 가능성 | **team57** (Provider Protocol) |
| 반복 불만 SQL 집계 성능 | **review-ops-agent** (정규화 + 인덱스) |
| 비즈니스 친화적 단순 운영 | **team57** (DB 1개) |
| 자연어 비서 (대화로 운영) | **review-ops-agent** (chat ReAct agent) |
| 결정론적 안전성 | **team57** (RISKY_PHRASES 후처리) |

---

## 10. team57이 review-ops-agent로 진화한 흔적

코드 디테일을 보면 같은 팀의 **MVP → 본 제출본** 의 evolution으로 읽힌다. 다음 변화가 보인다:

1. **다건 단일 invocation → 1리뷰 1 invocation** — streaming UI를 위한 재설계
2. **JSON 컬럼 집계 → 다대다 정규화** — `review_categories` 테이블 신설
3. **dataclass 전체 state → TypedDict + reducer** — node_log 자동 누적
4. **tool-like 함수 → @tool + bind_tools** — LangGraph tool calling surface 시연
5. **prompt 안 sentiment 분기 → conditional edge 4분기 + 별도 Drafter 노드** — 그래프 다이어그램에 분기가 보이도록
6. **SQLite-only → SQLite + Memory Store + 별도 batch/chat 그래프** — LangGraph 6대 요소(Node/Edge/Tool/State/Memory/Persistence) 풀 시연
7. **다중 provider Protocol → Solar 단일 + json_schema** — 한국어 품질과 출력 안정성 베팅

즉 team57은 **"동작하는 MVP"**, review-ops-agent는 **"LangGraph의 모든 핵심 개념을 시연·평가받을 수 있는 정통 LangGraph 구현"** 으로 포지셔닝이 다르다.

---

## 부록 — 의존성 비교

| | team57 | review-ops-agent |
|---|---|---|
| langgraph | `>=0.2.50` | `>=0.2.50` |
| langchain | `>=0.3.0` (full) | `langchain-core>=0.3.0` + `langchain-upstage>=0.7.0` (slim) |
| LLM SDK | `openai>=1.30.0` + `anthropic>=0.34.0` | `openai>=1.50.0` (Upstage base_url) |
| UI | `streamlit>=1.45.0` | `streamlit>=1.40.0` |
| build | hatchling | (uv only, no build backend declared) |
| dev tools | pytest | pytest + ruff |

review-ops-agent는 의존성을 더 슬림하게 유지하면서도(LangChain full 미사용) Upstage 전용 패키지로 한국어 품질을 챙겼다. 정적분석(`ruff`)이 dev 의존성에 들어간 것도 차이.
