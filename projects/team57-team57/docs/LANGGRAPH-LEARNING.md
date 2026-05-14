# LangGraph 학습 회고

> `review-ops-agent` 를 만들면서 익힌 LangGraph 핵심 개념과 실제 구현 시 마주친 고민·결정 사항을 정리한 문서. 코드만 보면 알기 어려운 *왜 이렇게 했는가* 를 남기는 게 목적.
>
> 대상 독자: 같은 팀, 다음에 LangGraph 로 무언가 만들 사람.

---

## 목차

**Part 1 — LangGraph 핵심 개념 6가지**
1. [StateGraph + TypedDict State](#1-stategraph--typeddict-state)
2. [Conditional Edges (Router)](#2-conditional-edges-router)
3. [Memory Store (Cross-thread Persistence)](#3-memory-store-cross-thread-persistence)
4. [Streaming](#4-streaming)
5. [Tool Calling](#5-tool-calling)
6. [`create_react_agent` (Prebuilt)](#6-create_react_agent-prebuilt)

**Part 2 — 구현하며 마주친 고민 16가지**

7. [멀티라벨 분류와 라우팅의 충돌](#7-멀티라벨-분류와-라우팅의-충돌)
8. [Tool calling: manual orchestration vs LLM-driven](#8-tool-calling-manual-orchestration-vs-llm-driven)
9. [Memory namespace 설계](#9-memory-namespace-설계)
10. [Conditional edge 의 trace 한계와 우회](#10-conditional-edge-의-trace-한계와-우회)
11. [LLM backend 두 번의 마이그레이션](#11-llm-backend-두-번의-마이그레이션)
12. [Streaming UX in Streamlit](#12-streaming-ux-in-streamlit)
13. [점진 personalization: 사장 답글 학습](#13-점진-personalization-사장-답글-학습)
14. [3개의 graph 분리](#14-3개의-graph-분리)
15. [Nested expander 제약과 컴포넌트 설계](#15-nested-expander-제약과-컴포넌트-설계)
16. [Multi-tenant 격리 기본값](#16-multi-tenant-격리-기본값)
17. [Mock LLM provider 와 env 라우팅 패턴](#17-mock-llm-provider-와-env-라우팅-패턴)
18. [Defense in depth — prompt + 후처리 safety filter](#18-defense-in-depth--prompt--후처리-safety-filter)
19. [Per-review failure isolation in batch streams](#19-per-review-failure-isolation-in-batch-streams)
20. [Audit trail: orthogonal to primary store](#20-audit-trail-orthogonal-to-primary-store)
21. [Multi-layer dedup — structured + LLM judgment + heuristic](#21-multi-layer-dedup--structured--llm-judgment--heuristic)
22. [UI surface 압축 — expander 6→3, tabs 통합](#22-ui-surface-압축--expander-63-tabs-통합)

---

# Part 1 — LangGraph 핵심 개념 6가지

## 1. StateGraph + TypedDict State

### 개념

LangGraph 의 가장 기본 단위는 *상태를 공유하는 노드 그래프*. 노드 사이를 흐르는 데이터는 `TypedDict` 로 정의된 *State* 다. 각 노드는 함수 `(state: dict) -> dict` 시그니처를 가지며, 반환된 dict 가 기존 state 에 *merge* 된다.

- 누적해야 하는 필드 (예: 로그 항목 list) 는 `Annotated[list, add]` 로 *reducer* 명시. LangGraph 가 자동으로 append.
- 일반 필드는 기본 *덮어쓰기* 동작.

### 우리 프로젝트 적용 — `src/graph/state.py`

```python
class ReviewState(TypedDict, total=False):
    # 입력
    place_id: str
    review_id: str
    raw_text: str

    # 노드별 산출
    place_metadata: dict
    tone_samples: list[dict]
    masked_text: str
    sentiment: Literal["positive", "negative", "neutral"]
    categories: list[dict]
    reply_draft: str
    drafter_used: str

    # 누적 — 모든 노드가 append, 최종에 모든 trace 가 합쳐짐
    node_log: Annotated[list[NodeLogEntry], add]
```

`node_log` 가 핵심 패턴. 7개 노드가 각자 `{"node_log": [entry]}` 를 반환하면 LangGraph 가 자동으로 누적 → graph 종료 시 6~7개 entry 의 통합 trace 가 됨.

### 학습 포인트

`total=False` 를 쓰면 *모든 필드 optional*. 노드는 자기 출력만 반환하면 됨 (다른 필드 None 으로 채울 필요 없음). 부분 dict 반환이 자연스러워짐.

---

## 2. Conditional Edges (Router)

### 개념

노드 다음 분기를 *동적으로* 결정하는 메커니즘. `add_conditional_edges(source, condition_fn, path_map)` 로 등록.

- `condition_fn(state) -> str` 이 다음 노드 이름을 반환
- `path_map` 은 `{key: node_name}` dict — `condition_fn` 결과를 실제 노드로 매핑
- 결과적으로 LLM 의 분류 결과에 따라 *다른 노드* 가 실행됨 (if-else 의 그래프 버전)

### 우리 프로젝트 적용 — `src/graph/routes/sentiment.py`

```python
CONFIDENCE_THRESHOLD = 0.7

def route_by_sentiment(state: dict) -> str:
    sentiment = state.get("sentiment")
    if sentiment == "positive":
        return "thanks_drafter"
    if sentiment == "neutral":
        return "neutral_drafter"
    if state.get("confidence", 0) >= CONFIDENCE_THRESHOLD:
        return "apology_drafter"
    return "apology_drafter_lowconf"
```

`classifier` 노드 직후 호출되어 4개 drafter 노드 중 1개로 분기. 부정 리뷰가 신뢰도 0.7 미만이면 *보수적인 prompt 의 drafter* 로 따로 분기 — 라우터로 안전성을 보강하는 패턴.

### 학습 포인트

- 라우터는 *결정론적* 으로 짜는 게 좋음. LLM 호출 안 하고 state 만 보고 결정.
- 분기 후 노드들이 모두 같은 다음 노드 (`memory_save`) 로 모이도록 정상화 — fan-out / fan-in.

---

## 3. Memory Store (Cross-thread Persistence)

### 개념

LangGraph 에는 두 가지 영속 메커니즘이 있다:
- **Checkpointer**: 한 *thread* (대화 세션) 안의 state 를 저장. 같은 대화 이어가기·time-travel 용.
- **Store**: thread 와 *독립적* 인 key-value 저장소. 매장별·사용자별 장기 메모리 같은 cross-thread 데이터.

Store 는 `(namespace_tuple, key, value)` 구조다. namespace 가 tuple 인 게 핵심 — *계층적 분리* 가 자연스럽다.

### 우리 프로젝트 적용 — `src/store/memory.py`

```python
# 매장별 격리 + 데이터 종류별 분리
store.put((place_id, "metadata"), key="profile", value={...})
store.put((place_id, "tone_samples"), key=sample_id, value={...})
store.put((place_id, "feedback"), key=feedback_id, value={...})

# 읽기
profile = store.search((place_id, "metadata"))[0].value
samples = store.search((place_id, "tone_samples"), limit=3)
```

namespace tuple 의 첫 요소 = `place_id` 라 *매장 격리는 자동*. 두 번째 요소 = `kind` 로 데이터 종류별 따로 관리 (partial update 가능).

### 학습 포인트

- Checkpointer 가 *thread 안* 의 state 라면 Store 는 *thread 밖* 의 영구 메모리.
- multi-tenant 시스템이면 namespace 의 *첫 차원* 을 tenant_id 로 두는 게 자연스러움.
- LangGraph 의 `InMemoryStore` 는 프로세스 메모리 — 영속 필요하면 `AsyncSqliteStore` 또는 직접 dump (우리는 JSON 파일에 dump).

---

## 4. Streaming

### 개념

LangGraph 의 `graph.stream(...)` 은 여러 mode 지원:
- `stream_mode="updates"` — 노드 1개 완료될 때마다 *state delta* yield. UI 진행률에 적합.
- `stream_mode="messages"` — LLM 호출 안의 *token chunk* yield. 채팅 응답 streaming 에 적합.
- `stream_mode="values"` — 매번 *전체 state* yield. 디버깅 용.

### 우리 프로젝트 적용

**진행 패널** (`src/ui/app.py` 의 fetch button 흐름):
```python
for chunk in graph.stream(input, stream_mode="updates"):
    for node_name, delta in chunk.items():
        # 진행률 바 + 노드 단계 로그 갱신
        panel.add_step_line(f"✓ {node_name}")
        panel.advance(...)
```

**채팅 응답** (시도했다가 invoke 로 회귀 — Trade-off 부분 참고):
```python
for chunk in agent.stream({"messages": ...}, stream_mode="messages"):
    msg, _meta = chunk
    if isinstance(msg, AIMessageChunk):
        placeholder.markdown(buffer + msg.content + "▌")
```

### 학습 포인트

- `updates` mode 가 가장 안정적. 매 노드 완료 시점이 명확.
- `messages` mode 는 `ChatModel(streaming=True)` 가 set 되어 있어야 진짜 token 단위로 분할.
- Streamlit 같은 re-run 모델 UI 와 결합하면 streaming 도중 사용자 interaction 이 들어오면 stream 이 끊김.

---

## 5. Tool Calling

### 개념

LLM 이 사전 정의된 *함수 (tool)* 를 호출해 외부 데이터·동작을 수행하는 패턴. OpenAI 의 function calling 표준과 호환.

흐름:
1. LLM 에 tool schema 를 `bind_tools([...])` 로 노출
2. 사용자 요청 → LLM 응답에 `tool_calls` 가 포함됨 (자연어 응답 대신)
3. 코드가 tool 함수 실행 → 결과를 `ToolMessage` 로 LLM 에 다시 전달
4. LLM 이 결과를 보고 *자연어로 최종 응답*

LangChain 의 `@tool` 데코레이터로 함수를 tool 로 등록.

### 우리 프로젝트 적용

**Pattern 노드** — SQL query tool (`src/graph/nodes/pattern.py`):

```python
@tool
def query_review_stats(place_id, group_by="category", days=28) -> str:
    """매장의 최근 N일 리뷰 통계를 집계합니다."""
    # parameterized SQL 호출, JSON 반환
    ...

llm = ChatUpstage(model="solar-pro2").bind_tools([query_review_stats])

# 1) LLM 이 tool_call 결정
response = llm.invoke(msgs)
if response.tool_calls:
    for tc in response.tool_calls:
        # 2) tool 실행
        result = query_review_stats.invoke(tc["args"])
        msgs.append(ToolMessage(content=result, tool_call_id=tc["id"]))
    # 3) LLM 이 결과 받아 자연어 정리
    final = llm.invoke(msgs)
```

### 학습 포인트

- Tool function 의 docstring 이 LLM 에게 그대로 노출됨 → docstring 을 prompt 작성하듯 신중하게.
- args 타입 힌트로 LLM 이 보내는 args 가 자동 검증됨 (Pydantic 변환).
- Tool 안에서 LLM 호출하면 *재귀* 가 됨. 우리 ReAct 패턴 (Part 6).

---

## 6. `create_react_agent` (Prebuilt)

### 개념

위의 Tool calling 루프 (LLM → tool_calls → tool → LLM → ...) 를 매번 직접 짜기 번거로워 LangGraph 가 *prebuilt agent* 제공. `langgraph.prebuilt.create_react_agent` 한 줄로 ReAct loop 완성된 그래프 반환.

```python
from langgraph.prebuilt import create_react_agent

agent = create_react_agent(
    llm,
    tools=[tool1, tool2, ...],
    prompt="당신은 ...",
)
# 자동으로 두 개 노드 + conditional edge:
#   agent (LLM) ─tool_calls?─→ tools (실행) ─→ agent
#       ↓ no tool_calls
#      END
```

내부 구조:
- `agent` 노드: LLM 호출
- `tools` 노드: 모든 tool 실행 (병렬)
- conditional edge: 응답에 `tool_calls` 있으면 → tools, 없으면 → END

### 우리 프로젝트 적용 — `src/graph/chat/agent.py`

매장별 chat agent. 5개 tool (read+write) 와 system prompt 결합:

```python
def build_chat_agent(place_id: str):
    llm = ChatUpstage(model="solar-pro2", streaming=True)
    tools = make_chat_tools(place_id)  # closure 로 place_id 주입
    return create_react_agent(llm, tools=tools, prompt=_SYSTEM)
```

사용자가 *"오늘 새 리뷰 5건 분석해줘"* 입력 → agent 가 `analyze_new_reviews(n=5)` tool 호출 결정 → tool 이 main graph 5번 invoke → 결과 받아 자연어 정리.

### 학습 포인트

- prebuilt 라서 *직접 그래프 빌더 안 짜도* 되지만, 내부는 일반 StateGraph 와 동일. `agent.get_graph().nodes` 로 확인 가능.
- max_iterations 같은 제한 옵션 있음 (무한 루프 방지).
- 자체 그래프 안에 *agent 노드 하나로 끼워넣는* 합성도 가능 (subgraph).

---

# Part 2 — 구현하며 마주친 고민 10가지

## 7. 멀티라벨 분류와 라우팅의 충돌

### 상황

PROPOSAL v2 가 "5대 카테고리 멀티라벨 분류" 를 명시. 한 리뷰가 `[맛, 서비스]` 처럼 두 카테고리에 동시 속할 수 있음.

### 고민

Router 가 카테고리 기반이면 멀티라벨 리뷰는 어디로 보내야 하나?
- (a) Primary 카테고리 1개로 압축 — 정보 손실
- (b) Send API 로 fan-out → 카테고리별 drafter 각각 실행 → 응답 합치기 — 복잡, prompt 5+ × 감정 3 = 15+ 변형 필요
- (c) 라우터는 다른 축 (감정) 으로, 카테고리는 *메타데이터* 로

### 결정

(c). Router 는 *감정 단축* (긍/중/부 + 부정 신뢰도) 4분기. 카테고리는 Classifier 가 출력하고 SQLite 에 저장하지만 *라우팅에는 안 씀*. 대신 Drafter prompt 에 *parameter 로 주입* (예: ApologyDrafter 가 "서비스 카테고리 부정 리뷰" 라는 컨텍스트 인지).

### 학습

라우팅 축이 *멀티라벨* 이면 그래프가 폭발한다. 단축으로 고정하고 멀티라벨 정보는 *prompt parameter / 메타데이터* 로 흘려보내는 게 실용적.

---

## 8. Tool calling: manual orchestration vs LLM-driven

### 상황

Pattern 노드 (TOP 3 부정 카테고리 집계) 가 SQL 을 호출해야 함. 두 가지 방식이 가능:
- (A) **Manual orchestration**: 코드가 직접 SQL 호출 → 결과를 LLM 에 넣어 정리만 요청
- (B) **LLM-driven**: LLM 에게 SQL tool 노출 → LLM 이 args 를 결정해 호출 → 결과 받아 정리

### 고민

- (A) 는 *결정론적·디버깅 쉬움*. LLM 이 args 를 틀릴 위험 0.
- (B) 는 *정통 ReAct 패턴*. trace 에 LLM 의 도구 호출 결정이 그대로 남아 LangGraph 학습 가치 ↑.
- 초기 (claude CLI subprocess 시절) 에는 (B) 가 어려웠음 — CLI 가 tool calling 안 받아주거나 MCP server 셋업 필요.

### 결정

- v1: (A) manual. SQL 직접 호출 → claude CLI 로 LLM 정리.
- v2 (Solar 마이그레이션 후): (B) LLM-driven 복원. `ChatUpstage.bind_tools([query_review_stats])`.
- Trace 가 3단계로 분할: `pattern.llm_decide` (tool_call 결정) → `pattern.sql_tool` (실행) → `pattern.llm_summarize` (정리).

### 학습

LangGraph Tool use surface 의 *진정한 학습 가치* 는 LLM 이 args 를 결정하는 부분. 데모 시 *trace 에서 tool_calls 가 보이도록* 분할해 노출하는 것이 좋다. v1 의 manual 도 동작은 같지만 학습 surface 노출이 약하다.

---

## 9. Memory namespace 설계

### 상황

Memory Store 의 namespace 를 어떻게 잡을지.
- (a) `(place_id,)` 1차원
- (b) `(place_id, kind)` 2차원
- (c) `(owner_id, place_id, kind)` 3차원

### 고민

- (a): KV 사전 수준. value 가 dict 면 partial update 시 *전체 dict re-put* 필요.
- (b): 종류별 (metadata / tone_samples / feedback) 분리. 톤 샘플은 list-of-records 형태로 *append-only* 자연스러움.
- (c): 사장 1명이 여러 매장 소유 시나리오. 현재 demo 에는 over-engineering.

### 결정

(b). `(place_id, "metadata"|"tone_samples"|"feedback")` 2차원. 각 kind 안에 여러 record 가 들어가도 `store.search` 가 namespace prefix matching 으로 가져옴. partial update 가능.

### 학습

namespace tuple 의 *각 차원* 은 *데이터 격리 축* 으로 사용해야 함:
- 첫 차원: tenant_id (자동 격리)
- 둘째 차원: data kind (논리 분리)
- LangGraph 공식 docs 에서도 이 패턴 권장.

---

## 10. Conditional edge 의 trace 한계와 우회

### 상황

`route_by_sentiment` 같은 conditional edge 함수는 *순수 함수* 라 state 를 변경 못함. 즉 trace (`node_log`) 에 *라우팅 결정* 을 직접 추가 못한다.

### 고민

학습 가치 측면에서 *왜 어느 분기로 갔는지* 가 trace 에 안 보이면 아쉽다. 사용자 입장에서 graph 동작이 *블랙박스* 가 됨.

### 결정

`classifier` 노드 끝에서 *라우터 결정을 예측해* trace 에 미리 emit. 라우팅 함수가 결정론적이라 같은 입력 → 같은 결과 보장 → 사전 계산 안전.

```python
# classifier_node 안에서
result = classify(state["masked_text"])
predicted_route = route_by_sentiment({**state, **result})
router_log = {
    "node": "route_by_sentiment",
    "kind": "router",
    "summary": f"→ {predicted_route} (sentiment={...}, conf={...})",
    "details": {...},
}
return {**result, "node_log": [classifier_log, router_log]}
```

### 학습

LangGraph 의 trace 메커니즘은 *노드 수준* 이라 *edge 수준 메타데이터* 는 직접 표현 안 된다. 결정론적 라우팅이면 *생성 노드에서 미리 추가* 하는 게 워크어라운드. 만약 LLM 기반 라우팅이면 그 LLM 호출 자체가 노드여야 함.

---

## 11. LLM backend 두 번의 마이그레이션

### 상황

LLM 호출을 어떤 SDK 로 할지 두 번 바뀜:
1. **v1**: `claude` CLI subprocess (Claude Max 구독 사용 — 별도 API 키 불필요)
2. **v2**: Upstage Solar API (`openai` SDK + `langchain-upstage`)

### 고민

- v1 의 동기: API key 결제 회피, 학습 비용 0.
- v1 의 문제:
  - cold start ~12s/call (subprocess 매번 spawn)
  - `--json-schema` 우회 필요 (custom CLI 플래그)
  - tool calling 은 MCP server 셋업 없으면 어려움
  - 5 review 처리 ~2분 → 데모에서 답답
- v2 의 계기: SOMA 가 Upstage credit 16만원 제공
- v2 의 장점:
  - OpenAI 호환 → langchain `bind_tools`, `with_structured_output` 표준 사용
  - 1-2s/call → 5 review 25-30초 (6배 빠름)
  - 한국어 강점 (Solar Pro 2, Ko-MT-Bench 81.0)

### 결정

v2 로 전환. drop-in replacement 가 가능하도록 `src/llm/upstage.py` 가 v1 `src/llm/cli.py` 와 동일 시그니처 (`complete_text_with_meta`, `complete_json_with_meta`). 노드 코드는 import 줄만 교체.

### 학습

- LLM 호출은 *interface 추상화* 해두면 backend 교체가 import 줄 한 줄로 끝남.
- Cold start 가 큰 backend (CLI subprocess) 는 *데모 흐름이 끊김* — UX 측면에서 결정적 단점.
- 한국어 작업이면 한국어 강점 모델 (Solar) 이 prompt tuning 시간 절감.

---

## 12. Streaming UX in Streamlit

### 상황

채팅봇 UI 에 token 단위 streaming 적용하려 했음. `agent.stream(stream_mode="messages")` 사용.

### 고민

- LangGraph + ChatUpstage(streaming=True) + stream_mode="messages" 조합이 *때때로 빈 응답*.
- 원인: agent 가 tool_calls 먼저 emit (content 비어있음) → tool 실행 → AIMessageChunk 두 번째 호출. 첫 chunk 에서 content="" 만 보고 종료하면 응답 누락.
- 또 streamlit re-run 모델이 stream 중 다른 user 액션과 충돌.

### 결정

Streaming 대신 `agent.invoke()` + *simulated typing* (5ms/char placeholder 갱신). 안정성 우선.

```python
result = agent.invoke({"messages": history})
full = extract_final_text(result["messages"])  # 마지막 *content 있는* AIMessage
displayed = ""
for char in full:
    displayed += char
    placeholder.markdown(displayed + "▌")
    time.sleep(0.005)
```

응답 시간 자체는 동일하지만 사용자에게는 *글자가 흘러나오는* 효과로 보임.

### 학습

진짜 token streaming 이 *프로토콜·UI framework·SDK 호환* 셋이 모두 맞아야 동작. 셋 중 하나가 부적합하면 *시각 효과만 시뮬* 하는 게 ROI 가 더 좋을 수 있다. 데모 우선 프로젝트에선 신뢰도 > 진정성.

---

## 13. 점진 personalization: 사장 답글 학습

### 상황

PROPOSAL F8: "사장 피드백 반영 — 사장이 답글을 수정하면 학습 풀에 반영".

### 고민

사장이 수정한 답글에서 *어떻게 학습* 할지:
- (a) 수정본을 *그대로 풀에 추가* (few-shot 으로 자동 사용)
- (b) AI 원본 vs 사장 수정본 *차이* 를 별도 hint 로 추출
- (c) 둘 다

### 결정

(c) 둘 다. tone_samples 에 수정본 append (few-shot 풀 확장) + Solar 가 AI 원본·사장 수정본 비교해 "더 짧은 종결어 선호, 이모티콘 사용" 같은 한 줄 hint 생성 → feedback namespace 에 저장. 다음 Drafter prompt 가 *둘 다* 자동 주입.

### 학습

LLM 기반 personalization 은 *데이터 두 개의 layer* 가 효과적:
- *Behavioral*: 실제 사용자 행동 (수정본) — few-shot 으로 모방
- *Meta-level*: 사용자 선호 요약 (hint) — explicit instruction

두 layer 가 같이 prompt 에 들어가면 LLM 이 더 빨리 톤을 잡는다.

---

## 14. 3개의 graph 분리

### 상황

처음엔 main graph 하나로 모든 걸 하려 했음. 하지만 *서로 다른 입력·출력·트리거* 가 있어 분리:

- `main_graph` (1 review = 1 invocation) — fetch button
- `batch_graph` (TOP 3 + 체크리스트) — TOP 3 button
- `chat_agent` (ReAct, prebuilt) — 채팅 버튼

### 고민

- 하나의 거대한 graph 로 만들면 *conditional edges 가 폭발*. "fetch 모드 vs batch 모드 vs chat 모드" 분기를 매번 따져야.
- 따로 만들면 *코드 분산* + 공유 utility 중복 가능.

### 결정

3 graph 분리. 각자 *학습 surface* 가 다름:
- main_graph: conditional Router (감정 분기), Memory Store
- batch_graph: Tool use (bind_tools), Streaming
- chat_agent: create_react_agent (prebuilt), 5 tool fan-out

### 학습

LangGraph 의 graph 는 *함수 단위* 다. 트리거 조건과 출력 형태가 다르면 *별개 graph* 가 자연스러움. 공유 utility 는 `src/store/`·`src/llm/` 처럼 *graph 외부* 에 두면 중복 없다.

---

## 15. Nested expander 제약과 컴포넌트 설계

### 상황

Streamlit 의 `st.expander` 는 *중첩 금지*. `expander 안에 expander` 면 silently 실패.

### 고민

처리된 리뷰 목록 (바닥 섹션) 은 row 마다 `st.expander` 로 wrap. 안에 분류 카드·답글 카드·graph trace expander 가 들어가야 함. trace 가 expander 면 nested → 실패.

### 결정

- 인라인 카드 (방금 처리된 리뷰): `with_trace_expander=True` — outer expander 없음, trace 가 `st.expander`
- 바닥 목록 (이미 outer expander): `with_trace_expander=False` — trace 가 `st.toggle`
- `render_node_trace` 안의 노드별 디테일도 *expander → toggle* 로 교체

```python
def render_review_result(..., with_trace_expander=True):
    if with_trace_expander:
        with st.expander("🔍 graph trace"):
            render_node_trace(...)
    else:
        if st.toggle("🔍 graph trace"):
            render_node_trace(...)
```

### 학습

UI framework 의 *제약* (Streamlit 의 nested expander 금지, dialog 안 chat_input 제한 등) 을 미리 알면 *상위 컴포넌트가 자기 안의 컨텍스트를 모름* 이 흔한 함정. 호출 측이 context 를 명시적으로 넘기는 게 안전 (`with_trace_expander=False` 같은 flag).

---

## 16. Multi-tenant 격리 기본값

### 상황

코드 어디서든 *현재 매장* 의 데이터만 보여야 함. 매장 A 의 톤 샘플이 매장 B 답글에 끼면 안 됨.

### 고민

격리 메커니즘을 어디에 둘지:
- (a) 호출 측이 매번 place_id 필터링
- (b) 데이터 layer 에서 자동 분리 (namespace, WHERE)
- (c) 둘 다

### 결정

(c) 다층 방어:
- **Memory Store**: namespace 첫 차원이 `place_id` → 다른 매장 데이터 *조회 자체가 불가능*
- **SQLite**: 모든 read/write 함수가 `place_id` 인자 강제, WHERE 절에 항상 포함
- **Chat agent tools**: factory 패턴으로 closure 에 `place_id` 주입 — tool 호출 시점에 매장 명시 안 받아도 됨

```python
def make_chat_tools(place_id: str) -> list:
    @tool
    def get_store_info() -> str:  # place_id 인자 없음
        meta = memory.get_metadata(place_id)  # closure
        return ...
    return [get_store_info, ...]
```

### 학습

multi-tenant 시스템에서 격리는 *기본값* 으로 잡혀야 함:
- 데이터 layer 에서 *bypass 불가능* 하게
- 호출 측이 격리를 *의식 안 해도* 작동
- closure / dependency injection 으로 매번 인자 안 넘겨도 됨

빠르게 데모 만들다 보면 격리를 *option* 으로 두기 쉬운데, 한 번 새면 *모든 데이터 신뢰성* 이 무너진다.

---

## 17. Mock LLM provider 와 env 라우팅 패턴

### 상황

데모/평가 당일 인터넷 또는 API 키 문제 = 단일 실패점. CI 도 매번 Solar 를 호출하면 비용·시간 두 축 모두 부담. 키 없이도 "동일한 흐름" 이 돌아가야 마음 편하게 demo recording / pytest 를 굴릴 수 있다.

### 고민

두 갈래.
- (a) **Provider 추상화**: `LLMProvider` 같은 Protocol 인터페이스 정의 + `UpstageProvider` / `MockProvider` 두 구현. 호출부는 `provider.complete_json(...)`.
- (b) **env 라우팅**: 기존 함수 시그니처 (`complete_text_with_meta`, `complete_json_with_meta`) 그대로 두고, 본문 상단에서 환경변수 보고 mock 모듈로 *조용히* 위임.

(a) 는 깔끔하지만 호출 측 코드를 *모두* 손봐야 함. 노드 7개 × import + 시그니처 = 변경 surface 가 크고, 디퍼런셜 PR 도 노이즈가 많다. (b) 는 호출부 변경 0 이지만 "숨겨진 분기" 가 생긴다.

### 결정

(b). `complete_*_with_meta` 함수 본문 상단에 `_is_mock_mode()` 게이트 하나 추가. 그 안에서 `upstage_mock` 모듈로 위임. `langchain-upstage` 의 `ChatUpstage` 처럼 *객체* 인터페이스는 `get_chat_llm()` factory + `_MockChatLLM` 클래스로 동일 처리 — `.bind_tools(...)` / `.invoke(...)` / `.stream(...)` 만 mimic 하면 `create_react_agent` 도 그게 mock 인지 인지 못 한다.

```python
def _is_mock_mode() -> bool:
    return (
        os.getenv("REVIEW_OPS_LLM", "").lower() == "mock"
        or not os.getenv("UPSTAGE_API_KEY")
    )

def complete_json_with_meta(prompt, *, system, schema, model=None):
    if _is_mock_mode():
        return upstage_mock.complete_json_with_meta(prompt, system=system, schema=schema, model=model)
    # 실제 Solar 호출
    ...
```

키가 없으면 *자동으로* mock — opt-out 이 아니라 *실패 시 안전한 default* 다.

### 학습

- Provider 추상화 (Protocol) 는 *멀티 backend 지원 의도가 있을 때* 가치. 단일 backend 베팅 + safety net 만 필요하면 env 라우팅이 코드 변경 최소.
- Mock 의 *deterministic* 보장 (random 사용 금지, 입력 해시 기반 분기) 이 CI 안정성 핵심. Same input → same output 이어야 snapshot test 가 의미 있음.
- ChatUpstage 같은 객체 인터페이스도 호환 가능: `_MockChatLLM` 이 `.bind_tools(...)` / `.invoke(...)` 만 mimic → langgraph prebuilt agent 도 차이를 못 알아챔. *덕 타이핑* 이 mock 의 친구.
- env 라우팅의 단점은 *trace 에서 mock 사용 여부가 안 보임*. 우리는 `model` 필드에 `"mock-solar-pro2"` prefix 를 박아 사후에 구분 가능하게 함.

---

## 18. Defense in depth — prompt + 후처리 safety filter

### 상황

drafter prompt 에 "환불·할인·교환 약속 금지" instruction 을 박았지만, Solar 가 가끔 일탈한다. "죄송합니다, 다음 방문 시 할인해드릴게요" 같은 문장이 한 번 새면 그게 *DB 에 final_text 로 박힘* → 영업 약속이 되어버린다. LLM 응답을 100% 신뢰할 수 없다.

### 고민

세 갈래.
- (a) **prompt 강화만** — 자연스러운 답글 유지, 결정성 0%, 어느 정도 일탈 잔존
- (b) **후처리 substitution 만** — 결정성 100%, 자연스러움 손상 위험 ("환불해드릴게요" → "별도 안내해드릴게요" 가 어색)
- (c) **둘 다** — 비용 약간 ↑ (몇십 자 추가 후처리 코드), 신뢰성 ↑↑

prompt 만 믿으면 *증거* 가 없고, 후처리만 두면 *prompt 자체가 약해져* 1차 출력 품질이 떨어진다.

### 결정

(c). `src/graph/tools/safety_filter.py` 의 `RISKY_PHRASES` 사전 (`{"환불": "별도 안내", "할인": "별도 안내", "교환": "별도 안내", ...}`) 으로 drafter 출력을 후처리. 치환 발생 시 `safety_notes` state 필드에 `[{phrase, replaced_with}]` 로 기록 → UI 의 답글 카드에 *"⚠️ 안전 필터 적용: '할인' → '별도 안내'"* 작은 배지로 노출. 사용자가 *눈으로* 안전망이 동작했음을 확인 가능.

### 학습

- LLM 앱에서 *결정론적 안전 baseline* 은 신뢰성·평가 양면에 의미 있음. 사용자/감사자가 "정말 막혀있나" 를 *눈으로 확인* 가능해야 안심. 보이지 않는 가드는 가드가 아니다.
- 치환은 사전 (dict) > 정규식 — 어휘 추가가 코드 변경 1줄. 빈도 모니터링도 쉬워 어떤 LLM 일탈이 잦은지 metric 화 가능 ("최근 100건 중 환불 치환 7건" 같은 집계).
- Trace 에 *치환 이력* 까지 남겨야 함. 사용자가 모르게 답글이 바뀌면 신뢰가 깨진다. *"내가 봤던 답글" 과 "DB 에 박힌 답글" 이 같다* 가 운영 규칙.
- prompt + 후처리는 *방어층이 직교* — prompt 가 일탈을 *줄이고*, 후처리가 *남은 일탈을 막는다*. 한 층이 무너져도 다른 층이 잡는다.

---

## 19. Per-review failure isolation in batch streams

### 상황

`graph.stream()` 으로 리뷰 5건을 순차 처리 중인데 3번째에 Solar 5xx 가 떨어진다. 현재 구조면 stream 자체가 raise → 1·2 번째는 이미 memory_save 됐지만 4·5 번째는 처리 시도조차 못 한다. 사장 입장에선 진행 패널이 빨갛게 굳고 "5건 다 실패한 것 같은" 느낌이 든다.

### 고민

- (a) **노드 단위 try/except** — graph 안에서 막아 외부엔 항상 성공으로 보임. 단, *어떤 실패인지* 가 잡음.
- (b) **호출 측 try/except per review** — graph 는 단순 유지, 실패는 *그래프 밖에서* 잡음. 그러나 그래프 trace 에 실패 정보가 안 남음.
- (c) **graph 안에 *실패 분기* 신설** — classifier 실패가 *카드로* 노출되고, downstream 노드도 graph 안에서 일관 처리.

### 결정

(c). classifier 노드에 `try / except` + *1회 retry* → 그래도 실패하면 `classification_failed=True` 와 safe defaults (sentiment=neutral, confidence=0, categories=[], rationale="LLM 분류 실패") 반환. `route_by_sentiment` 가 이 플래그를 *먼저* 검사해 `noop_drafter` 로 분기. noop_drafter 는 `reply_draft=""`, `drafter_used="noop"` 만 채우고 그대로 통과. memory_save 가 sentiment=NULL 로 기록하고 reply 는 placeholder 로 저장. UI 가 *빨강 경고 카드* 로 렌더 + 사장이 직접 답글을 쓸 `st.text_area` 노출.

### 학습

- 실패도 *그래프의 1차 시민*. 별도 분기로 만들면 (1) trace 가 명확 (classifier_failed 노드가 보임) (2) UI 가 분기 결과를 자연스럽게 분기 렌더 (3) 사용자가 "처리됐는데 답글 못 만든 케이스" 와 "처리 안 된 케이스" 를 구분 가능.
- "noop drafter" 같은 *empty 노드* 가 graph topology 를 *완결* 시킴 — END 로 직접 가지 않고 memory_save 까지 거쳐야 trace 가 일관된다. 빈 노드의 가치는 *형태 유지* 에 있다.
- `lang_skip` (비한국어 필터) 도 같은 분기를 *재사용* — 한 번 만든 noop 경로의 *교차 활용*. 분기 하나가 두 가지 실패 모드를 흡수.
- retry 정책은 *노드 단위* 가 한 번이 적정. 무한 retry 는 stream 을 멈추게 한다. "한 번 더 해보고 안 되면 boss 에게 넘긴다" 가 사용자 친화적.

---

## 20. Audit trail: orthogonal to primary store

### 상황

사장이 답글을 *수정* 또는 *복사* 하면 두 가지 일이 일어나야 함. (1) `replies.final_text` 최종 상태 갱신 (2) `tone_samples` 에 append (학습 풀 확장). 그런데 *언제 어떤 수정이 일어났는지* 의 history 가 사라진다. 같은 답글을 3번 수정해도 final 상태 하나만 남음. 사장이 "내가 한 시간 전에 뭘 바꿨더라" 를 확인할 길이 없다.

### 고민

- (a) **`replies.final_text` 에 JSON 배열로 history 저장** — 한 row 가 비대해지고 SQL 집계가 어려움. "최근 7일 edit 빈도" 를 보려면 매번 JSON 파싱.
- (b) **별도 audit table 신설** — 정규화·집계 깔끔, write 1개 추가 (성능 영향 미미).

### 결정

(b). `feedback_events(event_id, place_id, review_id, reply_id, event_type, before_text, after_text, diff_hint, created_at)` 테이블 신설 (`migrations/003_feedback_events.sql`). `mark_reply_edited` 가 UPDATE 직전 `SELECT final_text` 로 before 를 fetch → `INSERT INTO feedback_events` 호출 후 UPDATE. event_type 은 CHECK constraint 로 `copy / edit / manual_add / diff_hint_generated` 4종 enum 강제. 외래키는 `ON DELETE SET NULL` — 원본 review/reply 가 지워져도 *역사는 보존*.

### 학습

- 운영성·평가성 데이터는 *primary state 와 분리* 한 audit table 이 자연스럽다. primary 가 *현재 무엇* 을 보여주고, audit 가 *언제 어떻게 변했나* 를 보여줌. 두 책임이 한 테이블에 섞이면 곧 후회한다.
- `event_type` 을 enum 으로 못 박으면 SQL 집계 (예: "최근 7일 edit 빈도", "diff_hint 생성률") 가 쉬움. JSON 컬럼이면 매번 파싱 필요 + 오타에 무방비.
- `ON DELETE SET NULL` 외래키는 *감사 친화적* 이다. 원본 review/reply 삭제 후에도 *역사* 가 남아 GDPR-like 요구가 와도 익명 통계는 유지된다.
- audit table 은 *append-only* 로 운영. UPDATE/DELETE 를 안 쓰면 race condition 도 거의 없고 백업 정책도 단순해진다.

---

## 21. Multi-layer dedup — structured + LLM judgment + heuristic

### 상황

사장이 같은 매장에 시간을 두고 두 번 수정한다. "미안해요 → 죄송합니다" 1회 + 1주일 뒤 다른 답글에서 "미안 → 죄송" 으로 같은 변경. 결과적으로 톤 hint 가 *모순* 또는 *중복* 으로 누적 → drafter prompt 가 혼란스러워진다. *같은 의미 다른 표현* 인 hint 들이 동시에 들어가면 LLM 이 어느 쪽을 따라야 하나.

### 고민

단순 텍스트 일치 dedup 으로는 부족. *"미안해요 선호"* 와 *"사과 표현을 정중하게 다듬음"* 은 같은 의미·다른 표현 — 문자열 비교로는 안 잡힌다. 그렇다고 모든 hint 를 매번 LLM 으로 비교하면 비용 폭발.

### 결정

3 layer 로 쌓음.

1. **Structured diff_hint 출력**. 사장 수정 직후 Solar 가 hint 를 *자유 문장* 이 아니라 `{dimension, before, after, hint}` JSON schema 로 추출. dimension ∈ {사과표현, 감사표현, 어투/톤, 길이, 이모티콘, 구체성, 기타}. 추출 단계에서 *meta tag* 가 박히면 이후 비교가 쉽다.

2. **dedup LLM judgment**. 새 hint 를 append 직전, 기존 hint 5건 (같은 dimension 우선) 과 함께 Solar 에 보내 `{action: skip|merge|append, target_fid, merged_text, reason}` 를 받는다. prompt 안에 *같은 dimension 다른 선호 = MERGE 규칙* 을 명시 — 모델이 dimension 을 *비교 좌표축* 으로 쓰도록 유도.

3. **Heuristic fallback** (mock + 안전망). 정규식 `(.+?)\s*선호` 로 X 값을 추출해 *같은 dimension X 다르면 merge* 결정. LLM 실패 또는 mock 모드에서도 동일 동작.

### 학습

- LLM 결정을 신뢰하려면 *입력을 먼저 구조화* 해야 한다. "톤 차이 한 줄 요약" 같은 자유 출력은 다음 단계 LLM 비교에서 정확한 판단 불가. 추출 단계에서 schema 강제하면 비교가 *분류 문제* 로 줄어든다.
- Dimension 같은 *meta tag* 는 LLM 판단의 *예각화* 도구. "이 둘이 같은 차원이냐" 가 검색 공간을 1/N 로 줄여 prompt 도 짧아지고 결정도 일관된다.
- LLM 판단 + 결정론적 fallback 이 *defense in depth* 의 dedup 버전. mock 모드에서도 동일 시연 가능해 *데모 안정성* 까지 보너스로 챙긴다.
- 3 layer 의 비용 비대칭: 1번 (추출) 은 사장 수정 때 1회, 2번 (judgment) 은 hint 수가 임계치 이상일 때만, 3번 (heuristic) 은 항상. 자주 도는 layer 가 가벼워야 한다.

---

## 22. UI surface 압축 — expander 6→3, tabs 통합

### 상황

사이드바에 `st.expander` 가 시간이 지나면서 6개로 늘어났다. (메뉴 / 톤 샘플 / 톤 hint read-only / 직접 추가 form / 톤 힌트 관리 CRUD / 활동 이력). 사용자 피드백: *"톤 hint 와 톤 힌트 관리가 중복으로 보임. 다 펴면 화면이 끝없이 길어짐."*

### 고민

- 직관적으로는 다른 데이터들 (snapshot vs CRUD vs history) 이 *별도 expander* 가 자연스럽지만, 가로 폭이 좁은 사이드바에서 expander 6개 = *세로 스크롤 폭증*. 첫 화면에 메뉴조차 안 보일 수 있음.
- 합치면 *논리 그루핑* 이 깨질 위험. CRUD 와 read-only 가 한 expander 면 사용자 혼란.

### 결정

3 expander 로 압축. **메뉴 / 톤 샘플 & 활동 / 톤 힌트 관리**. "톤 샘플 & 활동" expander 안에 `st.tabs([📋 목록, ➕ 샘플 추가, 📜 이력])` 3탭. 추가 탭은 *radio toggle* 로 단일/일괄 모드 분리 (한 탭 안에서 토글). 톤 hint read-only view 는 CRUD expander 의 첫 줄로 흡수 — 읽기와 쓰기를 같은 컨텍스트에 두니 오히려 자연스럽다.

`src/ui/components.py` 의 `render_sidebar_place_info` 한 함수에 다 들어감.

### 학습

- *논리적으로 다른 데이터* 라도 *사용자 perceived overlap* 이 있으면 통합을 우선. expander 6개 vs 탭 통합 후 3개의 사이드바 가독성 차이는 즉시 체감된다. "한 화면에 메뉴가 보이는가" 가 첫 기준.
- `st.tabs` 는 *순서가 곧 빈도*. 가장 자주 보는 "목록" 을 첫 탭에, 가끔 보는 "이력" 을 마지막에. 사용자가 탭 위치를 *근육 기억* 으로 학습한다.
- 단일/일괄 처럼 *모드 분기* 는 같은 탭 안 radio toggle 이 깔끔. 두 탭으로 나누면 *어느 쪽을 쓸지* 매번 인지 부하 — 모드는 *데이터의 차원* 이 아니라 *동작의 옵션* 이기 때문.
- read-only snapshot + CRUD 를 한 expander 에 두는 게 처음엔 어색해 보이지만, "보면서 고친다" 가 자연스러운 사용 흐름. *데이터 종류* 보다 *작업 흐름* 으로 그루핑하는 편이 사용자 친화적.

---

# 마무리 — 어떤 surface 가 가장 인상 깊었나

| Surface | 학습 가치 | 우리 demo 임팩트 | 비고 |
|---|---|---|---|
| StateGraph + State | 5/10 | 5/10 | 기본기. 이해 없이는 아무것도 못 함 |
| Conditional Router | 8/10 | 9/10 | "분기 결정이 trace 에 보임" — 데모 임팩트 큼 |
| Memory Store | 9/10 | 8/10 | multi-tenant namespace 의 자연스러움 |
| Streaming (updates) | 7/10 | 9/10 | 진행률 바 매끄러움 → 사장 답답함 ↓ |
| Tool Calling (bind_tools) | 9/10 | 8/10 | LLM 이 args 결정하는 부분이 압권 |
| `create_react_agent` | 7/10 | 9/10 | 5줄로 챗봇 구축 — productivity 보너스 |
| Safety filter + Audit trail | 8/10 | 8/10 | LLM 신뢰성 보완·역사 보존, 두 직교 방어층 |

**가장 인상 깊은 surface**: Conditional Router. 한 줄짜리 분기 함수가 *전체 graph 동작* 을 가른다는 게 LangGraph 의 declarative 본질을 잘 보여줌. 학습 가치 측면에서 *결정 로직과 실행 그래프의 분리* 가 강력.

**가장 어려웠던 부분**: token streaming + Streamlit 조합. UI framework + LLM SDK + LangGraph 셋의 호환을 맞추는 게 의외로 복잡. 결국 simulated typing 으로 회피한 게 *상황을 받아들이는* 좋은 사례.

---

## 참고 — 우리 코드 위치

| 개념 | 코드 위치 |
|---|---|
| State | `src/graph/state.py` |
| Main Graph build | `src/graph/build.py` |
| Batch Graph build | `src/graph/build_batch.py` |
| Conditional Router | `src/graph/routes/sentiment.py` |
| Memory Store wrapper | `src/store/memory.py` |
| Tool 정의 | `src/graph/tools/sql_query.py`, `src/graph/chat/tools.py` |
| Chat ReAct agent | `src/graph/chat/agent.py` |
| Streaming (UI) | `src/ui/app.py` (graph.stream), `src/ui/chat.py` (agent.invoke + simulated) |
| Trace 컴포넌트 | `src/ui/components.py` (`render_node_trace`) |

상세 아키텍처: [`docs/spec/01-langgraph-architecture.md`](./spec/01-langgraph-architecture.md).
