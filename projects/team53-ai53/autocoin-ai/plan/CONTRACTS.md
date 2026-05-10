# autocoin-ai · 계약(Contracts) 사양

> **상태**: 캐노니컬 / AI 자율 실행 기준
> **작성일**: 2026-05-10
> **읽는 사람**: 노드 구현자 / ralph 자동화 루프 / 평가자
> **연관 문서**: `MASTER_PLAN.md` (비전), `PHASES.md` (작업 단위), `FIXTURES.md` (테스트 데이터)

이 문서는 모든 노드의 **입력/출력 schema**, **라우팅 규칙**, **resume 정책**을 잠근다.
하나의 contract 라도 어기면 노드가 통합 실패한다.

---

## §1. Principle / TraderMeta dataclass

### 1.1 `Principle`

`knowledge/{trader_id}/principles.md`의 H2 단위 1개를 표현하는 frozen dataclass.

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Principle:
    chunk_id: str             # "livermore.cut_losses"
    title: str                # H2 텍스트 — "손실은 빠르게 제한"
    content: str              # H2 직후 첫 문단
    keywords: tuple[str, ...] # frontmatter list 파싱
    preferred_action: str     # "HOLD or NO_ORDER when invalidation risk is high"
    avoid_when: str           # "손실 한도, 잔고, 변동성 조건이 불리할 때"
    source_refs: tuple[str, ...]
```

**불변 조건**:
- `Principle`은 frozen이며 노드 간 전달 시 dict로 직렬화: `dataclasses.asdict(p)`
- `state["trader_principles"]`는 `list[dict]` (TypedDict 호환)

### 1.2 `TraderMeta`

`knowledge/{trader_id}/principles.md` 상단 metadata 섹션을 표현.

```python
@dataclass(frozen=True)
class TraderMeta:
    trader_id: str            # "livermore"
    display_name: str         # "Jesse Livermore"
    style: str                # "trend_following_speculator"
    default_persona: str      # "MODERATE"
    primary_sources: tuple[str, ...]
    principles: tuple[Principle, ...]
```

### 1.3 Loader 시그니처

```python
# src/autocoin_ai/traders.py
def load_trader(trader_id: str) -> TraderMeta:
    """knowledge/{trader_id}/principles.md 파싱.
    파일 없음 → ValueError("unknown trader_id: ...")
    """
```

```python
# src/autocoin_ai/rag/retriever.py
def retrieve_relevant(trader_id: str, query: str, k: int = 5) -> list[Principle]:
    """MVP: 키워드 매칭 (Principle.keywords ∩ query 토큰).
    매칭 0개 → 모든 원칙을 score=0으로 반환 (top-k는 단순히 처음 k개).
    Phase 후속: 임베딩 기반 vector retrieval로 교체.
    """
```

**MVP 키워드 매칭 알고리즘**:
1. `query`를 공백/구두점으로 토큰화 (한국어 + 영어)
2. 각 `Principle.keywords` 와 토큰 교집합 크기로 점수
3. 점수 내림차순 top-k. 동점이면 chunk_id 알파벳 순.
4. **모든 원칙이 점수 0이면** 처음 k개 그대로 반환 (RAG 미스 방지).

---

## §2. trader_id × persona 결정 행렬

### 2.1 우선순위 (intake 노드가 적용)

```
1. user_input.trader_id 명시 있음 → 그대로 사용
2. 발화 텍스트에 키워드 있음 → 그 trader_id
   - "워뇨띠" / "wonyotti" → "wonyotti"
   - "리버모어" / "livermore" → "livermore"
3. 디폴트: constants.DEFAULT_TRADER ("wonyotti")
```

### 2.2 persona 결정 매트릭스

```
1. user_input.persona 명시 → 그대로 (CONSERVATIVE/MODERATE/AGGRESSIVE)
2. 발화에 명시적 단어 있음 → 그 persona + persona_override_reason 기록
   - "공격적/aggressive/공격적으로" → AGGRESSIVE
   - "보수적/conservative/안전하게" → CONSERVATIVE
   - "중립적/moderate/적당히" → MODERATE
3. trader_meta.default_persona → 그 값
4. 최종 디폴트: "MODERATE"
```

### 2.3 불변

`trader_id`와 `inferred_persona`는 **intake 종료 후 immutable**. 이후 어떤 노드도 수정 금지.

---

## §3. State 계약 (immutable / patchable)

| 필드 | 정책 | 생성 노드 |
|---|---|---|
| `run_id` | immutable | (외부 입력) |
| `request_context` | immutable | (외부 입력) |
| `policy_context` | immutable after policy | policy |
| `trader_id` | immutable after intake | intake |
| `inferred_persona` | immutable after intake | intake |
| `persona_override_reason` | immutable after intake (optional) | intake |
| `trader_principles` | immutable after policy | policy (RAG retrieve) |
| `normalized_order_intent` | immutable after intake | intake |
| `decision_trace[stage]` | append-only per stage | 각 노드 |
| `verification_checks` | append-only | 모든 노드 |
| `llm_proposal` | patchable | strategy |
| `risk_assessment` | patchable | risk_gate (또는 risk_agent) |
| `risk_tool_calls` | append-only | risk_gate(MVP) / risk_agent(opt) |
| `evaluator_review` | patchable | evaluator |
| `lifecycle_status` | patchable | 마지막 결정 노드 |
| `hold_reason` | patchable | risk_gate / intake |
| `completion_payload` | patchable | (외부 입력 via complete()) |

**immutable 검증 책임**: `app.py:resume()`이 patch 시 immutable 필드를 덮어쓰면 `ValueError`.
MVP에서는 **resume 자체를 미지원** (§9 참조).

---

## §4. Intake 노드 계약

### 4.1 입력 분기 (회귀 호환 필수)

```
state["request_context"]["user_input"]:
  - "raw_text" 키 있음 → LLM 파싱 모드
  - "raw_text" 키 없음 → 기존 dict 모드 (회귀 보호)
```

**이유**: 기존 24개 테스트 + qa/ evidence JSON은 dict 입력. `raw_text` 모드는 새로 도입.

### 4.2 LLM 파싱 모드

```python
INTAKE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "symbol":   {"type": "STRING"},
        "side":     {"type": "STRING", "enum": ["BUY", "SELL"]},
        "type":     {"type": "STRING", "enum": ["MARKET", "LIMIT"]},
        "size_usd": {"type": "STRING", "description": "USDT 숫자 문자열. KRW 발화면 1 USD ≈ 1350 KRW로 환산"},
        "trader_id":              {"type": "STRING", "description": "발화 추론 결과. 미명시 시 빈 문자열"},
        "inferred_persona":       {"type": "STRING", "enum": ["CONSERVATIVE", "MODERATE", "AGGRESSIVE"]},
        "persona_override_reason": {"type": "STRING", "description": "발화에 명시 시 사유, 없으면 빈 문자열"},
        "ambiguity_score":        {"type": "NUMBER", "description": "0=명확, 1=모호. 0.5 초과면 HOLD"},
    },
    "required": ["symbol", "side", "type", "size_usd",
                 "trader_id", "inferred_persona", "persona_override_reason", "ambiguity_score"],
}
```

### 4.3 Dict 모드 (회귀)

`raw_text` 없으면 기존 user_input dict를 그대로 `normalized_order_intent`에 박음:
```python
normalized = {
    "symbol": str(user_input["symbol"]).upper(),
    "side":   str(user_input["side"]).upper(),
    "type":   str(user_input["type"]).upper(),
}
if "quoteOrderQty" in user_input: normalized["quoteOrderQty"] = str(...)
if "quantity" in user_input:      normalized["quantity"] = str(...)
```
- `trader_id = DEFAULT_TRADER` (`"wonyotti"`)
- `inferred_persona = "MODERATE"` (디폴트)

### 4.4 종료 분기

| 조건 | 결과 |
|---|---|
| `validate_request_context` 실패 (필수 필드 누락) | `lifecycle_status = FAILED` + `decision_trace.intake.reason_codes = ["INITIAL_REQUEST_CONTRACT_FAILED"]` |
| LLM 호출 자체 실패 (예외) | `lifecycle_status = FAILED` + reason `"INTAKE_LLM_ERROR"` |
| LLM 응답 schema 깨짐 (필수 필드 누락) | `lifecycle_status = FAILED` + reason `"INTAKE_SCHEMA_INVALID"` |
| `ambiguity_score > 0.5` | `lifecycle_status = HOLD` + `hold_reason = HOLD_INPUT_AMBIGUOUS` |
| Dict 모드 + 모든 필드 OK | `lifecycle_status = ""` (다음 노드 진행) + 모든 필드 set |
| LLM 모드 + ambiguity ≤ 0.5 | 동일 |

### 4.5 출력 (state 변형)

set 필드:
- `normalized_order_intent` (dict)
- `trader_id` (string)
- `inferred_persona` (string)
- `persona_override_reason` (optional string)
- `decision_trace["intake"]` (TraceEntry)
- `verification_checks` += `{name: "intake_parse_complete", stage: "intake", result: "pass"|"fail", evidence_refs: [...]}`

### 4.6 금지

- `request_context` 수정 금지 (immutable)
- `llm_proposal`, `risk_assessment` 등 다른 stage 필드 set 금지
- `policy_context.policy_refs` 임의 수정 금지 (policy 노드 책임)

---

## §5. Policy 노드 계약 (수정)

### 5.1 책임 (변경)

기존:
- `request_context` 필드 검증
- `normalized_order_intent` 정규화

변경 (intake에서 위 책임이 옮겨감):
- `policy_context.policy_refs` 박기 (기존)
- `policy_context.persona` = `state["inferred_persona"]` (신규)
- `policy_context.persona_bounds` = `PERSONA_PROFILES[persona]` (신규)
- **RAG retrieval**: `state["trader_principles"] = retrieve_relevant(trader_id, query, k=5)` (신규)
  - query 생성: `f"{intent.symbol} {intent.side} {persona}"` (간단 join)

### 5.2 종료 분기

| 조건 | 결과 |
|---|---|
| `state["lifecycle_status"] == FAILED` | 그대로 통과 (no-op) |
| 위 set 모두 성공 | `lifecycle_status` 변경 없음 (다음 노드 진행), trace에 `"POLICY_GROUNDED"` |

### 5.3 금지

- `normalized_order_intent` 수정 금지 (intake 결과 immutable)
- `trader_id`, `inferred_persona` 수정 금지
- LLM 호출 금지 (RAG retrieval은 결정론 키워드 매칭)

---

## §6. Strategy 노드 계약 (신규)

### 6.1 입력

- `state["trader_principles"]` (list of Principle dict)
- `state["normalized_order_intent"]`
- `state["policy_context"]["persona_bounds"]`

### 6.2 LLM 호출 schema

```python
STRATEGY_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "action":     {"type": "STRING", "enum": ["BUY", "SELL", "HOLD"]},
        "size_usd":   {"type": "STRING", "description": "USDT 숫자 문자열"},
        "conviction": {"type": "NUMBER", "description": "0~1"},
        "rationale":  {"type": "STRING", "description": "한국어 1~2 문장"},
        "matched_principle_titles": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
            "description": "참고한 trader_principles의 title 리스트 (1개 이상)",
        },
    },
    "required": ["action", "size_usd", "conviction", "rationale", "matched_principle_titles"],
}
```

### 6.3 종료 분기

| 조건 | 결과 |
|---|---|
| `state["lifecycle_status"]`가 FAILED/HOLD | 그대로 통과 |
| LLM 응답 OK | `state["llm_proposal"] = response` + trace |
| LLM 호출 실패 / schema 깨짐 | `lifecycle_status = FAILED` + reason `"STRATEGY_LLM_ERROR"` |

### 6.4 출력

- `state["llm_proposal"]` (dict, STRATEGY_SCHEMA 그대로)
- `state["decision_trace"]["strategy"]` = TraceEntry(reason_codes=[action, f"CONVICTION_{conviction:.2f}"], evidence_refs=matched_principle_titles, final_action=action, notes=rationale)
- `verification_checks` += `{name: "strategy_proposal_generated", stage: "strategy", result: "pass", evidence_refs: ["llm_proposal"]}`

### 6.5 금지

- `lifecycle_status` 직접 변경 금지 (FAILED 케이스 제외)
- `trader_principles` 수정 금지 (immutable)
- 도구 호출 금지 (risk_gate / risk_agent 책임)

---

## §7. Risk Gate 노드 계약 (신규, MVP의 진짜 두뇌)

### 7.1 입력

- `state["llm_proposal"]`
- `state["normalized_order_intent"]`
- `state["policy_context"]["persona_bounds"]`
- mock tools (직접 호출)

### 7.2 검증 순서 (결정론, 위→아래로 단락)

| # | 체크 | 실패 시 | 사용 도구 |
|---|---|---|---|
| 1 | `llm_proposal.action == "HOLD"` | `lifecycle_status = HOLD` + reason `HOLD_LOW_CONVICTION` | (없음) |
| 2 | `Decimal(conviction) < persona_bounds.min_conviction` | 동일 | (없음) |
| 3 | `Decimal(size_usd) > Decimal(persona_bounds.max_order_usd)` | `lifecycle_status = NO_ORDER` + reason 비움, trace `"SIZE_EXCEEDS_PERSONA"` | (없음) |
| 4 | `intent.symbol ∉ persona_bounds.allowed_symbols` | `NO_ORDER` + trace `"SYMBOL_NOT_ALLOWED"` | (없음) |
| 5 | `get_balance(quote_asset).free < size_usd` | `HOLD` + reason `HOLD_DATA_INSUFFICIENT`, trace `"INSUFFICIENT_BALANCE"` | `get_balance` |
| 6 | `get_volatility(symbol, 7).atr_pct > VOLATILITY_HIGH_THRESHOLD` (=0.08) | `HOLD` + reason `HOLD_RISK_AGENT_FLAGGED`, trace `"VOLATILITY_HIGH"` | `get_volatility` |
| 7 | (선택, persona가 conservative일 때) `get_concentration_risk(symbol, size_usd).after_pct > MAX_CONCENTRATION` (=0.20) | `HOLD` + reason `HOLD_RISK_AGENT_FLAGGED`, trace `"CONCENTRATION_HIGH"` | `get_concentration_risk` |
| 모두 통과 | `lifecycle_status = READY_FOR_BE`, trace `"ALL_CHECKS_PASSED"`, action = `PASS_ACTION` | - |

**상수**:
```python
VOLATILITY_HIGH_THRESHOLD = 0.08
MAX_CONCENTRATION = 0.20
```
`constants.py`에 추가.

### 7.3 도구 호출 기록

호출된 모든 도구는 `state["risk_tool_calls"]`에 append:
```python
{
    "step": int,             # 호출 순서 1부터
    "thought": "",           # MVP는 빈 문자열 (결정론), risk_agent 사용 시만 채움
    "tool": "get_balance",
    "args": {"asset": "USDT"},
    "result": {...},
}
```

### 7.4 출력

- `state["risk_assessment"]` = `{verdict, fail_reason, tools_called: list[str]}`
  - `verdict`: `"ALLOW"` / `"HOLD"` / `"NO_ORDER"`
  - `fail_reason`: 실패한 체크 이름 (#1~#7) 또는 `null`
  - `tools_called`: 호출한 도구 이름 list
- `state["lifecycle_status"]`
- `state["hold_reason"]` (HOLD일 때만)
- `state["decision_trace"]["risk"]` (TraceEntry)
- `state["risk_tool_calls"]` (append)
- `verification_checks` += `{name: "risk_gate_verdict", stage: "risk", result: "pass", evidence_refs: [...]}`

### 7.5 금지

- LLM 호출 금지 (결정론)
- `llm_proposal` 수정 금지
- `decision_trace.strategy` 수정 금지
- 어떤 단계든 `READY_FOR_BE`를 무조건 부여 금지 (검증 순서 7 통과 시에만)

---

## §8. Evaluator 노드 계약 (수정/축소)

### 8.1 책임 (변경)

기존: 근거 충분성(policy/risk pass) 카운트.
변경: **최종 사용자 리포트 생성 + trace/schema sanity check**.
faithfulness 별도 판정 / `HOLD_TRADER_DEVIATION` 생성 → MVP 미구현.

### 8.2 항상 실행

`risk_gate`가 `NO_ORDER` / `HOLD` / `READY_FOR_BE` 무엇이든 evaluator는 **항상 실행**해서 `user_message`를 생성한다.
예외: `lifecycle_status == FAILED` (intake/policy/strategy 단계 실패)면 evaluator 진입 자체를 graph 라우팅에서 차단 (§10).

### 8.3 입력

- `state["llm_proposal"]`
- `state["risk_assessment"]`
- `state["trader_principles"]` (요약 인용용)
- `state["decision_trace"]`
- `state["verification_checks"]`
- `state["lifecycle_status"]` (echo 대상)
- `state["hold_reason"]` (echo 대상)

### 8.4 LLM 호출 schema

```python
EVALUATOR_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "summary":      {"type": "STRING", "description": "한국어 1문장"},
        "user_message": {"type": "STRING", "description": "한국어 2~3문장. 결과/근거/다음 액션"},
        "reason_codes": {"type": "ARRAY", "items": {"type": "STRING"}},
        "schema_warnings": {"type": "ARRAY", "items": {"type": "STRING"}},
    },
    "required": ["summary", "user_message", "reason_codes", "schema_warnings"],
}
```

### 8.5 schema_warnings 점검 항목 (필수)

evaluator는 LLM 호출 전후로 다음 4개 sanity 체크 수행. 위반 발견 시 `schema_warnings`에 한 줄 추가:

1. `decision_trace`에 모든 stage가 채워졌는지 (run_summary 제외)
2. `verification_checks`에 stage="strategy" pass가 있는지 (lifecycle != FAILED일 때)
3. `risk_tool_calls`이 `risk_assessment.tools_called`와 일치하는지
4. `llm_proposal.matched_principle_titles`가 `trader_principles` 안에 실제 존재하는 title인지 (환각 차단)

### 8.6 출력

- `state["evaluator_review"]` = `EVALUATOR_SCHEMA` 응답 그대로
- `state["decision_trace"]["evaluator"]` = TraceEntry(reason_codes=[r for r in evaluator_review.reason_codes], evidence_refs=["evaluator_review"], final_action=lifecycle_status_echo)
- `state["decision_trace"]["run_summary"]` = TraceEntry(reason_codes=["RUN_COMPLETE"], evidence_refs=[...], final_action=lifecycle_status_echo)
- `verification_checks` += `{name: "evaluator_summary_complete", stage: "evaluator", result: "pass" or "fail", evidence_refs: [...]}`

### 8.7 금지 (강제)

- `lifecycle_status` 변경 금지 (echo만)
- `llm_proposal.action` 수정 금지
- `risk_assessment.verdict` 수정 금지
- `HOLD_TRADER_DEVIATION` 등 신규 hold_reason 생성 금지
- 인용 강제 X (matched_principle_titles만 echo)

### 8.8 LLM 호출 실패 시 폴백

`gemini_generate` 예외 → 결정론 폴백:
```python
fallback = {
    "summary": f"{action} {symbol} {size_usd} USDT 평가 완료. 결과: {lifecycle_status}",
    "user_message": f"{verdict}로 판단되었습니다. 사유: {fail_reason or 'PASSED'}",
    "reason_codes": ["EVALUATOR_LLM_FALLBACK"],
    "schema_warnings": ["LLM call failed; deterministic summary used"],
}
```

이 폴백은 `lifecycle_status`를 FAILED로 만들지 않음 (사용자 설명은 항상 생성).

---

## §9. Resume 정책

### 9.1 MVP 정책

**MVP에서 resume은 미지원.**

이유:
- 새 흐름의 immutable/patchable 검증 추가 구현 시간 부족
- 데모 시나리오는 fresh start 한 번이면 충분
- 기존 `app.py:resume()` 코드는 그대로 두되 새 그래프 흐름에서는 호출 안 함

### 9.2 동작

`app.py:resume(run_id, ...)` 호출 시:
- 기존 lifecycle (`HOLD`)이 새 그래프에서 발생한 run이면 → `ValueError("resume not supported for agentic runs in MVP")`
- 기존 dict-mode run이면 (회귀 호환) → 기존 동작 유지

### 9.3 후속 (Phase 2)

- `decision_trace_history` 활용 + immutable 필드 보호 추가
- `HOLD_INPUT_AMBIGUOUS` resume → intake만 재실행
- `HOLD_LOW_CONVICTION` resume → strategy만 재실행

---

## §10. Graph 라우팅

### 10.1 새 그래프 (`build_order_graph`)

```python
graph.set_entry_point("intake")
graph.add_node("intake", intake_node)
graph.add_node("policy", policy_node)
graph.add_node("strategy", strategy_node)
graph.add_node("risk_gate", risk_gate_node)
graph.add_node("evaluator", evaluator_node)

graph.add_conditional_edges("intake",   route_after_intake)
graph.add_conditional_edges("policy",   route_after_policy)
graph.add_conditional_edges("strategy", route_after_strategy)
graph.add_conditional_edges("risk_gate", route_after_risk_gate)
graph.add_edge("evaluator", END)
```

### 10.2 라우팅 함수 4개

```python
def route_after_intake(state):
    if state["lifecycle_status"] == LIFECYCLE_FAILED: return END
    if state["lifecycle_status"] == LIFECYCLE_HOLD:   return "evaluator"  # HOLD도 user_message 생성
    return "policy"

def route_after_policy(state):
    if state["lifecycle_status"] == LIFECYCLE_FAILED: return END
    return "strategy"

def route_after_strategy(state):
    if state["lifecycle_status"] == LIFECYCLE_FAILED: return END
    return "risk_gate"

def route_after_risk_gate(state):
    # NO_ORDER / HOLD / READY_FOR_BE 모두 evaluator 거침
    return "evaluator"
```

**핵심 규칙**:
- `FAILED`는 즉시 END (graph stage가 깨졌으므로 evaluator도 무의미)
- `HOLD`/`NO_ORDER`/`READY_FOR_BE`는 evaluator 거쳐 user_message 생성

### 10.3 Optional risk_agent 흐름 (Phase 3c)

```python
# strategy → risk_agent → risk_gate → evaluator
graph.add_node("risk_agent", risk_agent_node)
graph.add_edge("strategy",   "risk_agent")    # strategy 다음 risk_agent
graph.add_edge("risk_agent", "risk_gate")     # risk_agent 다음 risk_gate (그대로)
```

risk_agent를 끼워도 risk_gate가 항상 마지막 결정 노드.

### 10.4 Completion graph (변경 없음)

`__start__ → execution → __end__` 그대로.
BE의 `complete()`이 호출하는 별도 그래프이므로 새 흐름과 독립.

---

## §11. SDK 시그니처 (PoC 검증 완료)

### 11.1 Structured output (intake / strategy / evaluator)

```python
def gemini_generate(prompt: str, response_schema: dict,
                     system_instruction: str = "") -> dict:
    resp = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction or None,
            response_mime_type="application/json",
            response_schema=response_schema,
            temperature=0,
        ),
    )
    return resp.parsed  # dict
```

### 11.2 Function calling (Optional risk_agent)

```python
@dataclass
class StepResult:
    is_final: bool
    function_calls: list
    text: str
    candidate_content: object

def gemini_step_with_tools(contents: list, tools: list,
                            system_instruction: str = "") -> StepResult:
    resp = client.models.generate_content(...)
    candidate = resp.candidates[0]
    parts = candidate.content.parts or []
    fcs = [p.function_call for p in parts if getattr(p, "function_call", None)]
    text = "".join(p.text for p in parts if getattr(p, "text", None))
    return StepResult(is_final=not fcs, function_calls=fcs, text=text,
                      candidate_content=candidate.content)
```

### 11.3 환율 정책 (intake 프롬프트 system_instruction에 박기)

```
size_usd는 항상 USDT 기준 숫자 문자열.
- "5만원"/"50000원"/"50,000 KRW" → 1 USD ≈ 1350 KRW로 환산해 USDT
- "$50"/"50 USDT"/"50 달러" → 그대로
- 단위 명시 없음 → KRW로 가정 후 환산
```

### 11.4 Risk Agent 종료 후 structured output 1회 (Optional, Phase 3c)

ReAct 루프 자연 종료 후 LLM이 짧은 텍스트만 반환할 수 있음. structured output으로 한 번 더 호출:
```python
final = gemini_generate(
    prompt=build_summary(tool_calls_log),
    response_schema=RISK_ASSESSMENT_SCHEMA,  # §7.4와 동일 형식
)
state["risk_assessment"] = final
```

---

## §12. Tool 시스템

### 12.1 Tool 등록 (`tools/registry.py`)

```python
@dataclass
class Tool:
    name: str
    description: str        # LLM이 직접 읽음 (function calling용 + 내부 문서)
    schema: dict            # JSON schema (parameters)
    fn: Callable[..., dict]

REGISTRY: dict[str, Tool] = {}

def tool(schema: dict):
    """데코레이터. 함수 등록."""

def dispatch(name: str, args: dict, run_id: str | None = None) -> dict:
    """unknown tool → {"error": "unknown tool: X"} 반환."""
```

### 12.2 MVP 도구 5개

| 도구 | 카테고리 | 데이터 출처 | 사용처 |
|---|---|---|---|
| `get_balance(asset: str)` | 계정 | `_mock_data.MOCK_BALANCE` | risk_gate (#5) |
| `check_persona_bounds(action, symbol, size_usd)` | 정책 | `personas.PERSONA_PROFILES` (결정론) | risk_gate / risk_agent |
| `get_volatility(symbol, days)` | 시장 | `_mock_data.MOCK_VOLATILITY` | risk_gate (#6) |
| `get_concentration_risk(symbol, proposed_size_usd)` | 계정 | `_mock_data.MOCK_CONCENTRATION` | risk_gate (#7) |
| `check_daily_loss_limit()` | 정책 | (Phase 3c, mock 0) | Optional risk_agent |

### 12.3 도구 description 작성 원칙

LLM이 직접 읽으므로:
- 한국어 1~2 문장
- 반환 schema 한 줄 명시
- "언제 부르는지" 1줄

예:
```python
@tool({"asset": "string"})
def get_balance(asset: str) -> dict:
    """사용자의 보유 자산 잔고를 조회합니다.
    반환: {"asset": str, "free": str, "locked": str, "total": str}.
    매수 가능 자금 확인이 필요할 때 호출하세요."""
    ...
```

---

## §13. Schema 변경 요약 (`constants.py` / `models.py`)

### 13.1 `constants.py` 추가

```python
TRACE_STAGES = ("intake", "policy", "strategy", "risk", "evaluator", "execution", "run_summary")
CHECK_STAGES = ("intake", "policy", "strategy", "risk", "evaluator", "execution", "be_revalidation")

HOLD_INPUT_AMBIGUOUS    = "HOLD_INPUT_AMBIGUOUS"
HOLD_LOW_CONVICTION     = "HOLD_LOW_CONVICTION"
HOLD_RISK_AGENT_FLAGGED = "HOLD_RISK_AGENT_FLAGGED"
HOLD_DATA_INSUFFICIENT  = "HOLD_DATA_INSUFFICIENT"   # 기존 유지

PERSONA_CONSERVATIVE = "CONSERVATIVE"
PERSONA_MODERATE     = "MODERATE"
PERSONA_AGGRESSIVE   = "AGGRESSIVE"

DEFAULT_TRADER = "wonyotti"

VOLATILITY_HIGH_THRESHOLD = 0.08
MAX_CONCENTRATION = 0.20
MAX_TOOL_CALLS = 4
```

### 13.2 `models.py:AgentState` 신규 필드

```python
trader_id: str
inferred_persona: str
persona_override_reason: NotRequired[str]
trader_principles: List[JsonDict]      # list of Principle dict
llm_proposal: JsonDict
risk_assessment: JsonDict
risk_tool_calls: List[JsonDict]
evaluator_review: JsonDict
```

### 13.3 `validators.py:assert_trace_container` 소프트화

```python
def assert_trace_container(trace, prefix="decision_trace"):
    REQUIRED_STAGES = ("policy", "risk", "evaluator", "execution", "run_summary")
    for stage in REQUIRED_STAGES:
        if stage not in trace:
            raise AssertionError(f"missing {prefix} stage: {stage}")
        # ... 기존 entry 검증
```

→ `intake`, `strategy`는 옵셔널. 기존 24개 테스트 회귀 안 깨짐.

---

## §14. 단방향 의존성 그래프

```
constants.py / personas.py / traders.py
    ↓
models.py (TypedDict)
    ↓
validators.py (state 검증)
    ↓
prompts/*.py (텍스트만)
    ↓
llm.py (Gemini SDK 래퍼)
    ↓
rag/retriever.py (Principle 사용)
    ↓
tools/*.py (registry + 5개 도구)
    ↓
nodes/intake.py
    ↓
nodes/policy.py (수정)
    ↓
nodes/strategy.py
    ↓
nodes/risk_gate.py
    ↓
nodes/evaluator.py (수정)
    ↓
graph.py (wiring + routing)
    ↓
app.py (resume 보호)
```

각 노드 구현 시 위 의존성 위쪽만 import. 아래로의 의존성은 금지.

---

## §15. 변경 사항 합치 (Decision Log은 MASTER_PLAN.md 13장 참조)

이 문서가 변경되면:
1. 영향 받는 노드의 단위 테스트 fixture 갱신 (`tests/fixtures/`)
2. PHASES.md의 acceptance 항목 갱신
3. MASTER_PLAN.md Decision Log에 한 줄 기록
