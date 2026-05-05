# AI 아키텍처 집중 비판 — "이건 Agentic이 아니다"

> 평가 대상: `AI.md`, `ARCHITECTURE.md` §3~5, `PROPOSAL.md` §2.7 / §3.5~3.7 / §4.4
> 평가 기준: 1주일 데모, 그러나 평가가 "Agentic Workflow" 채점이라는 가정 하의 적합성
> 한 줄 결론: **현재 설계는 "LangGraph로 그린 일직선 파이프라인"이지 Agent가 아니다.** Anthropic 정의로 workflow에 해당하고, ReAct/도구사용/자율판단/회복 같은 agentic 핵심 요소가 0개다.

---

## 0. 가장 먼저: "Agentic"의 표준 정의를 맞추자

가장 권위 있는 두 정의:

- **Anthropic (Building Effective Agents, 2024-12)**:
  > "**Workflows** are systems where LLMs and tools are **orchestrated through predefined code paths**. **Agents**, on the other hand, are systems where LLMs **dynamically direct their own processes and tool usage**, maintaining control over how they accomplish tasks."
  - https://www.anthropic.com/engineering/building-effective-agents

- **OpenAI (A Practical Guide to Building Agents, 2025-04)**:
  > "Agents are systems that **independently accomplish tasks on your behalf**. ... built on Model + Tools + Instructions, with three tool types: data, action, orchestration."
  - https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf

이 두 정의를 기준으로 보면 현재 설계는 **agent가 아닌 workflow**다. 그것도 분기 1개(Risk Gate)밖에 없는 가장 단순한 형태의 workflow다.

---

## 1. 왜 Agentic이 아닌가 — 6가지 핵심 결여

### 1.1 LLM이 "다음에 무엇을 할지"를 결정하지 않는다 (Critical)

`AI.md` §2 다이어그램:
```
IN → Shared State → Policy Agent → Risk Agent → Risk Gate → Execution Agent → OUT
```

이 그래프는 **고정된 토폴로지**다. 어떤 입력이 들어와도 노드 실행 순서가 동일하고, LLM은 각 노드 안에서만 호출되며, **다음에 어느 노드를 호출할지 결정하지 않는다**.

Anthropic 정의의 "dynamically direct their own processes"가 0이다. 이건 **prompt chaining**(Anthropic이 분류한 가장 단순한 workflow 패턴)에 가깝다.
- ref: https://www.anthropic.com/engineering/building-effective-agents (섹션: "Workflow: Prompt chaining")

### 1.2 Tool calling이 없다 (Critical)

문서 어디에도 LLM이 **tool/function을 호출**한다는 설계가 없다. Upbit 시세 조회는 BE의 일반 함수 호출이고, LLM은 "이미 받아둔 데이터를 자연어로 설명"만 한다.

이는 **ReAct 패턴** (Yao et al. 2022)의 핵심을 빠뜨리는 것이다. ReAct는 `Thought → Action → Observation` 루프인데, 여기는 Action이 없다.
- ref ReAct: https://arxiv.org/abs/2210.03629
- ref OpenAI Function Calling: https://developers.openai.com/api/docs/guides/function-calling
- ref Anthropic Tool use: https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview
- ref LangGraph `create_react_agent`: https://langchain-ai.github.io/langgraph/reference/agents/

**즉, "LangGraph"라는 단어를 쓰지만 LangGraph가 가장 잘 하는 것(`ToolNode` + 도구 루프)을 안 쓴다.**

### 1.3 자율성이 사실상 0이다 (Critical)

`PROPOSAL.md` §2.5 "Agent의 자율성 범위" 표를 그대로 옮기면:

| 단계 | Agent 수행 가능? |
|---|---|
| 사용자 입력 해석 | 가능 |
| 정보 검색/조회 | 가능 |
| 데이터 분석 | 가능 |
| 결과 요약 | 가능 |
| 추천/판단 | **제한적** |
| 외부 작업 실행 | **제한적** |
| 최종 결정 | **사전 설정된 정책** |

해석/조회/분석/요약은 **agent가 아니어도 다 한다**. 진짜 자율성이 측정되는 "판단/실행/결정"은 전부 룰 엔진과 사전 정책이 가져갔다.

**문제는 "안전하게 만들었다"가 아니라 "agent라고 부를 근거가 없다"는 것이다.** OpenAI 가이드 정의의 "independently accomplish tasks"가 충족되지 않는다.

### 1.4 메모리 / 학습 / 회복이 없다 (Major)

agentic 시스템의 차별점 중 하나는 **상태 누적 + 자기 교정**이다.

- **LangGraph Checkpointer / Persistence**: thread별로 state를 저장하고 시점 복원
  - https://docs.langchain.com/oss/python/langgraph/persistence
- **Reflexion (Shinn et al. 2023)**: 실패에서 verbal feedback을 누적해 다음 시도 개선
  - https://arxiv.org/abs/2303.11366
- **Self-Refine (Madaan et al. 2023)**: 자기 비판 → 재생성 루프로 평균 ~20% 개선
  - https://arxiv.org/abs/2303.17651

현재 문서는:
- Checkpointer 언급 없음 (Shared State가 메모리 내 dict로만 존재)
- 보류된 판단을 다음 사이클에 어떻게 반영하는지 정의 없음
- LLM이 자기 출력을 검증/수정하는 루프 없음

리스크 게이트 실패 시 그냥 "보류"로 끝난다. **Agent라면 "왜 보류됐는지를 학습해서 다음 정책 제안에 반영"하는 회로가 있어야 한다.**

### 1.5 Multi-Agent라고 부를 근거가 없다 (Major)

`PROPOSAL.md`는 "AI 3명 = 통합 Agent 안의 3 Agent"라고 주장한다. 하지만 multi-agent의 표준 패턴은:

- **Supervisor (manager)**: 한 supervisor가 worker들에게 동적으로 작업 할당
  - https://reference.langchain.com/python/langgraph-supervisor
- **Swarm (decentralized)**: agent들이 서로 handoff
  - https://reference.langchain.com/python/langgraph-swarm
- **Router**: LLM이 입력 분석해서 어느 worker로 보낼지 결정
  - https://docs.langchain.com/oss/python/langchain/multi-agent

현재 설계의 "3 Agent"는 단순 **순차 노드**이며 supervisor도, handoff도, router도 없다. 이건 multi-agent가 아니라 **3-step pipeline**이다.

OpenAI 가이드도 명시한다:
> "Multi-agent systems are appropriate when ... single agent + tools is no longer sufficient."

3개 노드가 다 LLM 호출이 필요하지도 않은 상황에서 multi-agent를 칭하는 건 **인원 정당화용 분할**이다.

### 1.6 Human-in-the-Loop이 설계 시점에 정의되지 않음 (Major)

금융성 서비스에서 가장 중요한 agentic 패턴 중 하나는 **Human approval before tool use**다.

- LangGraph Interrupts: 그래프 일시정지 → 사람 검토 → `Command`로 재개
  - https://docs.langchain.com/oss/python/langgraph/interrupts
  - https://blog.langchain.com/making-it-easier-to-build-human-in-the-loop-agents-with-interrupt/

현재 문서는 "정책 위반 시 무거래"만 있다. "**보류된 판단에 대해 사용자가 1회 승인하면 실행**"같은 진짜 HITL이 없다. 이게 있어야:
- 자율성 (agent가 후보 생성)
- 안전성 (인간이 최종 승인)
- 학습성 (승인/거절 결과로 정책 갱신)

세 가지가 동시에 충족된다. 지금은 자율성을 통째로 죽여서 안전을 얻은 형태.

---

## 2. 이 설계가 실제로 "무엇인지"

Anthropic 분류표에 매핑하면:

| Anthropic 패턴 | 현재 설계와의 일치도 |
|---|---|
| Augmented LLM (LLM + retrieval + tools) | **부분 일치** (retrieval만, tool 없음) |
| Prompt chaining | **거의 일치** ← 현재 위치 |
| Routing | 불일치 (router 없음) |
| Parallelization | 불일치 |
| Orchestrator-workers | 불일치 (supervisor 없음) |
| Evaluator-optimizer | 불일치 (self-critique 없음) |
| **Autonomous agent** | **불일치** |

ref: https://www.anthropic.com/engineering/building-effective-agents

→ **"LangGraph로 구현된 prompt chaining"이 현재의 정직한 명명**이다.

---

## 3. AI.md 문서 자체의 명세 결함

레퍼런스와 별개로, 문서가 SDD로서 가지는 구체적 결함:

### 3.1 LLM 호출 지점의 입출력 계약이 없다
- §7 "LLM 사용 지점"에 "근거 설명 생성"이라고만 적혀 있고
- 어떤 시스템 프롬프트, 어떤 입력 schema, 어떤 출력 schema인지 없음
- **Structured Outputs**를 안 쓰면 자연어 파싱이 망가진다
  - ref: https://developers.openai.com/api/docs/guides/structured-outputs
  - ref Instructor: https://python.useinstructor.com/

### 3.2 Shared State 8필드의 reducer가 없다
- LangGraph `StateGraph`는 필드별 reducer로 머지 동작을 정의
  - ref: https://docs.langchain.com/oss/python/langgraph/graph-api
- "errors"는 append인가 overwrite인가? "action_candidates"는?
- 정의 없으면 노드 간 race / 덮어쓰기 발생

### 3.3 가드레일이 "원칙"이지 "구현"이 아니다
- §8 프롬프트 원칙: "수익 보장 금지", "확정적 예측 금지"
- 이건 검증되지 않으면 깨진다. 가드레일 라이브러리 미명시:
  - NeMo Guardrails: https://github.com/NVIDIA/NeMo-Guardrails
  - Guardrails AI: https://www.guardrailsai.com/
  - OpenAI Moderation: https://developers.openai.com/api/docs/guides/moderation

### 3.4 평가(Evaluation) 기준이 "느낌"이다
- §10 "평가 기준": 정확도/일관성/명확성/안정성/억제 — **어떻게 측정하나?**
- LLM-as-judge / 데이터셋 / 메트릭 미명시:
  - LangSmith Evaluation: https://docs.langchain.com/langsmith/evaluation-concepts
  - LLM-as-judge canonical: https://arxiv.org/abs/2306.05685
  - Ragas: https://docs.ragas.io/

### 3.5 캐시·비용 정책 없음
- Anthropic Prompt Caching: 캐시 적중 시 입력 비용 10%
  - https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
- 데모는 거의 동일한 system prompt를 반복 호출 → 캐시 미사용 시 비용·지연 그대로 누적

### 3.6 도구 표준 무시
- MCP가 사실상 표준화된 tool 인터페이스가 됐는데 언급 없음
  - https://modelcontextprotocol.io/
- Upbit 조회를 MCP tool로 노출하면 외부 평가자가 즉시 이해함

### 3.7 "페이퍼 실행"이 시뮬레이터가 아니다
- 진짜 paper trading은 **포지션북 + 체결 모델 + 잔고**가 필요
  - QuantConnect Backtesting: https://www.quantconnect.com/docs/v2/cloud-platform/backtesting
  - Backtrader Quickstart: https://www.backtrader.com/docu/quickstart/quickstart/
- 현재 문서의 페이퍼 실행은 그냥 "주문 시뮬레이션 결과 JSON 한 줄 만들기"
- → "Agent가 거래를 학습/평가"한다고 말하려면 시뮬레이터 자체가 의미 있어야 함

---

## 4. 개선안 — "정말로 Agentic하게 만드는 3가지 옵션"

평가 기준이 "Agentic Workflow 시연"이라면, 1주일 안에 가능한 옵션을 난이도 순으로:

### 옵션 A (최소): "ReAct + Tools" 단일 에이전트로 다시 그려라

가장 적은 노력으로 agentic을 충족.

- 단일 `create_react_agent`(LangGraph 프리빌트) 사용
- 도구 4개 등록:
  - `get_market_snapshot(symbol)` — Upbit 호출
  - `compute_indicators(symbol, kind)` — RSI/MA 계산
  - `check_policy(action, amount)` — 룰 엔진 호출
  - `submit_paper_order(symbol, action, amount)` — 페이퍼 실행
- LLM이 사용자 요청에 따라 **어떤 도구를 어떤 순서로** 부를지 결정
- Structured Outputs로 최종 결과(`{action, reason, risk}`) 강제
- LangGraph Interrupt로 `submit_paper_order` 직전에 사람 승인

이렇게 하면:
- LLM이 **다음 행동을 결정** ✓ (agentic)
- **Tool calling** ✓
- **Human-in-the-loop** ✓
- **Structured output** ✓
- 작업량은 노드 1개 + 도구 4개 + interrupt 1개 → 1주일에 충분

ref: https://langchain-ai.github.io/langgraph/reference/agents/

### 옵션 B (중간): Supervisor + 2 Workers

- `Supervisor` 1개: 사용자 요청 파싱 → "분석 worker / 실행 worker" 중 누구에게 보낼지 결정
- `Analyst Worker`: 시세조회·지표·리스크 후보 생성 (도구 사용)
- `Executor Worker`: 정책 검증 + 페이퍼 실행 (도구 사용 + interrupt)
- Checkpointer로 thread별 상태 저장 → "어제 평가했던 BTC, 다시 봐줘"가 동작

ref: https://reference.langchain.com/python/langgraph-supervisor

### 옵션 C (도전적): Evaluator-Optimizer 루프 추가

- Worker가 후보 행동 생성 → Evaluator(LLM-as-judge)가 "정책 부합도/리스크 설명 명확성" 채점 → 점수 낮으면 Worker가 재시도 (Self-Refine 패턴)
- ref Self-Refine: https://arxiv.org/abs/2303.17651
- ref Reflexion: https://arxiv.org/abs/2303.11366
- ref LLM-as-judge: https://arxiv.org/abs/2306.05685

발표에서 "왜 이게 단순 if문이 아니라 agent인가?"에 답할 가장 강력한 근거가 됨.

### 옵션 D (★ Recommended): Workflow + ReAct Sub-Agents (하이브리드)

> "큰 틀은 workflow로 안전하게, 각 단계 안은 ReAct로 자율적으로."
> Anthropic의 **Orchestrator-workers 패턴**, OpenAI의 **Manager pattern**과 동일.
> 금융 도메인의 사실상 표준 답안.

**구조:**

```
사용자 입력
    ↓
[Macro = Workflow, 결정론적]
  Policy Subgraph → Risk Subgraph → Deterministic Gate → [HITL Interrupt] → Execution Subgraph → Report Subgraph
       (ReAct)        (ReAct)           (if/else only)                          (ReAct)             (ReAct + Self-critique)
```

- **Macro flow는 코드로 고정** → 컴플라이언스/감사 가능
- **각 노드 내부는 ReAct sub-agent** → LLM이 도구 호출 순서를 자율 결정
- **Gate는 LLM 없이 결정론적** → 리스크 판정의 reproducibility 보장
- **HITL Interrupt**가 실행 직전에 1회 → 자율성과 안전성을 동시에

**LangGraph 골격 (참고용):**

```python
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph, END

policy_agent = create_react_agent(llm, tools=POLICY_TOOLS, prompt=POLICY_SYS)
risk_agent = create_react_agent(llm, tools=RISK_TOOLS, prompt=RISK_SYS)
exec_agent = create_react_agent(llm, tools=EXEC_TOOLS, prompt=EXEC_SYS)
report_agent = create_react_agent(llm, tools=REPORT_TOOLS, prompt=REPORT_SYS)

g = StateGraph(SharedState)
g.add_node("policy", policy_agent)
g.add_node("risk", risk_agent)
g.add_node("gate", deterministic_gate)              # LLM 없음
g.add_node("approval", human_interrupt_node)         # interrupt()
g.add_node("execute", exec_agent)
g.add_node("report", report_agent)

g.add_edge("policy", "risk")
g.add_edge("risk", "gate")
g.add_conditional_edges("gate",
    lambda s: "approval" if s["gate_passed"] else "report")
g.add_edge("approval", "execute")
g.add_edge("execute", "report")
g.add_edge("report", END)
```

**왜 이게 답인가 — Workflow와 Agent의 trade-off:**

| 패턴 | 자율성 | 예측가능성 | 디버깅 | 1주일 적합성 |
|---|---|---|---|---|
| 순수 workflow (현재 설계) | ✗ | ✓ | ✓ | ✓ |
| 순수 single ReAct agent | ✓ | ✗ | ✗ | △ (LLM 헛소리 못 막음) |
| **Workflow + ReAct workers (옵션 D)** | ✓ | ✓ | ✓ | ✓ |

**ref:**
- Anthropic — Orchestrator-workers: https://www.anthropic.com/engineering/building-effective-agents
- OpenAI — Manager pattern (Practical Guide p.16~): https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf
- LangGraph Subgraphs as agents: https://docs.langchain.com/oss/python/langgraph/use-subgraphs
- LangGraph Supervisor: https://reference.langchain.com/python/langgraph-supervisor
- LangGraph create_react_agent: https://langchain-ai.github.io/langgraph/reference/agents/

---

### 4-D.1 Subgraph별 Tool / 자율성 / 결정론 영역 정의

**범례 (자율성 레벨):**
- **L0 (None)** — LLM 호출 없음, 코드만
- **L1 (Constrained)** — LLM이 structured output만 생성, 도구 선택 불가
- **L2 (Tool-augmented)** — LLM이 정해진 도구 풀에서 자유롭게 선택/순서 결정 (ReAct)
- **L3 (Self-improving)** — L2 + 자기 출력 평가/재시도

#### Subgraph 1. Policy Subgraph — 자율성 L2

> "사용자의 모호한 의도를 검증된 정책 객체로 변환"

| Tool 이름 | 입력 | 출력 | 종류 |
|---|---|---|---|
| `search_risk_rules(query, top_k)` | 자연어 query, 상위 N | rule 카탈로그 매칭 결과 | RAG (data) |
| `validate_policy_schema(policy_dict)` | 정책 dict | `{valid, errors[]}` | Action (검증) |
| `check_supported_coins(coins[])` | 코인 심볼 배열 | 지원/미지원 분류 | Data |
| `lookup_user_history(user_id)` | user_id | 과거 정책 변경 이력 | Data |
| `propose_policy_diff(current, draft)` | 현재 정책, 초안 | 변경점 요약 | Action |

**LLM 자율 영역:**
- 어떤 룰을 먼저 검색할지
- 검증 실패 시 어떤 항목을 사용자에게 다시 물어볼지
- 사용자 자연어 ↔ structured policy 매핑

**LLM 금지 영역 (코드 강제):**
- 임계값 숫자 자체의 결정 (사용자가 "보수적"이라고만 말하면 LLM이 추천하되, 최종값은 룰 카탈로그의 권장범위 내로 clamp)
- 지원 코인 enum (코드가 화이트리스트)

**Structured Output (강제):**
```json
{ "policy": UserPolicy, "rationale": str, "cited_rules": ["rule_id..."] }
```

#### Subgraph 2. Risk Subgraph — 자율성 L2

> "현재 시장 상태와 정책을 비교해 후보 행동 도출"

| Tool 이름 | 입력 | 출력 | 종류 |
|---|---|---|---|
| `get_market_snapshot(symbol)` | 코인 심볼 | 현재가/24h변동률/거래량 | Data (Upbit) |
| `get_candles(symbol, interval, count)` | 심볼/주기/개수 | OHLCV 배열 | Data (Upbit) |
| `compute_indicator(symbol, kind, params)` | 심볼, RSI/MA/변동성 등 | 지표값 | Action (계산) |
| `get_position_book(user_id)` | user_id | 보유/평단/PnL | Data |
| `compare_to_policy(snapshot, indicators, policy)` | 위 결과 + 정책 | 위반/접근 항목 리스트 | Action (룰엔진) |
| `search_market_cases(query, top_k)` | 자연어 query | 과거 유사 사례 RAG | RAG |

**LLM 자율 영역:**
- 어떤 지표를 어떤 순서로 계산할지 (RSI 먼저? MA부터? 보유 잔고 먼저?)
- 어떤 과거 사례가 현재 상황에 유사한지 판단
- 후보 행동 (`buy/sell/reduce/hold`) 추천 + 근거 서술

**LLM 금지 영역:**
- 게이트 통과 여부의 최종 판정 (다음 노드의 결정론적 게이트가 함)
- 임계값 비교 자체 (`compare_to_policy` 도구가 함)

**Structured Output:**
```json
{
  "candidates": [{"symbol", "action", "confidence_label", "rationale", "cited_cases"[]}],
  "risk_findings": [{"code", "severity", "evidence"}],
  "indicator_snapshot": {...}
}
```

#### Subgraph 3. Deterministic Gate — 자율성 L0

> "LLM은 절대 들어오지 않는 신뢰 경계"

- **Tool 없음.** 순수 Python 함수.
- 입력: Risk Subgraph의 `risk_findings` + `policy` + `position_book`
- 출력: `{gate_passed: bool, blocked_reasons: [str], allowed_candidates: [...]}`

**판정 규칙 (예시, 우선순위 순):**
1. `policy.required_fields_missing` → block
2. `position_book.daily_loss_pct >= policy.daily_loss_limit_pct * 0.9` → block (`loss_limit_near_exceeded`)
3. `candidate.amount_krw > policy.max_order_amount_krw` → block (`order_size_exceeded`)
4. `candidate.symbol not in policy.allowed_buy_coins and candidate.action == "buy"` → block
5. `data_staleness > 60s` → block (`data_insufficient`)
6. 이외 → pass

→ **이 노드가 결정론적이어야 컴플라이언스/감사 가능.** LLM이 들어오면 같은 입력에 다른 결과 → 금융 서비스에서 치명적.

#### Subgraph 4. HITL Approval — 자율성 L0 + 사용자

> "Gate 통과 후 페이퍼 실행 직전, 1회 사용자 승인"

- LangGraph `interrupt()` 호출 → FE가 승인 카드 렌더 → `Command(resume={...})`로 재개
- 데모 모드에서는 자동 승인 토글 가능 (시연 시간 제약)
- **이 단계 자체에는 LLM 없음**

ref: https://docs.langchain.com/oss/python/langgraph/interrupts

#### Subgraph 5. Execution Subgraph — 자율성 L2 (제한적)

> "승인된 후보를 페이퍼 체결로 변환 + 잔고/이력 갱신"

| Tool 이름 | 입력 | 출력 | 종류 |
|---|---|---|---|
| `simulate_fill(symbol, action, amount, current_price, slippage_bps)` | 주문 파라미터 | 체결가/체결수량/수수료 | Action (시뮬레이터) |
| `update_position_book(user_id, fill)` | 체결 결과 | 갱신된 포지션 | Action (DB write) |
| `write_execution_log(payload)` | 실행 정보 | log_id | Action (DB write) |
| `rollback_execution(execution_id)` | execution_id | rollback 결과 | Action (실패 시) |

**LLM 자율 영역:**
- 슬리피지/수수료 모델 선택 (보수적 vs 공격적)
- 체결 실패 시 부분체결 처리 방식
- 실행 결과 자연어 요약

**LLM 금지 영역:**
- 주문 금액·수량 변경 (Gate가 통과시킨 값 그대로)
- 사용자 정책 무시한 추가 주문

**Structured Output:**
```json
{
  "execution": PaperExecution,
  "position_after": Position,
  "narrative": str
}
```

#### Subgraph 6. Report Subgraph — 자율성 L3 (Self-critique 포함)

> "결과를 사용자에게 설명하고 자기 출력을 평가"

| Tool 이름 | 입력 | 출력 | 종류 |
|---|---|---|---|
| `query_execution_history(user_id, range)` | 기간 | 실행 로그 배열 | Data |
| `query_blocked_history(user_id, range)` | 기간 | 보류 로그 배열 | Data |
| `search_market_cases(query, top_k)` | 자연어 | 과거 사례 RAG | RAG |
| `format_report(template, data)` | 템플릿/데이터 | 마크다운 리포트 | Action |
| `judge_report_quality(report, rubric)` | 리포트, 평가표 | `{score, issues[]}` | LLM-as-judge |

**자율성 L3 흐름 (Self-Refine):**
1. report_agent가 초안 생성
2. `judge_report_quality` 호출 → 점수 < 임계값이면
3. issues를 컨텍스트에 추가 → 재생성 (최대 N회)
4. 통과 또는 N회 도달 시 종료

**LLM 자율 영역:**
- 리포트 구조 (요약→근거→리스크→다음 행동)
- 어떤 과거 사례를 인용할지
- 자기 출력의 약점 식별

**LLM 금지 영역:**
- 수치 데이터 자체 (도구가 가져온 값만 사용, 환각 금지)
- "수익 보장 / 확정적 예측" 표현 (가드레일 후처리)

ref Self-Refine: https://arxiv.org/abs/2303.17651
ref LLM-as-judge: https://arxiv.org/abs/2306.05685

---

### 4-D.2 자율성 매트릭스 한눈에

| Subgraph | 자율성 | LLM 호출? | Tool 수 | 결정론 영역 | 자율 영역 |
|---|:-:|:-:|:-:|---|---|
| Policy | L2 | ✓ | 5 | 스키마 검증, enum 화이트리스트 | RAG 검색, 누락 항목 질문, 자연어→정책 매핑 |
| Risk | L2 | ✓ | 6 | 임계값 비교, 게이트 산식 | 지표 호출 순서, 사례 매칭, 후보 추천 |
| Gate | **L0** | ✗ | 0 | **전부** | — |
| Approval | L0 + Human | ✗ | 0 | 흐름 제어 | 사용자 판단 |
| Execution | L2 (제한) | ✓ | 4 | 금액·수량 불변 | 슬리피지 모델, 실패 처리, 자연어화 |
| Report | **L3** | ✓ | 5 | 수치 인용, 표현 가드레일 | 리포트 구조, 사례 인용, 자기 평가 |

**합계:** Tool 20개, LLM 호출 노드 4개, Self-critique 1개, HITL 1개.

→ 발표 시 한 줄 정당화: **"Macro flow는 결정론적 workflow로 컴플라이언스를 확보하고, micro flow는 ReAct sub-agent로 자율성을 확보했습니다. Anthropic의 Orchestrator-workers 패턴이며, 신뢰 경계(Gate)는 LLM이 들어가지 않는 결정론 영역으로 격리했습니다."**

---

## 5. 1주일 일정 권장 (옵션 D 기준, 인원 분담)

전제: AI 3명 중 1명이 RAG/룰카탈로그, 1명이 Risk/Execution sub-agent, 1명이 Report/Eval. BE는 도구 백엔드 제공.

| Day | AI-1 (Policy + RAG) | AI-2 (Risk + Execution) | AI-3 (Report + Eval) | 공통 마일스톤 |
|---|---|---|---|---|
| 1 | 룰 카탈로그 JSON 20개 + Chroma 셋업 | LangGraph 골격 + StateGraph reducer 정의 | LLM-as-judge rubric 초안 + Ragas 셋업 | `create_react_agent` 헬로월드 통과 |
| 2 | `search_risk_rules`, `validate_policy_schema` 도구 + Policy sub-agent | `get_market_snapshot`, `compute_indicator` 도구 + Risk sub-agent | Report sub-agent + `format_report` | sub-agent 3개 단위 테스트 |
| 3 | Policy Structured Output 강제 + 정책 스키마 v1 | 결정론 Gate 함수 + `compare_to_policy` | `judge_report_quality` + Self-Refine 루프 (max 2회) | 시드 시나리오 3개 JSON 확정 |
| 4 | RAG `search_market_cases` 추가 + 인용 표시 | `simulate_fill` + `update_position_book` + Execution sub-agent | LangSmith dataset 등록 + 평가 1회 실행 | HITL Interrupt + Checkpointer(SQLite) E2E 통과 |
| 5 | (예비/디버깅) | (예비/디버깅) | 평가 리포트 시각화 | 발표 리허설 + 백업 영상 녹화 |

**산출물 체크포인트 (Day 4 끝):**
- [ ] Policy sub-agent가 RAG로 룰 추천 → 사용자 폼에 자동 채움
- [ ] Risk sub-agent가 도구 3+개 호출 후 후보 생성
- [ ] Gate가 결정론적으로 통과/차단
- [ ] HITL Interrupt가 FE에 승인 카드 띄움 → 승인 시 Execution 진행
- [ ] Execution이 포지션북/잔고 갱신
- [ ] Report가 Self-critique 1회 후 최종본 출력
- [ ] LangSmith trace로 모든 단계 가시화

**Agentic 7종 시연 체크:**
1. **Tool calling** (각 sub-agent에서)
2. **Dynamic action selection** (LLM이 도구 순서 결정)
3. **RAG** (Policy/Report)
4. **Multi-agent** (Subgraph 4개)
5. **HITL** (Interrupt)
6. **Memory/Persistence** (Checkpointer)
7. **Self-improvement** (Report Self-Refine)

---

## 6. 발표 시 피해야 할 표현

채점자가 "이게 왜 agent인가?"라고 물었을 때 **다음 답은 감점된다**:

- ❌ "LangGraph를 써서 agent입니다" → LangGraph는 workflow도 그린다
- ❌ "3개 Agent로 분리했습니다" → 노드 분리 = agent 분리 아님
- ❌ "정책 기반으로 자율 실행합니다" → 사전 정책 = 자율 아님

대신 다음과 같이 답할 수 있어야 함:

- ✅ **"Macro flow는 결정론적 workflow로 컴플라이언스를 확보하고, micro flow는 ReAct sub-agent로 자율성을 확보한 하이브리드입니다 (Anthropic Orchestrator-workers / OpenAI Manager pattern)."** ← 가장 강력한 한 줄
- ✅ "신뢰 경계인 Risk Gate는 LLM이 들어가지 않는 결정론 영역으로 격리해, 같은 입력에 항상 같은 판정이 나옵니다 (감사 가능)"
- ✅ "각 sub-agent는 ReAct loop로 도구 호출 순서를 동적으로 결정합니다"
- ✅ "Structured Output + Pydantic으로 출력 안정성을 강제했습니다"
- ✅ "LangGraph Interrupt로 실행 직전 승인 게이트를 두어 HITL을 구현했습니다"
- ✅ "Checkpointer로 thread별 컨텍스트를 보존해 후속 요청에서 학습 효과가 있습니다"
- ✅ "Report sub-agent는 LLM-as-judge로 자기 출력을 평가해 임계값 미달 시 재생성합니다 (Self-Refine)"

---

## 7. 정리해야 할 추가 질문

1. 평가 기준에 "agentic의 정의" 채점 항목이 명시되어 있는가? (있다면 옵션 A 이상 필수)
2. LLM 비용 예산은? (캐시 미사용 시 발표 리허설에서 $$ 의외로 큼)
3. Upbit 시세 조회는 LLM tool로 노출할 것인가, BE에서 미리 가져와 전달할 것인가? (전자가 진짜 agentic)
4. `submit_paper_order` 직전 HITL을 데모로 보여줄 의향이 있는가? (가장 인상적인 agentic 데모)
5. "Reflexion / Self-Refine" 같은 자기 개선 루프를 1개라도 넣을 것인가? (없으면 그냥 LLM 한 번 호출과 차이 없음)
6. 평가 데이터셋(시드 시나리오 3~5개)을 LangSmith dataset으로 등록해 reproducible eval을 할 것인가?
7. MCP로 Upbit/지표 도구를 노출해 외부 채점자가 테스트할 수 있게 할 것인가?

---

## 8. 종합 점수 (Agentic 적합성 한정)

| 차원 | 점수 | 비고 |
|---|---:|---|
| 자율성 (다음 행동 결정 주체가 LLM인가) | 1/10 | 전부 코드 경로 고정 |
| Tool use | 0/10 | 설계에 없음 |
| Multi-agent 구조 | 2/10 | 순차 노드일 뿐 |
| Memory / Persistence | 1/10 | Checkpointer 미명시 |
| Human-in-the-Loop | 2/10 | "보류"만 있고 승인 루프 없음 |
| Self-improvement (Reflexion/Self-Refine) | 0/10 | 없음 |
| Structured Output / 안정성 | 3/10 | 원칙만 있고 구현 없음 |
| Guardrails (구현 수준) | 2/10 | 라이브러리·검증 없음 |
| Evaluation 체계 | 1/10 | 메트릭 정의 모호 |
| **Agentic 종합** | **1.5/10** | "Agent라고 부를 수 없는 workflow" |

---

## 9. 마지막 한 줄

> **현재 설계는 "안전한 자동화" 쪽으로 너무 치우친 나머지, 시연할 자율성이 0이 되었다.**
> 1주일 데모에서 "왜 agent인가"를 묻는 순간 답할 게 없다.
> 옵션 A(ReAct + Tools + HITL + Structured Output)만 추가해도 agentic 5종이 다 들어가고 일정 안에 끝낼 수 있다.

---

## 부록: 참고 문헌 한 곳에 모음

**Agentic 정의 / 패턴**
- Anthropic — Building Effective Agents (2024-12): https://www.anthropic.com/engineering/building-effective-agents
- OpenAI — A Practical Guide to Building Agents (2025-04): https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf

**ReAct / Reflexion / Self-Refine**
- ReAct (Yao+ 2022): https://arxiv.org/abs/2210.03629
- Reflexion (Shinn+ 2023): https://arxiv.org/abs/2303.11366
- Self-Refine (Madaan+ 2023): https://arxiv.org/abs/2303.17651

**LangGraph**
- Overview: https://docs.langchain.com/oss/python/langgraph/overview
- Graph API & Reducers: https://docs.langchain.com/oss/python/langgraph/graph-api
- Multi-agent patterns: https://docs.langchain.com/oss/python/langchain/multi-agent
- Interrupts (HITL): https://docs.langchain.com/oss/python/langgraph/interrupts
- Persistence / Checkpointer: https://docs.langchain.com/oss/python/langgraph/persistence
- Streaming: https://docs.langchain.com/oss/python/langgraph/streaming
- Subgraphs: https://docs.langchain.com/oss/python/langgraph/use-subgraphs
- create_react_agent: https://langchain-ai.github.io/langgraph/reference/agents/
- Supervisor: https://reference.langchain.com/python/langgraph-supervisor
- Swarm: https://reference.langchain.com/python/langgraph-swarm
- HITL blog: https://blog.langchain.com/making-it-easier-to-build-human-in-the-loop-agents-with-interrupt/

**Tool use / Function calling / Structured outputs**
- OpenAI Function calling: https://developers.openai.com/api/docs/guides/function-calling
- Anthropic Tool use: https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview
- OpenAI Structured Outputs: https://developers.openai.com/api/docs/guides/structured-outputs
- Instructor: https://python.useinstructor.com/

**Evaluation / LLM-as-judge**
- LangSmith Evaluation: https://docs.langchain.com/langsmith/evaluation-concepts
- LLM-as-judge (Zheng+ 2023): https://arxiv.org/abs/2306.05685
- Ragas: https://docs.ragas.io/

**Guardrails**
- NeMo Guardrails: https://github.com/NVIDIA/NeMo-Guardrails
- Guardrails AI: https://www.guardrailsai.com/
- OpenAI Moderation: https://developers.openai.com/api/docs/guides/moderation

**Caching / Tool Standard**
- Anthropic Prompt Caching: https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
- MCP: https://modelcontextprotocol.io/

**Trading / Backtesting (페이퍼 실행 비교용)**
- QuantConnect Backtesting: https://www.quantconnect.com/docs/v2/cloud-platform/backtesting
- Backtrader Quickstart: https://www.backtrader.com/docu/quickstart/quickstart/
