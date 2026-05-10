# autocoin-ai · Agentic Upgrade — 마스터 플랜

> **상태**: 캐노니컬 / 작업 시작 가능
> **작성일**: 2026-05-10
> **모드**: 제출 모드 (코드 + 영상 녹화. 라이브 데모 없음)
> **데드라인**: 2026-05-11 11:00
> **이 문서가 단일 소스다.** 이전 문서(`history/AGENTIC_UPGRADE.md`, `history/AGENTIC_UPGRADE_REVIEW.md`)는 참고용 히스토리.

---

## 0. 한 줄 정의

> **"챗봇으로 자연어 받아 → 워뇨띠 매매 원칙(RAG)을 grounding으로 LLM이 매매 판단 → Risk Gate가 안전성 hard check → Evaluator가 최종 리포트와 trace를 정리 → 모든 판단이 trace에 기록"**

기존 결정론 LangGraph 골격(`policy → risk → evaluator → execution`)은 **계약을 깨지 않고 확장**한다. `intake`/`strategy`/`risk_gate`를 우선 추가하고, `risk_agent`는 시간이 남으면 붙이는 확장 기능으로 둔다. `evaluator`는 엄격한 faithfulness 판정자가 아니라 **최종 설명 생성 + trace/schema sanity check** 역할로 축소한다.

---

## 1. 확정 사항 모음

| # | 항목 | 결정 |
|---|---|---|
| 1 | NL 파싱 위치 | **AI 안** (`intake` 노드 신설) |
| 2 | Persona 결정 | **하이브리드** — 계정 디폴트 + 발화 override |
| 3 | 모호한 입력 처리 | MVP에선 즉시 **HOLD_INPUT_AMBIGUOUS** |
| 4 | 도구 권한 차등 | 도구함 통일 + persona별 `required_tools` |
| 5 | Trace 레벨 | **Lv2** — tool 이름·인자·결과 + 호출 직전 thought |
| 6 | 거래소 | Binance Spot Testnet (변경 없음) |
| 7 | RAG 트레이더 | MVP 기본은 **워뇨띠**, 보조 mock dataset으로 **Jesse Livermore** 추가 |
| 8 | RAG 방식 | MVP는 **md 키워드 매칭**, v2는 **embedding vector retrieval** |
| 9 | BE 도구 endpoint | **mock fixture로 대체** (`tools/_mock_data.py`) |
| 10 | UI | **CLI 데모 + 영상 녹화** (FE는 계약/표시 가이드만 갱신) |
| 11 | LLM | **Gemini 2.5 Pro** (`gemini-2.5-pro`) |
| 12 | Submission mode | 코드 품질 + 테스트 + README 우선 |
| 13 | Evaluator 역할 | **최종 리포트 + trace/schema sanity check** (faithfulness strict mode는 후속) |
| 14 | MVP 우선순위 | `intake → RAG → strategy → risk_gate → evaluator summary → e2e` 먼저 완성 |
| 15 | FE/BE 전달 | FE는 자연어 입력/AI 요약 표시, BE는 AI proposal 재검증 + completion payload 유지 |
| 16 | 입력 호환 | `user_input.text/raw_text`는 LLM intake, 기존 구조화 dict는 그대로 통과 |
| 17 | Resume 정책 | MVP는 그래프 처음부터 재실행하되 immutable 산출물은 cache hit로 LLM/RAG 재호출 스킵 |

---

## 2. 새 흐름

### Before (현재)
```
__start__ → policy → risk → evaluator → __end__
```

### After (Agentic)
```
__start__
  → intake          [LLM] 자연어 → 구조화 + persona 추론
  → policy          [코드+RAG] 검증 + 워뇨띠 원칙 retrieval
  → strategy        [LLM] 워뇨띠 원칙 grounding으로 매매 판단
  → risk_gate       [코드] hard limit + mock tools 기반 안전성 검증
  → evaluator       [LLM/코드] 최종 리포트 생성 + trace/schema sanity check
  → __end__
```

### Optional 확장 흐름
```
strategy
  → risk_agent      [LLM+Tools] 도구 ReAct 루프
  → risk_gate       [코드] hard limit + 필수 도구 사후 검증
```
`risk_agent`는 데모 완성 후 붙인다. MVP에서는 `risk_gate`가 mock tool을 직접 호출하거나 deterministic helper를 통해 잔고/변동성/persona bound를 검증한다.

### Completion graph (변경 없음)
```
__start__ → execution → __end__
```
BE의 `execution_result` / `be_rejection_evidence` 해석. 기존 그대로 유지.

---

## 3. 변경 파일 매트릭스

### 신규
```
src/autocoin_ai/
├── nodes/
│   ├── intake.py              🆕 자연어 → 구조화 (LLM)
│   ├── strategy.py            🆕 Trader LLM (워뇨띠 원칙 주입)
│   ├── risk_agent.py          🆕 optional ReAct 도구 루프
│   └── risk_gate.py           🆕 결정론 사후 검증
├── tools/                     🆕
│   ├── __init__.py
│   ├── _mock_data.py
│   ├── registry.py            ← @tool 데코레이터 + dispatch
│   ├── account_tools.py
│   ├── market_tools.py
│   └── policy_tools.py
├── prompts/                   🆕
│   ├── intake_prompt.py
│   ├── strategy_prompt.py
│   ├── risk_agent_prompt.py   ← optional
│   └── evaluator_prompt.py
├── rag/                       🆕
│   ├── __init__.py
│   ├── retriever.py           ← MVP: md 파싱 + 키워드 매칭
│   └── embedder.py            ← v2: embedding/vector retrieval 후속 자리
└── personas.py                🆕 PERSONA_PROFILES + 워뇨띠 메타

knowledge/                     🆕
├── wonyotti/
│   └── principles.md          ← 팀원 A 산출물 (mock 포함)
└── livermore/
    └── principles.md          ← 보조 mock dataset (공개 원칙 요약)

tests/
├── test_intake.py             🆕
├── test_strategy.py           🆕
├── test_risk_agent.py         🆕 optional
├── test_risk_gate.py          🆕
├── test_evaluator_summary.py  🆕
└── test_e2e_wonyotti.py       🆕

examples/
├── wonyotti_buy.json          🆕 (Happy path)
├── wonyotti_hold.json         🆕 (HOLD 시나리오)
├── wonyotti_low_conviction.json 🆕 (HOLD_LOW_CONVICTION)
└── DISCLAIMER.md              🆕

poc/                           ✅ 이미 있음 (검증 완료)
└── ...
```

### 수정
```
src/autocoin_ai/
├── constants.py               TRACE_STAGES/CHECK_STAGES 확장 + HOLD_* 추가
├── models.py                  AgentState에 6개 필드 추가
├── validators.py              assert_trace_container 소프트화 (P0-1)
├── llm.py                     실제 Gemini 호출 채우기 (PoC 시그니처 적용)
├── nodes/policy.py            persona_bounds + RAG 호출 추가
├── nodes/evaluator.py         최종 리포트 생성 + trace/schema sanity check
├── graph.py                   새 노드 wire + 라우팅 함수 추가
└── app.py                     resume 시 immutable 필드 보호 (P0-2)
```

---

## 4. State 계약 (immutable / patchable)

advisor P0-2 반영. `app.py:resume()`에서 명시적으로 보호.

| 필드 | 정책 | 비고 |
|---|---|---|
| `run_id` | **immutable** | 기존 |
| `request_context` | **immutable** | 기존 |
| `policy_context` | **immutable** | 기존 |
| `inferred_persona` | **immutable** | 🆕 (resume 시 persona 변경 불가) |
| `trader_id` | **immutable** | 🆕 (워뇨띠 → 다른 트레이더 swap 금지) |
| `trader_principles` | **immutable** | 🆕 (RAG 결과는 grounding) |
| `decision_trace` (이전 단계 분) | **immutable** | 기존 |
| `verification_checks` (이전 분) | **immutable** | 기존 |
| `llm_proposal` | patchable | 🆕 (재실행 시 재생성) |
| `risk_assessment` | patchable | 🆕 |
| `risk_tool_calls` | **append-only** | 🆕 risk_gate(MVP) + risk_agent(optional) tool 호출 기록. risk_agent에서만 thought 채움 |
| `evaluator_review` | patchable | 🆕 (최종 리포트/형식 검증 결과) |
| `completion_payload` | patchable | 기존 |

### `HOLD_TRADER_DEVIATION` 정책
MVP에서는 `HOLD_TRADER_DEVIATION`을 구현하지 않는다. 워뇨띠 원칙과 충돌하는 판단은 `strategy` 단계에서 `conviction`을 낮추거나 `HOLD_LOW_CONVICTION`으로 처리한다.

엄격한 faithfulness 판정, 인용 chunk 강제, deviation override resume은 Phase 후속으로 둔다.

---

## 4.1 Evaluator MVP 계약

Evaluator는 MVP에서 주문을 새로 판단하지 않는다. 앞 단계 결과를 사용자/데모용으로 정리하고, trace shape이 깨지지 않았는지만 확인한다.

MVP에서는 evaluator가 LLM을 사용해 자연어 `summary`와 `user_message`를 생성한다. LLM 호출 실패 또는 시간 부족 시에는 `decision_trace` + `risk_assessment`를 단순 직렬화한 코드 기반 요약으로 대체한다.

### 입력
- `llm_proposal`: strategy의 매매 제안
- `risk_assessment`: risk_gate의 결정론 검증 결과
- `trader_principles`: strategy가 참고한 워뇨띠 원칙
- `decision_trace`, `verification_checks`

### 출력 예시
`final_action`은 risk_gate가 결정한 `lifecycle_status`를 그대로 echo한다. Evaluator는 lifecycle을 새로 만들지 않는다.

```json
{
  "summary": "BTCUSDT 매수 제안입니다.",
  "user_message": "워뇨띠 원칙 중 추세 확인과 거래량 확인을 근거로 판단했고, risk_gate 검증을 통과했습니다.",
  "final_action": "READY_FOR_BE",
  "reason_codes": ["EVIDENCE_SUMMARIZED", "RISK_GATE_PASSED"],
  "schema_warnings": []
}
```

### 금지
- 워뇨띠다움 별도 판정으로 `HOLD_TRADER_DEVIATION` 생성 금지
- strategy의 `action`을 임의로 뒤집기 금지
- 인용 `chunk_id` 강제 금지 (원칙 제목 수준이면 충분)

---

## 4.2 Risk Gate MVP 계약

Risk Gate는 MVP의 deterministic safety brain이다. LLM을 호출하지 않고, strategy proposal과 persona bounds, mock tools 결과만으로 lifecycle을 결정한다.

### 입력
- `llm_proposal`: strategy 결과
- `policy_context.persona_bounds`: persona별 한도/허용 심볼/min conviction
- mock tools: `get_balance`, `check_persona_bounds`, `get_volatility`

### 검증 순서
아래 순서대로 결정론적으로 평가하고, 첫 실패에서 멈춘다.

1. `llm_proposal.action == "HOLD"` → `NO_ORDER`
2. `llm_proposal.conviction < persona_bounds.min_conviction` → `HOLD_LOW_CONVICTION`
3. `llm_proposal.size_usd > persona_bounds.max_order_usd` → `NO_ORDER`
4. `llm_proposal.symbol not in persona_bounds.allowed_symbols` → `NO_ORDER`
5. `get_balance().free < llm_proposal.size_usd` → `HOLD_DATA_INSUFFICIENT`
6. `get_volatility().atr_pct > RISK_VOLATILITY_ATR_THRESHOLD` → `HOLD_RISK_AGENT_FLAGGED`
7. 모두 통과 → `READY_FOR_BE`

### 출력 / state 변형
```json
{
  "risk_assessment": {
    "verdict": "ALLOW",
    "lifecycle_status": "READY_FOR_BE",
    "fail_reason": null,
    "tools_called": ["check_persona_bounds", "get_balance", "get_volatility"],
    "reasoning": "Persona bounds, balance, and volatility checks passed."
  },
  "risk_tool_calls": [
    {
      "stage": "risk",
      "tool": "get_balance",
      "args": {"asset": "USDT"},
      "result": {"free": "5000.0"},
      "thought": null
    }
  ]
}
```

`risk_tool_calls`는 MVP에서도 risk_gate가 호출한 mock tool들을 기록한다. optional `risk_agent`가 붙는 경우에만 호출 직전 thought를 채운다.

### 금지
- LLM 호출 금지
- `decision_trace.strategy.final_action` 수정 금지
- `conviction` 임의 가중치 적용 금지
- evaluator 대신 사용자 메시지 생성 금지

---

## 4.3 Strategy MVP 출력 계약

Strategy는 evaluator가 근거를 설명할 수 있도록 매칭된 원칙 제목을 반드시 포함한다.

```json
{
  "action": "BUY",
  "symbol": "BTCUSDT",
  "side": "BUY",
  "type": "MARKET",
  "size_usd": "37.04",
  "conviction": 0.72,
  "rationale": "추세와 거래량 확인 원칙에 부합해 소액 진입을 제안합니다.",
  "matched_principle_titles": ["추세 확인 후 진입", "거래량 동반 확인"]
}
```

`matched_principle_titles`는 `trader_principles[*].title`에서 가져온다. 새 원칙명을 LLM이 지어내면 안 된다.

---

## 4.4 Intake 입력/실패 계약

Intake는 자연어 입력과 기존 구조화 입력을 모두 받아야 한다. 기존 테스트와 examples가 구조화 dict를 쓰므로, 호환 분기를 명시적으로 둔다.

### 입력 분기
1. `user_input.text` 또는 `user_input.raw_text`가 있으면 LLM intake를 실행한다.
2. `text/raw_text`가 없고 `symbol`, `side`, `type`, `quoteOrderQty`가 있으면 기존 구조화 dict로 보고 LLM 호출 없이 정규화만 한다.
3. 둘 다 없거나 필수 필드가 부족하면 `FAILED`가 아니라 `HOLD_INPUT_AMBIGUOUS`로 둔다. 사용자가 보완할 수 있는 입력 문제이기 때문이다.

### 출력
```json
{
  "normalized_order": {
    "symbol": "BTCUSDT",
    "side": "BUY",
    "type": "MARKET",
    "quoteOrderQty": "37.04"
  },
  "inferred_persona": "AGGRESSIVE",
  "ambiguity_score": 0.1,
  "persona_override_reason": "사용자가 공격적으로 매수하라고 표현함"
}
```

### 종료 조건
- `ambiguity_score > 0.5` → `HOLD_INPUT_AMBIGUOUS`
- LLM 호출 실패, schema mismatch, JSON parse 실패, 필수 normalized field 결손 → `FAILED`
- 기존 구조화 dict가 유효하면 `ambiguity_score = 0`으로 간주하고 다음 단계로 진행

### Trace
`intake`가 호출되면 `decision_trace.intake`와 `verification_checks[stage=intake]`를 반드시 남긴다. 기존 구조화 dict fast path도 trace를 남긴다.

---

## 4.5 Graph 라우팅 계약

MVP 그래프는 대부분 linear지만, 실패/보류/종료 상태를 명확히 라우팅한다.

| 함수 | 조건 | 다음 |
|---|---|---|
| `route_after_intake` | `FAILED`, `HOLD_INPUT_AMBIGUOUS` | `evaluator` |
| `route_after_intake` | 정상 | `policy` |
| `route_after_policy` | `FAILED`, `HOLD`, `NO_ORDER` | `evaluator` |
| `route_after_policy` | 정상 | `strategy` |
| `route_after_strategy` | `FAILED` | `evaluator` |
| `route_after_strategy` | 정상 | `risk_gate` |
| `route_after_risk_gate` | 모든 결과 | `evaluator` |
| `route_after_evaluator` | 모든 결과 | `__end__` |

Evaluator는 lifecycle과 무관하게 항상 실행한다. `FAILED`, `HOLD`, `NO_ORDER`, `READY_FOR_BE` 모두 사용자에게 설명 가능한 `evaluator_review.user_message`를 만든 뒤 종료한다.

---

## 4.6 Resume 흐름

MVP resume은 별도 entry point를 만들지 않고 그래프 처음부터 재실행한다. 대신 immutable 산출물이 이미 있으면 해당 노드는 cache hit로 처리하고 LLM/RAG 호출을 스킵한다.

### Cache hit 규칙
- `intake`: `normalized_order`, `inferred_persona`, `trader_id`가 있으면 LLM intake 스킵
- `policy`: `policy_context`, `trader_principles`, `persona_bounds`가 있으면 RAG retrieval 스킵
- `strategy`: `llm_proposal`이 있고 resume patch가 strategy 입력을 바꾸지 않았으면 LLM strategy 스킵
- `risk_gate`: patchable approval/input이 바뀌었으면 재실행
- `evaluator`: 항상 재실행해서 최신 사용자 메시지 생성

### 불변성
`run_id`, 최초 `request_context`, `policy_context`, `inferred_persona`, `trader_id`, `trader_principles`, 이전 `decision_trace`, 이전 `verification_checks`는 덮어쓰지 않는다. 재실행으로 새 trace가 필요하면 append만 한다.

### 후속
v2에서는 HOLD 지점부터 재개하는 resume entry point를 따로 둔다. MVP에서는 구현 시간을 줄이기 위해 cache hit 기반 전체 재실행을 선택한다.

---

## 4.7 FE/BE 전달사항

이번 변경은 AI 레이어가 자연어 이해와 매매 판단을 더 많이 맡는 방향이다. FE/BE는 새 비즈니스 판단을 직접 구현하기보다, AI가 만든 상태와 trace를 안전하게 주고받고 표시하는 역할로 맞춘다.

### FE 변경 가이드
- 입력은 기존 구조화 주문 form만 고집하지 말고 `user_input.raw_text`를 받을 수 있게 둔다.
- FE가 persona/trader를 직접 판단하지 않는다. 계정 기본값만 보내고, 발화 override는 AI `intake`가 판단한다.
- 화면에는 `evaluator_review.summary`, `evaluator_review.user_message`, `decision_trace`, `verification_checks`, `hold_reason`을 표시한다.
- `READY_FOR_BE`는 "주문 성공"이 아니라 "BE 재검증 대기/진행"으로 표현한다.
- `PASS`는 내부 gate 통과 의미이므로 사용자에게 최종 승인처럼 보여주지 않는다.
- 데모에서는 CLI가 1차 UI이므로 FE 변경은 계약 반영 수준으로 충분하다.

### BE 변경 가이드
- BE는 AI의 `READY_FOR_BE` proposal을 그대로 실행하지 않고 deterministic revalidation을 유지한다.
- 재검증 항목은 최소 `symbol allowlist`, `side/type 허용`, `quoteOrderQty/minNotional`, `persona max_order_usd`, 잔고, 일일 손실 한도다.
- BE가 막으면 `be_rejection_evidence.reason_codes`를 채우고 최종 상태를 `BE_REJECTED`로 만든다.
- BE가 실행하면 `execution_result`를 채우고 completion graph로 AI에 돌려준다.
- BE도 AI/LLM을 써도 되지만, **설명 생성/로그 요약/운영자 메시지 초안**까지만 허용한다. 주문 허용/차단의 최종 판단은 결정론 검증이 맡는다.
- mock 단계에서는 `tools/_mock_data.py`가 BE tool endpoint 역할을 대체한다. 실제 BE 연동 시 같은 shape로 endpoint를 교체하면 된다.

### 검증 계약
| 구간 | 담당 | 검증 성격 |
|---|---|---|
| `intake` | AI | 자연어 → 구조화, 모호성 판단 |
| `strategy` | AI | 워뇨띠 원칙 기반 제안, conviction 산출 |
| `risk_gate` | AI 코드 | persona 한도/잔고/변동성 등 deterministic pre-check |
| `evaluator` | AI/코드 | 사용자 설명 + trace/schema sanity check |
| `be_revalidation` | BE 코드 | 실제 실행 전 최종 deterministic revalidation |
| `execution` | BE | Binance Testnet 제출/결과 검증 |

---

## 5. SDK 시그니처 (PoC 검증 완료)

### 5.1 structured output (intake / strategy / evaluator summary / risk_assessment 최종)
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
    return resp.parsed  # dict 바로 반환됨 ✓
```

**PoC 결과**:
- `resp.parsed`가 dict로 즉시 반환됨
- "공격적으로" → `inferred_persona: "AGGRESSIVE"` 정확 매핑
- "비트코인 좀 사봐" → `ambiguity_score: 0.8` 모호 인지
- ⚠️ **단위 환산 일관성 문제**: "5만원" → `"37.04"` (USD 변환), "10만원" → `"100000"` (KRW 그대로)
  → intake 프롬프트에 환율 정책 명시 필요: **항상 USDT 숫자 문자열, KRW면 1 USD ≈ 1350 KRW로 환산**

### 5.2 function calling (optional risk_agent ReAct 루프)
```python
@dataclass
class StepResult:
    is_final: bool
    function_calls: list      # part.function_call 리스트
    text: str                 # 누적 텍스트
    candidate_content: object # 다음 turn에 그대로 append

def gemini_step_with_tools(contents: list, tools: list,
                             system_instruction: str = "") -> StepResult:
    resp = client.models.generate_content(
        model=MODEL, contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction or None,
            tools=tools, temperature=0,
        ),
    )
    candidate = resp.candidates[0]
    parts = candidate.content.parts or []
    fcs = [p.function_call for p in parts if getattr(p, "function_call", None)]
    text = "".join(p.text for p in parts if getattr(p, "text", None))
    return StepResult(
        is_final=not fcs,
        function_calls=fcs,
        text=text,
        candidate_content=candidate.content,
    )
```

**PoC 결과**:
- `Tool(function_declarations=[FunctionDeclaration(...)])` 정상
- ReAct 자연 종료: 도구 호출 없는 텍스트 응답 → `is_final=True`
- Turn 3에서 모델이 `"ALLOW"` 한 단어로 답 → **별도 처리 필요**

### 5.3 Optional Risk Agent의 최종 검증 마무리 (PoC 결과 반영)
ReAct 루프가 자연 종료되면 LLM이 `"ALLOW"` 같은 짧은 텍스트만 줄 수 있음. 우리는 `{verdict, score, concerns, missed_risks, reasoning}` 구조가 필요.

**해결**: ReAct 종료 후 **structured output 1회 추가 호출**.

```python
# risk_agent_node 마지막 부분
loop_summary = build_summary(tool_calls_log)
final_assessment = gemini_generate(
    prompt=f"다음 도구 조사 결과로 risk_assessment를 JSON으로 만들어라.\n{loop_summary}",
    response_schema=RISK_ASSESSMENT_SCHEMA,
)
state["risk_assessment"] = final_assessment
```

---

## 6. Mock 가정 (시간 절약)

### 6.1 `knowledge/wonyotti/principles.md` (팀원 A 산출 / 없으면 mock)
```markdown
# 워뇨띠 매매 원칙

## 추세 확인 후 진입
추세가 명확히 잡히지 않으면 절대 들어가지 않는다.

## 손절 -5% 엄수
손실 한도 미리 정하고 칼같이 자른다.

## 분할 매수
한 번에 다 사지 않고 3~5회로 나눈다.

## 변동성 폭발 회피
변동성이 평소 2배 이상이면 관망.

## 거래량 동반 확인
가격 움직임이 거래량으로 뒷받침되어야 신뢰.
```

### 6.2 `tools/_mock_data.py` (BE 도구 대체)
```python
MOCK_BALANCE = {
    "USDT": {"free": "5000.0", "locked": "0", "total": "5000.0"},
    "BTC":  {"free": "0.05",   "locked": "0", "total": "0.05"},
}

MOCK_VOLATILITY = {
    "BTCUSDT": {"atr_pct": 0.045, "stdev_pct": 0.038, "window_days": 7},
    "ETHUSDT": {"atr_pct": 0.061, "stdev_pct": 0.054, "window_days": 7},
}

MOCK_CONCENTRATION = {
    ("BTCUSDT", "50"):  {"current_pct": 0.08, "after_pct": 0.09},
    ("BTCUSDT", "200"): {"current_pct": 0.08, "after_pct": 0.12},
}
```

### 6.3 Persona Profile (`personas.py`)
```python
PERSONA_PROFILES = {
    "CONSERVATIVE": {
        "max_order_usd": "100",
        "allowed_symbols": ["BTCUSDT", "ETHUSDT"],
        "min_conviction": 0.85,
        "required_tools": ["get_balance", "check_persona_bounds",
                           "get_volatility", "get_concentration_risk"],
    },
    "MODERATE": {
        "max_order_usd": "500",
        "allowed_symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        "min_conviction": 0.65,
        "required_tools": ["get_balance", "check_persona_bounds", "get_volatility"],
    },
    "AGGRESSIVE": {
        "max_order_usd": "2000",
        "allowed_symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"],
        "min_conviction": 0.50,
        "required_tools": ["get_balance", "check_persona_bounds"],
    },
}
```

---

## 7. 새 상수 / 모델 변경

### `constants.py`
```python
# 확장
TRACE_STAGES = ("intake", "policy", "strategy", "risk", "evaluator", "execution", "run_summary")
CHECK_STAGES = ("intake", "policy", "strategy", "risk", "evaluator", "execution", "be_revalidation")

# 신규 HOLD reasons
HOLD_INPUT_AMBIGUOUS    = "HOLD_INPUT_AMBIGUOUS"
HOLD_LOW_CONVICTION     = "HOLD_LOW_CONVICTION"
HOLD_RISK_AGENT_FLAGGED = "HOLD_RISK_AGENT_FLAGGED"
# HOLD_TRADER_DEVIATION은 strict faithfulness phase에서 후속 도입

# Risk Gate
RISK_VOLATILITY_ATR_THRESHOLD = 0.08

# Persona
PERSONA_CONSERVATIVE = "CONSERVATIVE"
PERSONA_MODERATE     = "MODERATE"
PERSONA_AGGRESSIVE   = "AGGRESSIVE"

# Trader
DEFAULT_TRADER = "wonyotti"

# Risk Agent (optional 확장)
MAX_TOOL_CALLS = 4   # 데모 rate limit 회피
```

### `models.py` — `AgentState` 추가 필드
```python
trader_id: str                          # default "wonyotti"; optional dataset "livermore"
inferred_persona: str                   # "MODERATE"
persona_override_reason: NotRequired[str]
trader_principles: List[JsonDict]       # RAG retrieved
llm_proposal: JsonDict                  # strategy 결과
risk_assessment: JsonDict               # risk_gate 또는 risk_agent 최종
risk_tool_calls: List[JsonDict]         # risk_gate tools + optional ReAct chain
evaluator_review: JsonDict              # 최종 리포트/형식 검증 결과
```

### `validators.py:assert_trace_container` 소프트화 (P0-1)
```python
def assert_trace_container(trace, prefix="decision_trace"):
    # 새 stage(intake/strategy)는 옵셔널
    REQUIRED_STAGES = ("policy", "risk", "evaluator", "execution", "run_summary")
    for stage in REQUIRED_STAGES:
        if stage not in trace:
            raise AssertionError(f"missing {prefix} stage: {stage}")
        # ...기존 검증
```
→ 기존 24개 테스트 + QA evidence JSON 깨지지 않음.

새 stage(`intake`, `strategy`)는 기존 회귀 방지를 위해 required stage는 아니지만, 해당 노드가 실제 호출되면 반드시 자기 stage의 `decision_trace`와 `verification_checks`를 append한다. 데모 trace가 비는 것을 막기 위한 코딩 컨벤션이다.

---

## 8. 작업 순서 (Phase-by-Phase)

### Phase 0a — 기반 (15분, 의존 X)
- [ ] `constants.py` 확장
- [ ] `models.py` 새 필드 추가
- [ ] `validators.py` 소프트화 (P0-1)
- [ ] `personas.py` 신설
- [ ] `tools/_mock_data.py`

→ **검증**: 기존 `pytest` 통과해야 함 (회귀 없음)

### Phase 0b — Prompts + Knowledge (1h, 팀원 A 산출 도착 후)
- [ ] `prompts/intake_prompt.py` (환율 정책 명시)
- [ ] `prompts/strategy_prompt.py` (워뇨띠 원칙 주입 템플릿)
- [ ] `prompts/evaluator_prompt.py` (최종 리포트 + trace/schema sanity check)
- [ ] `prompts/risk_agent_prompt.py` (optional, 도구 호출 가이드)
- [ ] `knowledge/wonyotti/principles.md` (팀원 A or mock)

### Phase 1 — LLM/RAG 인프라 (2h)
- [ ] `llm.py` 채우기 — `gemini_generate` 우선, `gemini_step_with_tools`는 optional risk_agent 때 추가
- [ ] `rag/retriever.py` — md 파싱 + 키워드 매칭 (vector db 없음)
- [ ] `tools/registry.py` — `@tool` 데코레이터 + dispatch

### Phase 2 — 도구 (1.5h)
- [ ] 필수: `tools/account_tools.py` — `get_balance`
- [ ] 필수: `tools/policy_tools.py` — `check_persona_bounds`
- [ ] 필수: `tools/market_tools.py` — `get_volatility`
- [ ] Nice: `tools/market_tools.py` — `get_concentration_risk`
- [ ] Nice: `tools/policy_tools.py` — `check_daily_loss_limit`

### Phase 3a — 노드 1 (3h)
- [ ] `nodes/intake.py`
- [ ] `nodes/policy.py` 수정 (RAG 호출 + persona_bounds)
- [ ] `nodes/strategy.py`
- [ ] 각 단위 테스트 1~2개

### Phase 3b — 노드 2 (2h)
- [ ] `nodes/risk_gate.py`
- [ ] `nodes/evaluator.py` 수정 (최종 리포트 + trace/schema sanity check)
- [ ] 각 단위 테스트

### Phase 3c — Optional Agentic 확장 (2~3h, 남는 시간)
- [ ] `nodes/risk_agent.py` (ReAct + 마지막 structured output)
- [ ] `gemini_step_with_tools` 연결
- [ ] `risk_tool_calls` Lv2 trace 출력

### ⏸ 수면 (4~5h)

### Phase 4 — 통합 (2h)
- [ ] `graph.py` 새 노드 wire
- [ ] `app.py` resume immutable 보호 (P0-2)
- [ ] e2e 테스트 (`test_e2e_wonyotti.py`)

### Phase 5 — 코드 품질 + 데모 (3h)
- [ ] `examples/wonyotti_buy.json`, `wonyotti_hold.json`, `wonyotti_low_conviction.json`, `DISCLAIMER.md`
- [ ] `tests/` 커버리지 점검 + 누락 보강
- [ ] `basedpyright` 통과
- [ ] docstring 정리 (특히 도구 description — LLM이 직접 읽음)
- [ ] `README.md` 업데이트 (실행 방법 + 아키텍처 개요)

### Phase 6 — 영상 + git 정리 (1.5h)
- [ ] CLI 데모 영상 1~3분 녹화
- [ ] git commit 정리 (atomic)
- [ ] PR 생성 또는 main에 푸시

---

## 9. Cut Line — 못 끝내면 빠질 것

| 우선 | 기능 | 빠질 시 폴백 |
|---|---|---|
| Must | intake (NL→dict) | (없으면 못 빠짐) |
| Must | strategy (LLM trader) | 결정론 strategy 폴백은 imperfect |
| Must | trader RAG (워뇨띠 기본) | hardcoded principles 리스트로 fallback |
| Must | risk_gate (결정론) | (없으면 못 빠짐) |
| Must | evaluator summary | 코드 기반 summary라도 생성 |
| Should | risk_agent (ReAct + tools) | risk_gate가 mock tool 직접 호출 |
| Nice | evaluator faithfulness strict mode | strategy conviction + HOLD_LOW_CONVICTION으로 대체 |
| Nice | 인용 chunk_id 명시 | 원칙 제목만 표시 |
| Cut | 도구 5개 → 3개로 | get_balance + check_persona_bounds + get_volatility만 |
| Cut | multi-trader routing/UI | 워뇨띠 기본 + Livermore 데이터셋만 보관 |
| Cut | resume HOLD_TRADER_DEVIATION | MVP 미구현 |

→ **먼저 `intake → RAG → strategy → risk_gate → evaluator summary → e2e`를 끝까지 통과시킨다.** 그 다음 시간이 남으면 `risk_agent`를 붙인다.

---

## 9.1 T+0 → T+24 Schedule

| 구간 | 작업 | 누적 |
|---|---|---|
| Phase 0a | 기반 상수/모델/validator/persona/mock | 0.25h |
| Phase 0b | prompts + knowledge | 1.25h |
| Phase 1 | LLM/RAG/tool registry | 3.25h |
| Phase 2 | 필수 3개 도구 + Nice 2개 가능 시 | 4.75h |
| Phase 3a | intake/policy/strategy + 단위 테스트 | 7.75h |
| Phase 3b | risk_gate/evaluator summary + 단위 테스트 | 9.75h |
| 수면 | 4~5h | 14~15h |
| Phase 4 | graph/app/e2e 통합 | 16~17h |
| Phase 5 | 품질/README/examples | 19~20h |
| Phase 6 | 영상/git 정리 | 20.5~21.5h |
| Phase 3c optional | risk_agent ReAct | +2~3h |

3c를 포함하면 총 22~24h라 안전마진이 거의 없다. Phase 3b e2e가 흔들리면 3c는 즉시 스킵한다.

---

## 10. 작업 분담 (3인 팀)

### 👤 본인 (AI 코드)
- 모든 노드 + 도구 + RAG + LLM 인프라
- 단위 테스트 + e2e
- README 업데이트
- 영상 녹화

### 👤 팀원 A (코인 도메인 리서치)
- `knowledge/wonyotti/principles.md` 작성 (5~7개 원칙)
- 각 원칙에 출처 라벨 (인터뷰/SNS)
- 산출 시점: **오늘 밤 자정 전**
- 없으면 mock으로 진행

### 👤 팀원 B (트레이더 + LLM 통합 조사)
- LangGraph + Gemini 구조 정리 (`docs/notes/`)
- LangSmith 트레이싱 활성화 가이드
- 산출 시점: **이미 진행 중** — 결과 받는 즉시 `llm.py`에 반영

### 의존성 처리
- 팀원 A 산출 늦으면 → mock principles로 Phase 0b 시작 → 도착 시 교체
- 팀원 B 가이드 늦으면 → PoC 결과 기반으로 진행 (충분히 검증됨)

---

## 11. 평가 기준 (제출 모드)

### 코드 품질 (Must)
- [ ] `basedpyright` 통과
- [ ] 모든 신규 함수에 docstring
- [ ] 도구 description은 LLM이 읽으니 명확하게
- [ ] 기존 테스트 회귀 없음

### 동작 보증 (Must)
- [ ] `pytest tests/` 통과
- [ ] e2e 시나리오 1개 이상 (`test_e2e_wonyotti.py`)
- [ ] examples/ JSON으로 CLI 실행 가능

### 문서 (Must)
- [ ] `README.md` — 설치/실행/예시
- [ ] `examples/DISCLAIMER.md` — 트레이더 이름 사용 고지
- [ ] `docs/MASTER_PLAN.md` (이 문서) — 설계 의도

### 데모 (Must)
- [ ] CLI로 워뇨띠 happy path 영상
- [ ] CLI로 HOLD 케이스 영상
- [ ] decision_trace + evaluator summary 화면 캡처
- [ ] risk_agent 구현 시 risk_tool_calls 화면 캡처

### 보너스 (Nice)
- [ ] LangSmith trace 링크 (구현되었다면)
- [ ] 시나리오별 mock 3개 (advisor P1-2)
- [ ] persona별 동일 입력 비교

---

## 12. 환경 변수 (`.env.example` 갱신)

```bash
# Gemini
AI_LLM_PROVIDER=gemini
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-pro

# 신규
AUTOCOIN_AI_RUNS_FILE=.runtime/autocoin-ai-runs.json
BINANCE_MODE=disabled
AI_RISK_MAX_TOOL_CALLS=4
AI_DEFAULT_TRADER=wonyotti

# LangSmith (선택)
LANGSMITH_API_KEY=
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=autocoin-ai
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
```

---

## 13. Decision Log

| 날짜 | 결정 | 사유 / 근거 |
|---|---|---|
| 2026-05-09 | NL 파싱을 AI 안(`intake`)에 두기 | 데모 임팩트 + 분업 영향 최소 |
| 2026-05-09 | Persona는 계정 디폴트 + 발화 override 하이브리드 | 안전성 + 자연스러움 |
| 2026-05-09 | 모호 입력은 MVP에선 즉시 HOLD | Multi-turn은 v3로 |
| 2026-05-09 | 도구함은 통일, persona별 required_tools만 분기 | 코드 깔끔함 |
| 2026-05-09 | Trace Lv2 (thought 포함) | 비용 대비 가치 최적 |
| 2026-05-09 | Binance Testnet 유지 | 기존 코드 재활용 + 안전성 |
| 2026-05-09 | RAG 트레이더 워뇨띠 1명 | 단순화 + 데모 차별화 |
| 2026-05-09 | Vector DB 대신 키워드 매칭 | 24h 시간 제약 |
| 2026-05-09 | BE 도구는 mock fixture | BE 미구현 + 분업 자유도 |
| 2026-05-09 | CLI 데모 + 영상 (라이브 X) | 코드 제출이 평가 대상 |
| 2026-05-10 | `MAX_TOOL_CALLS = 4` (advisor P0-3) | 데모 rate limit 회피 |
| 2026-05-10 | `assert_trace_container` 소프트화 (P0-1) | 기존 테스트 회귀 차단 |
| 2026-05-10 | `HOLD_TRADER_DEVIATION`은 MVP 미구현 | evaluator 역할 축소. strategy conviction/HOLD_LOW_CONVICTION으로 대체 |
| 2026-05-10 | risk_agent 종료 후 structured output 1회 (PoC 결과) | LLM이 verdict 단어만 줄 수 있음 |
| 2026-05-10 | intake 프롬프트에 KRW→USDT 환율 명시 (PoC 결과) | "5만원" vs "10만원" 단위 일관성 결여 발견 |
| 2026-05-10 | SDK 시그니처 PoC 검증 완료 | `resp.parsed`, `part.function_call` 모두 동작 |
| 2026-05-10 | Evaluator를 최종 리포트/trace 정리자로 축소 | 데모 제출 안정성 우선. strict faithfulness는 후속 |
| 2026-05-10 | Gemini 2.5 Pro로 변경 | 판단 품질 우선. 공식 모델 코드 `gemini-2.5-pro` 사용 |
| 2026-05-10 | FE/BE 전달사항 추가 | FE는 AI 결과 표시, BE는 deterministic revalidation 책임 명확화 |
| 2026-05-10 | §4.1 Evaluator MVP 계약 신설 | 주문 판단 금지, final_action echo, LLM summary + 코드 fallback 명확화 |
| 2026-05-10 | §4.2 Risk Gate MVP 계약 신설 | MVP 핵심 결정론 검증 순서와 risk_tool_calls 기록 책임 명확화 |
| 2026-05-10 | Strategy schema에 `matched_principle_titles` 추가 | evaluator summary가 원칙 근거를 지어내지 않도록 방지 |
| 2026-05-10 | RAG 단계화 명시 | MVP는 키워드 매칭, v2는 embedding/vector retrieval |
| 2026-05-10 | §4.4 Intake 입력/실패 계약 신설 | `text/raw_text`와 기존 구조화 dict 호환, LLM/schema 실패는 `FAILED` |
| 2026-05-10 | §4.5 Graph 라우팅 계약 신설 | 모든 종료 케이스가 evaluator를 거쳐 user_message 생성 |
| 2026-05-10 | §4.6 Resume 흐름 결정 | MVP는 전체 재실행 + immutable cache hit로 LLM/RAG 재호출 방지 |
| 2026-05-10 | 보조 RAG dataset으로 Jesse Livermore 추가 | 데이터셋 확장성 시연. MVP 기본 trader는 wonyotti 유지 |

---

## 14. 부록 — 즉시 실행 체크리스트

### 시작 전 (지금)
- [x] PoC 두 스크립트 통과 ✓
- [ ] 팀원 A에게 `principles.md` 형식 공유 (이 문서 6.1)
- [ ] 팀원 B 통합 가이드 받기
- [ ] `.env`에 `LANGSMITH_*` 채우기 (선택)

### Phase 0a 시작 시 가장 먼저
- [ ] `constants.py` 확장 + 새 stages 추가
- [ ] `models.py` 새 필드
- [ ] `validators.py` 소프트화 → 기존 `pytest tests/` 한 번 돌려서 회귀 없음 확인
- [ ] `personas.py` 신설
- [ ] `tools/_mock_data.py`

### Phase 1 시작 시
- [ ] `llm.py`에 PoC 검증된 시그니처 그대로 박기
- [ ] `rag/retriever.py` md 파싱 (간단 H2 split)
- [ ] `tools/registry.py` 데코레이터 + dispatch

### 고비 (T+9.25h, Phase 3b)
- [ ] `intake → RAG → strategy → risk_gate → evaluator summary` e2e 확인
- [ ] e2e가 통과하면 optional `risk_agent` 착수
- [ ] e2e가 불안정하면 `risk_agent`는 스킵하고 HOLD/BUY 시나리오 안정화

### 최종 점검 (T+22h)
- [ ] `pytest tests/` 전체 통과
- [ ] `basedpyright` 0 error
- [ ] CLI 시나리오 2개 (buy / hold) 실행 영상
- [ ] git log 정리

---

## 📌 단일 진실 (Single Source of Truth)

이 문서가 캐노니컬 플랜이다. 결정 변경 시:
1. **Decision Log (13장)에 한 줄 추가**
2. 영향 받는 섹션 직접 수정
3. 다른 문서(`AGENTIC_UPGRADE.md` 등)는 갱신 의무 없음 — 이 문서만 갱신

> **다음 액션**: Phase 0a 시작 — `constants.py` + `models.py` + `validators.py` 소프트화부터.
