# autocoin-ai · Agentic Upgrade 구현 계획서

> **상태**: 계획 / 미구현
> **작성일**: 2026-05-09
> **범위**: AI 저장소 + BE(autocoin-api) + FE(autocoin-web) 모두 영향

---

## 0. 한 줄 요약

> **"챗봇으로 자연어 받아서 → LLM이 의도/persona를 구조화 → Risk Agent가 도구함을 보고 스스로 조사·판단 → 모든 호출이 trace로 남음"**

기존 결정론 LangGraph 골격(`policy → risk → evaluator → execution`)은 **그대로 유지**하고,
앞에 `intake`, `strategy`를 끼우고 `risk`를 `risk_agent + risk_gate`로 분리한다.

---

## 1. 확정 사항 (의사결정 결과)

| # | 항목 | 결정 |
|---|---|---|
| 1 | NL 파싱 위치 | **C — AI 안에서** (`intake` 노드 신설) |
| 2 | Persona 결정 방식 | **B/C 하이브리드** — 계정 디폴트 + 발화 명시 시 override |
| 3 | 모호한 입력 처리 | v3 단계로 (MVP는 즉시 HOLD) |
| 4 | 도구 권한 차등 | **C** — 도구함 통일 + persona별 `required_tools` 강제 |
| 5 | Trace 레벨 | **Lv2** — tool 이름·인자·결과 + 호출 직전 thought |
| 6 | 거래소 | **Binance Spot Testnet** 유지 |
| 7 | 구현 방식 | 바이브 코딩 + 사람 분담 |

---

## 2. 새 흐름 (Before / After)

### Before (현재)
```
__start__ → policy → risk → evaluator → __end__
```

### After (Agentic)
```
__start__
  → intake          [LLM] 자연어 → 구조화 + persona 추론
  → policy          [코드] 필드 검증 + 정규화
  → strategy        [LLM] 트레이더: 살까/얼마나/얼마나 확신해
  → risk_agent      [LLM + Tools] 도구함으로 능동 조사 (ReAct 루프)
  → risk_gate       [코드] hard limit·필수 도구 사후 검증
  → evaluator       [코드] 근거 충분성 누적 체크
  → __end__
```

각 노드의 **입력→출력**:

| 노드 | 입력 | 출력 추가 |
|---|---|---|
| `intake` | `request_context.user_input.text` (자연어) + `persona_default` | `normalized_order_intent`, `inferred_persona`, `persona_override_reason` |
| `policy` | 위의 normalized intent | `policy_context.policy_refs`, `policy_context.persona_bounds` |
| `strategy` | persona_bounds, market_snapshot | `llm_proposal {action, size_usd, conviction, rationale}` |
| `risk_agent` | proposal + persona | `risk_assessment {verdict, score, concerns}`, `risk_tool_calls[]` |
| `risk_gate` | 위의 둘 | `lifecycle_status` 결정 |
| `evaluator` | verification_checks 누적 | 통과 / HOLD |

---

## 3. AI 저장소 변경 (autocoin-ai)

### 3.1 새 폴더 / 파일

```
src/autocoin_ai/
├── nodes/
│   ├── intake.py        🆕 NL → 구조화 (LLM)
│   ├── policy.py            (기존 그대로, persona_bounds 박는 부분만 추가)
│   ├── strategy.py      🆕 Trader LLM
│   ├── risk_agent.py    🆕 ReAct 도구 루프
│   ├── risk_gate.py     🆕 결정론 사후 검증
│   ├── evaluator.py         (그대로)
│   └── execution.py         (그대로)
├── tools/               🆕 도구함 (Risk Agent 전용)
│   ├── __init__.py
│   ├── registry.py          ← @tool 데코레이터 + dispatch
│   ├── account_tools.py     ← BE proxy 호출
│   ├── market_tools.py      ← BE proxy 호출
│   ├── policy_tools.py      ← 결정론 (persona bounds 등)
│   └── be_client.py     🆕 BE 도구 endpoint 호출용 HTTP 클라이언트
├── prompts/             🆕
│   ├── intake_prompt.py
│   ├── strategy_prompt.py
│   └── risk_agent_prompt.py
├── personas.py          🆕 PERSONA_PROFILES 상수
└── llm.py                   ← 실제 호출 로직 채우기 (지금은 hook만)
```

### 3.2 `personas.py` (확정 정의)

```python
PERSONA_PROFILES = {
    "CONSERVATIVE": {
        "max_position_pct": 0.05,
        "allowed_symbols": ["BTCUSDT", "ETHUSDT"],
        "max_order_usd": "100",
        "min_conviction": 0.85,
        "allowed_order_types": ["MARKET"],
        "required_tools": [
            "get_balance", "check_persona_bounds",
            "get_volatility", "get_economic_calendar",
        ],
    },
    "MODERATE": {
        "max_position_pct": 0.15,
        "allowed_symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT"],
        "max_order_usd": "500",
        "min_conviction": 0.65,
        "allowed_order_types": ["MARKET", "LIMIT"],
        "required_tools": [
            "get_balance", "check_persona_bounds", "get_volatility",
        ],
    },
    "AGGRESSIVE": {
        "max_position_pct": 0.30,
        "allowed_symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT", "DOGEUSDT", "ADAUSDT"],
        "max_order_usd": "2000",
        "min_conviction": 0.50,
        "allowed_order_types": ["MARKET", "LIMIT"],
        "required_tools": [
            "get_balance", "check_persona_bounds",
        ],
    },
}
```

### 3.3 State (`models.py`) 새 필드

```python
class AgentState(TypedDict):
    # ── 기존 ───────────────────────────────────────
    run_id: str
    request_context: JsonDict       # immutable
    policy_context: JsonDict
    normalized_order_intent: JsonDict
    lifecycle_status: str
    hold_reason: Optional[str]
    decision_trace: Dict[str, TraceEntry]
    verification_checks: List[VerificationCheck]
    completion_payload: JsonDict
    execution_result: JsonDict
    be_rejection_evidence: JsonDict
    report: JsonDict
    resume_history: List[JsonDict]
    decision_trace_history: List[DecisionTraceHistoryEntry]
    
    # ── 🆕 Agentic 추가 ───────────────────────────
    inferred_persona: str            # "CONSERVATIVE" | "MODERATE" | "AGGRESSIVE"
    persona_override_reason: NotRequired[str]   # 발화 override 사유
    llm_proposal: JsonDict           # strategy 노드 결과
    risk_assessment: JsonDict        # risk_agent 결과
    risk_tool_calls: List[JsonDict]  # ReAct 도구 호출 chain
```

### 3.4 `constants.py` 추가

```python
# 새 stage
TRACE_STAGES = ("intake", "policy", "strategy", "risk", "evaluator", "execution", "run_summary")
CHECK_STAGES = ("intake", "policy", "strategy", "risk", "evaluator", "execution", "be_revalidation")

# 새 hold reason
HOLD_INPUT_AMBIGUOUS = "HOLD_INPUT_AMBIGUOUS"
HOLD_LOW_CONVICTION = "HOLD_LOW_CONVICTION"
HOLD_RISK_AGENT_FLAGGED = "HOLD_RISK_AGENT_FLAGGED"
HOLD_QUALITY_CONCERNS = "HOLD_QUALITY_CONCERNS"

# Persona
PERSONA_CONSERVATIVE = "CONSERVATIVE"
PERSONA_MODERATE = "MODERATE"
PERSONA_AGGRESSIVE = "AGGRESSIVE"
```

### 3.5 노드별 핵심 로직 (의사 코드)

#### `intake_node`
```python
def intake_node(state):
    text = state["request_context"]["user_input"].get("text")
    if not text:
        # MVP: 텍스트 없으면 기존 구조화 입력 그대로 사용
        return state
    
    persona_default = state["request_context"]["user_input"].get("persona_default", "MODERATE")
    
    parsed = gemini.generate(
        prompt=INTAKE_PROMPT.format(text=text, persona_default=persona_default),
        response_schema={
            "symbol": "string (e.g., BTCUSDT)",
            "side": "BUY | SELL",
            "type": "MARKET | LIMIT",
            "size_usd": "string number",
            "inferred_persona": "CONSERVATIVE | MODERATE | AGGRESSIVE",
            "persona_override_reason": "string | null",
            "ambiguity_score": "float 0-1",
        }
    )
    
    if parsed["ambiguity_score"] > 0.5:
        # MVP: 모호하면 즉시 HOLD
        next_state["lifecycle_status"] = LIFECYCLE_HOLD
        next_state["hold_reason"] = HOLD_INPUT_AMBIGUOUS
        return next_state
    
    next_state["normalized_order_intent"] = {
        "symbol": parsed["symbol"], "side": parsed["side"],
        "type": parsed["type"], "quoteOrderQty": parsed["size_usd"],
    }
    next_state["inferred_persona"] = parsed["inferred_persona"]
    if parsed["persona_override_reason"]:
        next_state["persona_override_reason"] = parsed["persona_override_reason"]
    
    set_trace(next_state, "intake", ["NL_PARSED"], ["request_context.user_input.text"], PASS_ACTION)
    append_check(next_state, "intake_parse_ok", "intake", "pass", ["normalized_order_intent"])
    return next_state
```

#### `policy_node` (수정)
```python
# 기존 로직 + persona_bounds 박기
persona = state.get("inferred_persona", "MODERATE")
state["policy_context"]["persona"] = persona
state["policy_context"]["persona_bounds"] = PERSONA_PROFILES[persona]
```

#### `strategy_node`
```python
def strategy_node(state):
    persona = state["policy_context"]["persona"]
    bounds = state["policy_context"]["persona_bounds"]
    intent = state["normalized_order_intent"]
    market = state["request_context"]["user_input"].get("market_snapshot", {})
    
    proposal = gemini.generate(
        prompt=STRATEGY_PROMPT.format(persona=persona, intent=intent, market=market, bounds=bounds),
        response_schema={
            "action": "BUY | SELL | HOLD",
            "size_usd": "string",
            "conviction": "float 0-1",
            "rationale": "string",
        }
    )
    
    state["llm_proposal"] = proposal
    set_trace(state, "strategy",
              [proposal["action"], f"CONVICTION_{proposal['conviction']:.2f}"],
              ["llm_proposal"], proposal["action"], notes=proposal["rationale"])
    append_check(state, "strategy_proposal_complete", "strategy", "pass", ["llm_proposal"])
    return state
```

#### `risk_agent_node` (ReAct 루프)
```python
MAX_TOOL_CALLS = 8

def risk_agent_node(state):
    persona = state["policy_context"]["persona"]
    bounds = state["policy_context"]["persona_bounds"]
    
    tool_specs = [t.spec() for t in REGISTRY.values()]
    messages = [
        {"role": "system", "content": RISK_AGENT_PROMPT.format(persona=persona, bounds=bounds)},
        {"role": "user", "content": json.dumps({
            "proposal": state["llm_proposal"],
            "intent": state["normalized_order_intent"],
            "run_id": state["run_id"],
        })},
    ]
    
    tool_calls_log = []
    for step in range(1, MAX_TOOL_CALLS + 1):
        response = gemini.generate_with_tools(messages, tools=tool_specs)
        
        if response.is_final:
            state["risk_assessment"] = response.json
            break
        
        for call in response.tool_calls:
            result = dispatch(call.name, call.args, run_id=state["run_id"])
            tool_calls_log.append({
                "step": step,
                "thought": call.thought,
                "tool": call.name,
                "args": call.args,
                "result": result,
            })
            messages.append({"role": "tool", "name": call.name, "content": json.dumps(result)})
    
    state["risk_tool_calls"] = tool_calls_log
    set_trace(state, "risk",
              [state["risk_assessment"]["verdict"]],
              [f"risk_tool_calls[{i}]" for i in range(len(tool_calls_log))],
              state["risk_assessment"]["verdict"],
              notes=state["risk_assessment"].get("reasoning", ""))
    append_check(state, "risk_agent_investigation", "risk", "pass", ["risk_assessment", "risk_tool_calls"])
    return state
```

#### `risk_gate_node` (결정론 사후 검증)
```python
def risk_gate_node(state):
    assessment = state["risk_assessment"]
    proposal = state["llm_proposal"]
    bounds = state["policy_context"]["persona_bounds"]
    
    # 1. Hard limit 위반 체크 (LLM이 뚫고 들어왔어도 여기서 차단)
    size = Decimal(proposal.get("size_usd", "0"))
    if size > Decimal(bounds["max_order_usd"]):
        state["lifecycle_status"] = LIFECYCLE_NO_ORDER
        append_check(state, "hard_size_limit", "risk", "fail", ["llm_proposal.size_usd"])
        return state
    
    if proposal.get("symbol") not in bounds["allowed_symbols"]:
        state["lifecycle_status"] = LIFECYCLE_NO_ORDER
        append_check(state, "hard_symbol_allowlist", "risk", "fail", ["llm_proposal.symbol"])
        return state
    
    # 2. 필수 도구 호출 검증
    called = {t["tool"] for t in state["risk_tool_calls"]}
    required = set(bounds["required_tools"])
    if not required.issubset(called):
        state["lifecycle_status"] = LIFECYCLE_FAILED
        missing = required - called
        append_check(state, "required_tools_missing", "risk", "fail", list(missing))
        return state
    
    # 3. Conviction 임계값
    if Decimal(str(proposal["conviction"])) < Decimal(str(bounds["min_conviction"])):
        state["lifecycle_status"] = LIFECYCLE_HOLD
        state["hold_reason"] = HOLD_LOW_CONVICTION
        return state
    
    # 4. LLM verdict → lifecycle 매핑
    verdict = assessment.get("verdict", "REJECT")
    if verdict == "ALLOW":
        state["lifecycle_status"] = LIFECYCLE_READY_FOR_BE
    elif verdict == "HOLD":
        state["lifecycle_status"] = LIFECYCLE_HOLD
        state["hold_reason"] = HOLD_RISK_AGENT_FLAGGED
    else:
        state["lifecycle_status"] = LIFECYCLE_NO_ORDER
    
    append_check(state, "risk_gate_complete", "risk", "pass", ["lifecycle_status"])
    return state
```

### 3.6 도구 (`tools/`) — MVP 도구 5개

| 도구 | 카테고리 | 데이터 출처 | 비고 |
|---|---|---|---|
| `get_balance(asset)` | 계정 | **BE proxy** | Binance Testnet 잔고 |
| `check_persona_bounds(action, symbol, size_usd)` | 정책 | **AI 내부 (결정론)** | personas.py 참조 |
| `get_volatility(symbol, days)` | 시장 | **BE proxy** | Binance Testnet kline |
| `get_concentration_risk(symbol, proposed_size)` | 계정 | **BE proxy** | balance 기반 계산 |
| `get_economic_calendar(hours_ahead)` | 신호 | **BE proxy** | (v2: mock 가능) |

> **원칙**: AI는 Binance Testnet을 **직접 호출 안 함**. 모두 BE의 `/tools/...` endpoint를 통해서만.
> 이 원칙이 `docs/AI.md` 7번 "금지 사항"과 일치함.

### 3.7 HTTP API 변경

기존 endpoint는 그대로 유지. 입력 schema만 확장.

`POST /runs/start` 의 body 예:
```jsonc
{
  "run_id": "airun_001",
  "request_context": {
    "request_id": "req_001",
    "request_type": "PLACE_ORDER_TEST",
    "requested_at": "2026-05-09T10:00:00+09:00",
    "user_input": {
      // ⭐ 새 필드 (둘 중 하나)
      "text": "BTC 5만원치 공격적으로 사줘",       // NL 입력
      "persona_default": "MODERATE",
      
      // 또는 기존 구조화 입력 (둘 다 보내도 OK, text 우선)
      "symbol": "BTCUSDT",
      "side": "BUY",
      "type": "MARKET",
      "quoteOrderQty": "50",
      
      // BE가 미리 박아주는 시장 스냅샷
      "market_snapshot": {
        "btc_price_usd": "67432",
        "fetched_at": "2026-05-09T10:00:00+09:00"
      }
    }
  },
  "policy_context": {
    "policy_refs": ["policy.symbol_allowlist", "policy.spot_testnet_only"]
    // persona_bounds는 AI가 채움 (intake 결과 기반)
  }
}
```

응답 새 필드:
```jsonc
{
  // ... 기존 필드
  "inferred_persona": "AGGRESSIVE",
  "persona_override_reason": "사용자 발화에 '공격적으로' 포함",
  "llm_proposal": { "action": "BUY", "size_usd": "50", "conviction": 0.71, "rationale": "..." },
  "risk_assessment": { "verdict": "HOLD", "score": 0.65, "concerns": ["FOMC 18h ahead"] },
  "risk_tool_calls": [
    { "step": 1, "thought": "잔고 확인", "tool": "get_balance", "args": {"asset": "USDT"}, "result": {"free": "5000"} },
    // ...
  ]
}
```

---

## 4. BE 변경 (autocoin-api)

### 4.1 영향 범위 — **중간 수준**

BE는 다음을 새로 만들어야 함:
1. **NL 텍스트 라우팅** — `text` 필드 그대로 AI에 전달
2. **시장 스냅샷 사전 패키징** — `request_context`에 `market_snapshot` 박기
3. **🆕 Tool Proxy Endpoints** — AI의 risk_agent 도구가 호출할 BE 측 endpoint들

### 4.2 새 BE Endpoints (Tool Proxy)

AI는 Binance를 직접 못 부르므로, BE가 도구 호출 proxy 역할.

```
POST /tools/account/balance
  body: { "asset": "USDT", "run_id": "..." }
  resp: { "free": "5000", "locked": "0", "total": "5000" }

POST /tools/market/volatility
  body: { "symbol": "BTCUSDT", "days": 7, "run_id": "..." }
  resp: { "atr": 0.045, "stdev": 0.038, "window_days": 7 }

POST /tools/account/concentration
  body: { "symbol": "BTCUSDT", "proposed_size_usd": "200", "run_id": "..." }
  resp: { "current_pct": 0.08, "after_pct": 0.12 }

POST /tools/calendar/economic
  body: { "hours_ahead": 24, "run_id": "..." }
  resp: { "events": [{ "name": "FOMC", "in_hours": 18, "impact": "HIGH" }] }
```

**인증**: 모든 도구 endpoint는 같은 `run_id`의 활성 run에서만 호출 가능. BE가 `run_id` 화이트리스트 관리.

**캐싱**: 같은 `(run_id, tool, args)` 조합은 캐시 (LLM이 같은 도구 두 번 부르는 일 방지).

### 4.3 기존 BE 흐름 변경

```
이전: FE (구조화 dict) → BE → AI start
이후: FE (text 또는 dict) → BE
       ├ market_snapshot 패키징
       ├ persona_default 결정 (사용자 계정 설정)
       ├ AI start 호출
       └ (AI가 도구 호출하면 응답)
```

BE는 NL 자체를 파싱하지 않음. 단순 라우팅 + 도구 데이터 제공.

### 4.4 BE 영향 정리

| 변경 | 신규/수정 | 난이도 |
|---|---|---|
| `request_context.user_input.text` 라우팅 | 수정 | ⭐ |
| `market_snapshot` 사전 패키징 | 신규 | ⭐⭐ |
| `persona_default` 사용자 계정 필드 | 신규 (DB 마이그레이션) | ⭐⭐ |
| Tool proxy endpoints 5개 | 신규 | ⭐⭐⭐ |
| Tool 호출 캐싱 | 신규 | ⭐⭐ |
| `run_id` 인증/화이트리스트 | 신규 | ⭐⭐ |

---

## 5. FE 변경 (autocoin-web)

### 5.1 영향 범위 — **큰 폭**

UX가 완전히 달라짐. 폼 입력 → 챗봇 입력.

### 5.2 새 화면 / 컴포넌트

#### A. 챗 입력 UI
- 텍스트 인풋 (자연어)
- 빠른 예시 ("BTC 5만원 사줘", "공격적으로 ETH 10만원")
- 전송 버튼

#### B. Persona 프로필 화면
- 사용자가 본인 디폴트 persona 선택 (CONSERVATIVE/MODERATE/AGGRESSIVE)
- 각 persona의 한도 시각화
- 발화 override 시 알림

#### C. AI 처리 진행 화면 (스트리밍)
```
✓ 입력 이해 (intake) — "공격적으로" 발화 감지 → AGGRESSIVE
✓ 정책 검증 (policy)
✓ 트레이더 판단 (strategy) — BUY $50, conviction 0.71
🔄 리스크 조사 (risk_agent)
   - get_balance("USDT") → $5000
   - check_persona_bounds(...) → OK
   - get_volatility(...) → 4.5% (정상)
   - get_economic_calendar(24) → FOMC 18h
   ↳ verdict: HOLD ("FOMC 임박")
✓ 검증 통과 → BE 핸드오프 또는 HOLD
```

#### D. Decision Trace 시각화
- stage별 reason_codes 펼침
- risk_tool_calls 타임라인 (각 호출의 thought + result)
- HOLD 시 concerns 강조

#### E. HOLD / Resume UI
- HOLD 사유에 따른 안내
- 보완 입력 폼 (v2)
- approval 토글 (v2)

### 5.3 FE 영향 정리

| 변경 | 신규/수정 | 난이도 |
|---|---|---|
| 챗 입력 컴포넌트 | 신규 | ⭐⭐ |
| Persona 프로필 화면 | 신규 | ⭐⭐ |
| AI 진행 스트리밍 표시 | 신규 (SSE 또는 폴링) | ⭐⭐⭐ |
| Decision Trace 시각화 | 신규 | ⭐⭐⭐ |
| Tool calls 타임라인 | 신규 | ⭐⭐⭐ |
| HOLD/Resume UX | 수정 | ⭐⭐ |

> **선택**: 진행 스트리밍은 SSE(Server-Sent Events)로 구현하면 가장 깔끔. BE가 AI 응답을 SSE로 흘려주면 됨.

---

## 6. 인터페이스 계약 변경 요약

### 6.1 FE → BE
```jsonc
// 기존
{ "symbol": "BTCUSDT", "quoteOrderQty": "50", "side": "BUY", "type": "MARKET" }

// 신규
{
  "text": "BTC 5만원치 공격적으로 사줘",
  // 또는 기존 구조화도 그대로 받음 (호환성 유지)
}
```

### 6.2 BE → AI (`POST /runs/start`)
- `request_context.user_input.text` 추가
- `request_context.user_input.persona_default` 추가
- `request_context.user_input.market_snapshot` 추가

### 6.3 AI → BE (응답)
- `inferred_persona`, `persona_override_reason`
- `llm_proposal`, `risk_assessment`
- `risk_tool_calls` (Lv2 trace)

### 6.4 AI → BE (도구 호출, 신규 방향)
- `POST {BE_URL}/tools/...` — AI가 BE의 도구를 호출

---

## 7. 작업 분담 (3인 가정)

### 👤 AI 담당
- `nodes/intake.py`, `strategy.py`, `risk_agent.py`, `risk_gate.py`
- `tools/` 폴더 전체 (registry + dispatch + 5개 도구 client)
- `prompts/` 3개 템플릿
- `personas.py`, `models.py`, `constants.py` 확장
- `llm.py` 실제 Gemini 호출 채우기
- `tools/be_client.py` (BE 도구 endpoint 호출 클라이언트)

**MVP 산출물**: 자연어 입력 → trace 포함 응답까지 동작

### 👤 BE 담당
- `request_context.user_input.text` 라우팅
- `market_snapshot` 패키징 로직
- 사용자 계정에 `persona_default` 추가 (DB 마이그)
- 5개 tool proxy endpoint (`/tools/...`)
- run_id 인증 + 호출 캐싱

**MVP 산출물**: AI가 도구 호출하면 Binance Testnet 데이터 회신

### 👤 FE 담당
- 챗 입력 컴포넌트
- Persona 프로필 페이지
- 진행 스트리밍 표시 (SSE)
- Decision trace + tool_calls 시각화
- HOLD/Resume UX

**MVP 산출물**: 사용자가 자연어 보내고 AI 처리 chain을 볼 수 있는 화면

---

## 8. MVP 페이즈

### 🥇 Phase 1 — 1주차 (각자 단독 동작)
- AI: intake + strategy + 결정론 risk (도구 없이) 흐름 동작
- BE: text 라우팅 + market_snapshot 1개 필드만
- FE: 챗 입력 + 단순 결과 표시

**검증**: "BTC 5만원 사줘" → strategy 노드까지 LLM 호출되고 trace 생김

### 🥈 Phase 2 — 2주차 (Risk Agent + 도구 3개)
- AI: risk_agent + risk_gate 노드, 도구 3개 (`get_balance`, `check_persona_bounds`, `get_volatility`)
- BE: tool proxy endpoint 3개
- FE: tool_calls 타임라인 시각화

**검증**: 같은 발화를 3개 persona로 돌렸을 때 다른 결정이 나오는지

### 🥉 Phase 3 — 3주차 (도구 확장 + Persona 추론)
- AI: 도구 5개로 확장, persona 발화 override 정교화
- BE: 도구 endpoint 추가, calendar/concentration
- FE: persona override 알림 UI, HOLD 안내 UX

### ✨ Phase 4 — 폴리싱
- Critic LLM (evaluator 강화)
- Self-correction 루프 (HOLD 시 strategy에 피드백)
- 데모 시나리오 매트릭스 정리

---

## 9. 위험 / 검토 사항

| 위험 | 완화 |
|---|---|
| LLM 환각으로 잘못된 의도 추출 | `intake`의 `ambiguity_score` + `risk_gate`의 hard limit |
| LLM이 persona allowlist 밖 심볼 추천 | `risk_gate`가 차단 |
| 도구 무한 호출 | `MAX_TOOL_CALLS = 8` 강제 |
| 같은 도구 반복 호출 (비용↑) | BE 캐싱 + AI 측 dedup |
| LLM 응답 schema 깨짐 | structured output 강제 + 파싱 실패 시 FAILED |
| 비결정성 ↑ | trace에 모델 버전 + 응답 원문 기록 (재현 가능성) |
| BE 도구 endpoint 인증 누락 | `run_id` 화이트리스트 + 활성 상태 체크 |
| FE 진행 표시 끊김 | SSE 재연결 로직 |

---

## 10. 데모 시나리오 매트릭스 (Phase 2 종료 시)

같은 발화를 persona별로 돌려서 차이 보여주기:

| 발화 | CONSERVATIVE | MODERATE | AGGRESSIVE |
|---|---|---|---|
| "BTC 5만원 사줘" | $50 < $100 OK → BUY | OK → BUY | OK → BUY |
| "BTC 200만원 사줘" | $200 > $100 → NO_ORDER | $200 < $500 → BUY | $200 < $2000 → BUY |
| "DOGE 10만원 사줘" | DOGE 미허용 → NO_ORDER | DOGE 미허용 → NO_ORDER | OK → BUY |
| "BTC 좀 사봐" (모호) | HOLD_INPUT_AMBIGUOUS | HOLD_INPUT_AMBIGUOUS | HOLD_INPUT_AMBIGUOUS |
| "공격적으로 BTC 매수" (보수형 계정) | persona_override → AGGRESSIVE 룰 적용 (사용자 동의 후) | (override 발동 X) | (이미 AGGRESSIVE) |

---

## 11. 환경 변수 추가 (`.env.example`)

```bash
# 기존
GEMINI_API_KEY=...
AI_LLM_PROVIDER=gemini
GEMINI_MODEL=gemini-2.5-flash

# 🆕 Agentic용
AUTOCOIN_BE_URL=http://localhost:8000     # 도구 proxy 호출용
AI_RISK_MAX_TOOL_CALLS=8
AI_TOOL_CACHE_TTL_SECONDS=60
AI_LLM_TEMPERATURE=0                       # 결정성 ↑
```

---

## 12. 문서 업데이트 필요

이 변경에 맞춰 다음 문서들도 업데이트:

- `docs/AI.md` — 새 4 노드 추가 + persona 섹션
- `docs/DATA.md` — 새 State 필드 + tool_call shape
- `docs/ARCHITECTURE.md` — 도구 호출이 AI→BE 방향으로 추가됨을 반영
- `docs/FE.md`, `docs/BE.md` — boundary 계약 갱신
- `docs/TEST_AND_DEMO.md` — 데모 매트릭스 시나리오 추가

---

## 13. 결정 기록 (Decision Log)

| 날짜 | 결정 | 사유 |
|---|---|---|
| 2026-05-09 | NL 파싱을 AI 안(`intake`)에 둠 | 데모로 "AI가 자연어부터 받음" 그림이 강력 |
| 2026-05-09 | Persona는 계정 디폴트 + 발화 override 하이브리드 | 안전성 + 자연스러움 |
| 2026-05-09 | 모호 입력은 MVP에선 즉시 HOLD | Multi-turn은 v3로 |
| 2026-05-09 | 도구함은 통일, persona별 required_tools만 분기 | 코드 깔끔함 |
| 2026-05-09 | Trace Lv2 (thought 포함, full message history 제외) | 비용 대비 가치 최적 |
| 2026-05-09 | 거래소: Binance Testnet 유지 | 안전성 + 기존 코드 활용 |
| 2026-05-09 | AI는 Binance 직접 호출 금지 원칙 유지 → 모든 도구가 BE proxy 통과 | `docs/AI.md` 7번과 일치 |

---

## 14. 다음 액션

1. ☐ 이 문서 팀 공유 + 합의
2. ☐ Phase 1 작업을 GitHub Issue로 분해 (AI/BE/FE 각각)
3. ☐ `personas.py` 한도 값 도메인 검토 (외부 자문 권장)
4. ☐ Gemini structured output 시그니처 PoC (intake 노드부터)
5. ☐ BE의 `market_snapshot` 첫 버전 정의 (어떤 필드를 항상 박을지)
6. ☐ FE 챗 UI 와이어프레임

---

> 📌 이 문서는 변경 시 **Decision Log(13장)에 한 줄 추가**하고 갱신.
