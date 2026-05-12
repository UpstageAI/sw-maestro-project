# autocoin-ai Agentic Upgrade — 24h MVP 플랜 리뷰

> **상태**: Advisor 리뷰 결과
> **작성일**: 2026-05-10
> **대상 플랜**: `AGENTIC_UPGRADE.md` + 워뇨띠 RAG 확장 + 24h MVP 일정
> **리뷰어 시점**: 24시간 데드라인 + 3인 팀 + 바이브 코딩 환경

---

## 📌 한 줄 요약

> 플랜의 골격은 탄탄. 다만 24시간 안에 실행하려면 **사전 PoC 2시간 + 기존 테스트 마이그레이션 + LLM 호출 예산** 세 가지를 락인하지 않으면 새벽에 무너질 가능성이 큽니다. P0 4개, P1 4개, P2 3개로 분리합니다.

---

## ✅ 잘 잡힌 부분 (유지)

- **6-phase 의존성 그래프**가 명확. 병렬화 가능 지점도 표시되어 있음.
- **Mock-first** 접근 — BE 미구현이라는 현실을 잘 흡수.
- **결정론 가드(`risk_gate`)를 LLM 뒤에 두는** 디자인. 환각 차단 정통 패턴.
- **인용(citation) 강제** — RAG 환각 방지용으로 옳은 선택.
- **CLI 데모**로 FE 의존성 끊은 것 — 24h 모드에 맞는 결정.

---

## 🔴 P0 — 지금 락인 안 하면 플랜 깨짐

### P0-1. 기존 테스트 24개+ 가 즉시 깨짐

`constants.py`에서 `TRACE_STAGES`를 `("policy", "risk", "evaluator", "execution", "run_summary")` → `("intake", "policy", "strategy", "risk", "evaluator", "execution", "run_summary")` 로 바꾸는 순간, `validators.py:assert_trace_container()`가 **모든 기존 state**에 대해 `missing decision_trace stage: intake` 를 던집니다.

영향:
- `tests/` 의 모든 happy path 테스트
- `qa/B/`, `qa/C/` evidence JSON (PR #2, #6에서 추가됨)
- `app.py:start()`의 `assert_contract_state()` 호출

**액션 (선택)**:
- A. `assert_trace_container`를 **소프트화** — 신규 stage는 옵셔널로
- B. 기존 fixture를 **새 stage로 마이그레이션 스크립트**로 일괄 업데이트
- C. **새 그래프는 별도 lifecycle 키**로 분리 (`agentic_lifecycle_status` 등)

→ **A가 가장 빠름** (15분). B는 evidence JSON 30+ 개 손대야 함. C는 두 코드패스 유지라 부담 큼.

### P0-2. Resume 의미가 새 필드들에 대해 미정의

`docs/AI.md`의 immutable vs patchable 계약:
> immutable: `run_id`, 최초 `request_context`, 최초 `policy_context`, 이전 `decision_trace`, 이전 `verification_checks`

새 필드 처리 방침이 플랜에 없음:

| 필드 | immutable? patchable? |
|---|---|
| `trader_id` | **immutable** (resume 시 트레이더 변경 불가) |
| `trader_principles` | **immutable** (RAG 결과는 grounding) |
| `llm_proposal` | **patchable** (재실행 시 재생성) |
| `risk_assessment` | **patchable** |
| `risk_tool_calls` | **append-only** (history 이전 것 유지 + 새것 추가) |
| `evaluator_review` | **patchable** |

→ `app.py:resume()`와 `models.py:state_copy()`에 명시 추가. 이거 안 하면 **`HOLD_TRADER_DEVIATION` 후 resume 시 새 트레이더로 갈아탈 수 있는 구멍** 생김.

### P0-3. LLM 호출 폭주 → 데모 시연 중 rate limit / 지연

한 run당 LLM 호출:
- intake: 1회
- strategy: 1회
- risk_agent: **최대 8회** (MAX_TOOL_CALLS) + 최종 1회
- evaluator: 1회

→ **최악 12회/run**. Gemini 무료 티어는 RPM 제한 빠르게 침. 데모 중 "다시 한 번" 했다가 rate limit으로 사고 가능.

**액션**:
- MVP에서는 `MAX_TOOL_CALLS = 4` 로 강하게 제한
- **데모용 응답 캐시** 추가: 같은 (prompt, schema) 입력은 디스크 캐시 (`.cache/llm/`). 데모 한 번 미리 돌려서 캐시 채우기.
- `AI_DEMO_MODE=true` 환경변수 → 캐시 강제 hit

### P0-4. Gemini structured output / function calling은 가정이지 검증 아님

플랜의 `gemini_generate(prompt, response_schema={...})`, `gemini_generate_with_tools(messages, tools=tool_specs)` 는 **의사 코드**. 실제 `google-genai` v1.x SDK의 정확한 호출 형태와 다를 수 있음 (특히 function calling 응답 shape).

→ **Phase 0 시작 전 60분 PoC 필수**:
```
1. structured output 한 번 성공 (intake 스키마로)
2. function calling 한 번 성공 (1개 도구로)
3. 양쪽 응답 객체 attribute 정확히 기록 → llm.py에 그대로 매핑
```

이 PoC 실패하면 → 도구 호출은 **수동 JSON 파싱 폴백**으로 가야 함 (시간 더 듦).

---

## 🟡 P1 — 중요 보정

### P1-1. Phase 0 안의 숨은 의존성

플랜은 Phase 0를 "병렬 가능"으로 표시했지만, 실제로는:
```
constants.py + models.py
        ↓
  prompts/*.py    ← response_schema가 models의 TypedDict를 참조
        ↓
  tools/_mock_data.py  (독립)
```

**액션**: Phase 0를 두 단계로 쪼갬.
- Phase 0a (15분): `constants.py`, `models.py`, `personas.py`/`traders.py`, `tools/_mock_data.py`
- Phase 0b (1h): `prompts/*.py`, `principles.md`

### P1-2. Mock 데이터가 정적 → 시연 임팩트 약화

현재 mock은 한 가지 시장 상태만 있음. "워뇨띠가 같은 시장 상태에서 BUY vs HOLD가 갈리는" 시연이 안 됨.

**액션**: mock을 **2~3개 시나리오**로:
```python
MOCK_SCENARIOS = {
    "trending_up":   {"volatility": 0.045, "trend": "UP",       "volume_anomaly": False},
    "sideways":      {"volatility": 0.025, "trend": "SIDEWAYS", "volume_anomaly": False},
    "volatile":      {"volatility": 0.092, "trend": "DOWN",     "volume_anomaly": True},
}
# request_context.user_input.market_scenario 로 선택
```

→ 데모 input 3개 만들 수 있음: trending_up=APPROVE / sideways=HOLD / volatile=DEVIATES.

### P1-3. 트레이더 이름 사용 — 법적 리스크 그대로 이월됨

이전 advisor 의견에서 "공인 인사 + 사망/공개 도서 위주" 권장 → 사용자가 **워뇨띠로 결정**. 이 결정은 존중하지만, **demo 첫 슬라이드에 disclaimer 한 줄**은 비용 0이고 보호 큼.

```
"본 데모는 공개 인터뷰/SNS 발언을 기반으로 매매 스타일을 학습한
시뮬레이션입니다. 실제 인물의 동의/검수를 받지 않았으며,
실제 매매 결과를 보장하지 않습니다."
```

→ `examples/`에 `DISCLAIMER.md` 추가. CLI 첫 줄에도 출력.

### P1-4. 시간 추정 vs 자체 추정의 모순

플랜에서 "1700줄, 24시간 가능"이라 했지만, 같은 트랜스크립트에서:
> "솔직히 정상 페이스로 1~2주짜리 작업이에요. AI/바이브 코딩 써도 6~8일"

이 둘이 충돌. 후자가 더 정확할 가능성 큼. P0-1 (테스트 마이그레이션) + P0-4 (Gemini PoC 실패 시 폴백) 합치면 8~12시간이 추가로 들 수 있음.

**액션**: **Demo Cut Line**을 미리 정의.
- **반드시 동작**: intake + strategy + risk_gate(deterministic only, no agent) + evaluator (deterministic only, no LLM)
- **있으면 좋음**: risk_agent (tool loop), evaluator LLM faithfulness
- **포기 가능**: trader 2명 이상, multi-scenario mocks, evaluator citations

→ 새벽 4시에 risk_agent가 안 되면 deterministic 버전으로 폴백, 데모는 진행.

---

## 🟢 P2 — 권장 보강

### P2-1. `risk_tool_calls`를 verification_checks와 분리

플랜의 state 확장은 두 곳에 검증을 분산:
- `verification_checks` (기존, append-only)
- `risk_tool_calls` (신규)

기존 `evaluator_node`는 `verification_checks`에서 카운트. 새 `risk_agent` 호출 결과가 `verification_checks`에 안 들어가면 evaluator의 deterministic 카운트가 망가짐.

→ `risk_agent` 종료 시 `append_check(state, "risk_agent_complete", "risk", "pass", [...])` 한 줄 명시. 이미 의사 코드에 있긴 한데, **검증 의무로 못 박기**.

### P2-2. `HOLD_TRADER_DEVIATION` 의 resume 정책 정의

evaluator가 DEVIATES → HOLD. 이걸 resume하려면 무엇을 patch해야 하나?

옵션:
- A. resume 불가 (terminal HOLD) — 사용자가 새 run으로 재시작
- B. patch_fields = `{"approval": {"override_deviation": true}}` 받으면 진행 — 사용자가 명시적 동의
- C. 새 trader_id로 재시도 (워뇨띠 → 세일러)

**제 추천: A 또는 B**. C는 trader_id immutable 원칙 위반.

이거 명시 안 해두면 사용자가 "그래도 사고 싶어요" 했을 때 코드가 미정의 동작.

### P2-3. 데모 시연 안전망

11시 시연 → 10:55에 한 번 돌려보고 무대 올라가는 패턴 위험. 다음을 미리 준비:

| 자산 | 위치 | 용도 |
|---|---|---|
| 캐시된 LLM 응답 (3개 시나리오) | `.cache/llm/` | rate limit 백업 |
| 미리 녹화한 trace JSON | `qa/demo/golden_trace.json` | 라이브 실패 시 "녹화본" 재생 |
| 데모 스크립트 단축키 | `scripts/demo.sh` | 손 안 떨리게 |
| Network off 모드 | `AI_DEMO_OFFLINE=true` | 인터넷 끊어져도 캐시로 진행 |

---

## 🚦 사전 PoC (Phase 0 전, 60~90분)

다음 두 스니펫이 동작해야 플랜 진행. 둘 다 실패하면 **risk_agent ReAct는 폐기, 결정론 fallback으로**.

```python
# poc_structured.py
from google import genai
client = genai.Client(api_key=...)
resp = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="BTC 5만원 사줘",
    config={
        "response_mime_type": "application/json",
        "response_schema": {...},  # SDK 스펙 확인 필요
    },
)
print(resp.parsed)  # 또는 resp.text 파싱
```

```python
# poc_function_calling.py
tool = {"name": "get_balance", "description": "...", "parameters": {...}}
resp = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="잔고 확인해줘",
    config={"tools": [{"function_declarations": [tool]}]},
)
# resp.candidates[0].content.parts[*].function_call ?
print(resp)  # 정확한 attribute 경로 기록
```

→ 이 결과를 그대로 `llm.py`의 시그니처로 굳히세요. 의사 코드 그대로 쓰면 안 맞을 수 있음.

---

## 📋 수정된 작업 순서 (P0/P1 반영)

```
T+0h     PoC 60~90분 — Gemini structured output + function calling 검증
         └ 실패 시 즉시 fallback 결정 (deterministic-only MVP로 축소)

T+1.5h   Phase 0a (15min) — constants/models/mock_data + assert_trace_container 소프트화
T+1.75h  Phase 0b (1h)    — prompts/principles.md (팀원 A 산출 도착 가정)

T+2.75h  Phase 1 (2h)     — llm.py 실제 채우기 + rag/retriever + tools/registry
T+4.75h  Phase 2 (1.5h)   — tools 5개

T+6.25h  Phase 3a (3h)    — intake, policy, strategy 노드 + 단위 테스트
T+9.25h  Phase 3b (3h)    — risk_agent, risk_gate, evaluator + 단위 테스트

T+12h    ⏸ 수면 (반드시 4~5시간)

T+17h    Phase 4 (2h)     — graph wiring + 통합 테스트
T+19h    Phase 5 (2h)     — 데모 input 3개 + CLI 데모 스크립트 + LLM 응답 캐시
T+21h    Buffer (2h)      — 발견된 버그 / DEVIATES 시연 디버그
T+23h    데모 리허설 2회 + DISCLAIMER 추가
```

T+9.25h에 risk_agent가 막히면 → **deterministic 폴백 시점**. 새벽까지 끌지 말 것.

---

## 🎯 Cut Line 명시 (못 하면 빠짐)

| 우선순위 | 기능 | 빠질 시 영향 |
|---|---|---|
| Must | intake (NL→dict) | 데모 인풋이 자연어가 아니게 됨. 데모 약해짐. |
| Must | strategy (LLM trader) | "AI가 판단" 그림이 사라짐 |
| Must | trader RAG (1명, 키워드 매칭) | 워뇨띠 차별화 사라짐 |
| Must | evaluator (deterministic 최소) | lifecycle 깨짐 |
| Should | risk_agent (LLM + tools) | 결정론 risk로 폴백 가능 |
| Should | evaluator faithfulness LLM | DEVIATES 시연 못 함 |
| Nice  | citation chunks 명시 | 인용 없이 verdict만 보여줘도 됨 |
| Cut   | trader 2명 이상 | 1명으로 충분 |
| Cut   | multi-scenario mocks | 1개 시나리오로 데모 |
| Cut   | resume 흐름 동작 | 데모는 fresh start만 |

---

## 🔑 한 줄 결론

> **PoC 90분 + assert_trace_container 소프트화 15분 + LLM 응답 캐시 1시간 = 합계 ~2시간**.
> 이 셋을 Phase 0 전에 락인하면 24h MVP 가능. 없으면 새벽에 무너집니다.
>
> **데모 cut line을 미리 정해서 새벽 3시에 폴백 결정을 미루지 마세요.**

---

## 📎 부록 — 액션 아이템 체크리스트

### 즉시 (Phase 0 전)
- [ ] `assert_trace_container`를 새 stage 옵셔널로 소프트화 (15분)
- [ ] Gemini structured output PoC 1개 성공
- [ ] Gemini function calling PoC 1개 성공
- [ ] 응답 객체 attribute 경로 기록 → `llm.py` 시그니처 확정
- [ ] `MAX_TOOL_CALLS = 4` 로 강하게 제한
- [ ] `.cache/llm/` 디스크 캐시 골격 (key=hash(prompt+schema))

### 락인할 디자인 결정
- [ ] 새 state 필드 immutable/patchable 정책 명시 (위 표)
- [ ] `HOLD_TRADER_DEVIATION` resume 정책: A 또는 B 중 선택
- [ ] Mock 시나리오 3개 키 결정 (`trending_up`/`sideways`/`volatile`)
- [ ] Trader: 워뇨띠 1명 — `DISCLAIMER.md` 작성

### 데모 안전망
- [ ] `qa/demo/golden_trace.json` 미리 생성 (라이브 실패 시 폴백)
- [ ] `scripts/demo.sh` 단축 실행 스크립트
- [ ] `AI_DEMO_MODE=true` 환경변수로 캐시 강제 hit
- [ ] 시연 30분 전 dry-run 1회

### 못 하면 빠질 것 (Cut)
- [ ] Trader 2명 이상 (워뇨띠 1명 고정)
- [ ] Multi-scenario mocks (단일 시나리오로)
- [ ] Resume 흐름 데모 (fresh start만)

---

> 📌 이 문서는 `AGENTIC_UPGRADE.md` v2 작업 시 P0/P1 항목을 우선 반영해야 함.
