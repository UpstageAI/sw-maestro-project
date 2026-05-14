---
title: 01 — LangGraph Architecture
related:
  - 00-overview.md
  - 02-data-model.md
  - 06-models-and-evaluation.md
  - 08-risks-and-deferrals.md
last_updated: 2026-05-08
---

# LangGraph Architecture

## Graph topology

### Main graph — review processing (1 review = 1 invocation)

```
START
  │
  ▼
load_context        # Memory Store read: (place_id, "metadata"), (place_id, "tone_samples"), (place_id, "feedback")
  │
  ▼
pii_mask            # 정규식: 전화·이메일·계좌 → [MASKED]
  │
  ▼
classifier          # Haiku, JSON: {sentiment, categories[], confidence, risk_flag, risk_reason?}
  │
  ▼
route_by_sentiment  # conditional edges
  │
  ├──(긍정)──────────► thanks_drafter
  │
  ├──(부정 ∧ confidence≥0.7) ► apology_drafter
  │
  ├──(부정 ∧ confidence<0.7) ► apology_drafter_lowconf
  │                            (보수적 prompt — "구체적 약속 회피, 사실 확인 요청")
  │
  └──(중립)──────────► neutral_drafter
                        │
                        ▼
                  memory_save        # Store write: 답글 sample 후보 (사장이 수정 시 tone_samples에 append)
                        │
                        ▼
                       END
```

노드 수 = 7 (load_context, pii_mask, classifier, 3+1 drafter[1 routed at a time], memory_save). 4개 conditional edge.

### Batch graph — pattern + checklist (W2 D2~D3 구현)

```
START
  │
  ▼
pattern_aggregator  # Haiku + SQL query tool — TOP 3 카테고리 집계
  │
  ▼
checklist_generator # Haiku — 매장 메타 + TOP 3 → 점검 항목 3~5개
  │
  ▼
END
```

노드 수 = 2. Tool calling 1회.

### Chat agent — `langgraph.prebuilt.create_react_agent` (3번째 graph)

매장별 chat agent. UI 우측 하단 💬 floating button → dialog 안에서 사장이 자연어로 작업 요청.

```
START → agent (LLM) ⇄ tools (5개) → END
        ↑________________↓
         (ReAct loop, max_iter=N)
```

- LLM: ChatUpstage `solar-pro2`, temperature 0.3
- Tools (5개, place_id closure 주입):
  - `analyze_new_reviews(n)` — main graph 를 N번 invoke (read+write)
  - `get_top_complaints()` — batch graph invoke
  - `query_reviews(sentiment, limit)` — SQLite read
  - `get_store_info()` — Memory Store + SQL 통계
  - `add_owner_reply(review, reply, drafter_kind)` — Memory Store tone_samples append
- Streaming: `stream_mode='messages'` 로 token-level (Streamlit `st.chat_message` + `st.empty().markdown(buf + "▌")`)
- 학습 surface: ReAct agent loop 가 자동 노출 (LLM → tool_call → tool_result → LLM 재귀)
- 코드: `src/graph/chat/{tools.py, agent.py}`, UI: `src/ui/chat.py`

## State schema

```python
from typing import TypedDict, Annotated, Literal
from langgraph.graph.message import add_messages
from operator import add

class ReviewState(TypedDict):
    # 입력 — graph.invoke 시 채워짐
    place_id: str
    review_id: str
    raw_text: str
    review_created_at: str  # ISO timestamp

    # load_context 출력
    place_metadata: dict       # 매장명, 메뉴, 톤 선호 등
    tone_samples: list[dict]   # 사장이 채택/수정한 답글 샘플 (최근 N건)
    feedback_hints: list[str]  # diff hint 누적

    # pii_mask 출력
    masked_text: str

    # classifier 출력
    sentiment: Literal["positive", "negative", "neutral"]
    categories: list[str]      # ["맛", "서비스"] 등 — 메타데이터, Drafter prompt parameter로 사용
    confidence: float
    risk_flag: bool
    risk_reason: str | None

    # drafter 출력
    reply_draft: str
    drafter_used: str          # "thanks" | "apology" | "apology_lowconf" | "neutral"

    # 누적 (Streaming 시 UI에 노출)
    node_log: Annotated[list[dict], add]  # [{node, started_at, ended_at, status}, ...]
```

## 4 LangGraph surfaces — 노드 매핑

### 1. Conditional Edges (Router)

- 위치: `route_by_sentiment` 분기 함수
- 분기 함수 시그니처:
  ```python
  def route_by_sentiment(state: ReviewState) -> str:
      if state["sentiment"] == "positive": return "thanks_drafter"
      if state["sentiment"] == "neutral":  return "neutral_drafter"
      # negative
      return "apology_drafter" if state["confidence"] >= 0.7 else "apology_drafter_lowconf"
  ```
- 학습 포인트: `add_conditional_edges(source, condition_fn, path_map)` — `path_map`이 dict 반환값을 노드명으로 매핑.
- risk_flag 처리: 별도 분기 없이 prompt 내부에서 "risk 있으면 매장 정책 위반 표현 회피" 지시.

### 2. Cross-thread Store (Memory)

- 사용 노드: `load_context` (read), `memory_save` (write).
- Namespace 구조:
  ```python
  store.put((place_id, "metadata"), key="profile", value={...})
  store.put((place_id, "tone_samples"), key=sample_id, value={...})
  store.put((place_id, "feedback"), key=feedback_id, value={...})
  ```
- 읽기 패턴: `store.search((place_id, "tone_samples"), limit=3)` — 최근 3개 sample을 few-shot으로.
- 쓰기 시점: 사장이 답글 수정 시 (UI에서 호출) → `tone_samples` append + `feedback` (diff hint) put.
- 학습 포인트: Store는 Checkpointer와 다른 cross-thread 자원 — graph thread에 종속되지 않고 매장 단위로 영속.

### 3. Streaming

- 형태: **node-level only (`stream_mode='updates'`)** — Drafter token streaming은 W2 여유 시 옵션.
- UI 활용: Streamlit 좌측 사이드바에 노드 체크리스트 (✓ load_context → ✓ pii_mask → ⏳ classifier → ...).
- 호출 패턴:
  ```python
  for chunk in graph.stream(input, config={"configurable": {"place_id": pid}}, stream_mode="updates"):
      node_name = list(chunk.keys())[0]
      st.write(f"✓ {node_name}")
  ```
- 학습 포인트: `updates` mode는 노드 단위 변경분만 emit — full state stream보다 가볍고 UI 친화.

### 4. Tool use

- 사용 노드: `pattern_aggregator` (batch graph).
- Tool 정의:
  ```python
  from langchain_core.tools import tool

  @tool
  def query_review_stats(place_id: str, since: str, group_by: str) -> str:
      """
      Aggregate review categories for a place since a date.
      group_by: 'category' or 'sentiment'
      Returns: JSON string of {key: count} sorted desc.
      """
      # SQLite 쿼리 실행, JSON 반환
  ```
- 안전: SQL injection 방지 위해 `group_by`는 enum whitelist (`["category", "sentiment"]`) 만 허용. raw SQL은 LLM이 작성하지 않음 — Tool 내부에서 parameterized query 사용.
- 학습 포인트: LLM이 Tool 호출 결정 → `bind_tools(tools)` + agent loop. Anthropic SDK의 tool_use block과 LangGraph Tool 노드(`ToolNode`)가 어떻게 연결되는지.

## 의도적으로 사용하지 않는 LangGraph 기능

| 기능 | 미사용 이유 |
|---|---|
| Checkpointer + Thread | 1 review = 1 graph run, stateless. Memory Store만으로 매장별 영속 충분. |
| Send API / parallel | 멀티라벨 폐기로 fan-out 필요 없음. 학습 surface 5번째로 미선택. |
| Subgraph | 7~8 노드는 단일 graph로 충분. 계층화 가치 ≦ 복잡도 비용. |
| `interrupt()` / HITL | 학습-only 렌즈에서 의도적 제외. Streamlit re-run 모델과 LangGraph thread 모델 충돌 회피. |

상세 회피 사유는 [`08-risks-and-deferrals.md`](./08-risks-and-deferrals.md).

## 후순위 (시간 부족 시)

1. **token-level streaming** → node-level만으로 축소 (이미 권장이지만 추가 후순위)
2. **risk_flag low-confidence 분기** → 단일 apology_drafter로 통합
3. **batch graph (Pattern + Checklist)** → main graph 외 별개라 maingraph 안정 후 착수, 늦어지면 통계 카드 hardcoded 표시

## 디렉토리 (참고)

```
src/
  graph/
    state.py          # ReviewState TypedDict
    build.py          # graph 컴파일 (StateGraph + 노드 추가 + edges)
    nodes/
      load_context.py
      pii_mask.py
      classifier.py
      drafters.py     # 4개 (thanks, apology, apology_lowconf, neutral)
      memory_save.py
    routes/
      sentiment.py    # route_by_sentiment 분기 함수
    tools/
      sql_query.py    # query_review_stats tool
  prompts/
    classifier.md
    drafter_thanks.md
    drafter_apology.md
    drafter_apology_lowconf.md
    drafter_neutral.md
    pattern.md
    checklist.md
  store/
    sqlite.py         # SQLite 헬퍼
    memory.py         # Store wrapper
  ui/
    app.py            # Streamlit
```
