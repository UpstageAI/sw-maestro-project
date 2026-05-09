# autocoin-ai · 작업 단계(Phases)

> **상태**: 캐노니컬 / ralph 단일 루프 단위
> **작성일**: 2026-05-10
> **연관 문서**: `CONTRACTS.md` (계약), `FIXTURES.md` (테스트 데이터), `MASTER_PLAN.md` (비전)

각 phase는 **단일 ralph 루프 / 단일 PR / 단일 시간 budget**으로 끊어졌다.
Phase 시작 시 `precondition`을 만족해야 하고, 종료 시 `acceptance`를 통과해야 한다.

---

## 작업 단계 일람 (T+0 → T+24h)

| Phase | 시간 | 주요 산출 | 의존 |
|---|---|---|---|
| **0a** | 15m | constants/models/validators 확장 | (없음) |
| **0b** | 1h | prompts + knowledge | 0a |
| **1**  | 2h | llm + RAG + tools registry | 0a, 0b |
| **2**  | 1.5h | 도구 5개 | 1 |
| **3a-1** | 45m | intake 노드 + 테스트 | 1, 2, FIXTURES intake |
| **3a-2** | 45m | policy 노드 (수정) + 테스트 | 3a-1, FIXTURES policy |
| **3a-3** | 90m | strategy 노드 + 테스트 | 3a-2, FIXTURES strategy |
| **3b-1** | 90m | risk_gate 노드 + 테스트 | 3a-3, FIXTURES risk_gate |
| **3b-2** | 60m | evaluator 노드 (수정) + 테스트 | 3b-1, FIXTURES evaluator |
| **수면** | 4-5h | - | - |
| **3c (opt)** | 2~3h | risk_agent (ReAct) | 3b-2 통과 + 시간 여유 |
| **4**  | 2h | graph wiring + e2e | 3b-2 (또는 3c) |
| **5**  | 3h | 코드 품질 + examples + README | 4 |
| **6**  | 1.5h | 영상 + git 정리 | 5 |

**합계 (3c 제외)**: 21h  
**3c 포함**: 23~24h (빠듯)

---

## Phase 0a — 기반 인프라

**Precondition**: PoC 두 스크립트 통과 ✓

**Allowed files** (편집 가능):
- `src/autocoin_ai/constants.py`
- `src/autocoin_ai/models.py`
- `src/autocoin_ai/validators.py`
- `src/autocoin_ai/personas.py` (신규)
- `src/autocoin_ai/traders.py` (신규)
- `src/autocoin_ai/tools/_mock_data.py` (신규)
- `src/autocoin_ai/tools/__init__.py` (신규, 빈 파일 OK)

**Forbidden**:
- 노드 파일 (`nodes/*.py`) 추가/수정
- LLM 호출 코드
- prompts/

**Tasks**:
1. `constants.py` 확장 (CONTRACTS §13.1)
2. `models.py` `AgentState` 신규 필드 8개 추가 (CONTRACTS §13.2)
3. `validators.py:assert_trace_container` 소프트화 (CONTRACTS §13.3)
4. `personas.py` 신설 — `PERSONA_PROFILES` dict
5. `traders.py` 신설 — `TraderMeta`, `Principle`, `load_trader()` (CONTRACTS §1)
6. `tools/_mock_data.py` 신설 — MOCK_BALANCE / MOCK_VOLATILITY / MOCK_CONCENTRATION
7. `tools/__init__.py` 신설 (빈 파일)

**Acceptance**:
```bash
pytest tests/                            # 기존 테스트 24개 모두 통과 (회귀 없음)
python -c "from autocoin_ai.traders import load_trader; t=load_trader('livermore'); print(len(t.principles))"
# → 9 (또는 livermore principles.md 헤더 개수)
```

**Forbidden additions**:
- `from langgraph` import (그래프 wiring은 Phase 4)
- 새 lifecycle 상수 추가 (FAILED 등은 기존 유지)

---

## Phase 0b — Prompts + Knowledge

**Precondition**: 0a 통과.

**Allowed files**:
- `src/autocoin_ai/prompts/__init__.py`
- `src/autocoin_ai/prompts/intake_prompt.py`
- `src/autocoin_ai/prompts/strategy_prompt.py`
- `src/autocoin_ai/prompts/evaluator_prompt.py`
- `src/autocoin_ai/prompts/risk_agent_prompt.py` (Phase 3c용, 미리 작성)
- `knowledge/wonyotti/principles.md` (팀원 A 산출물 기다리되, 도착 전엔 mock으로)
- `knowledge/livermore/principles.md` (이미 있음 ✓)

**Forbidden**:
- LLM 실제 호출
- 노드 import

**Tasks**:
1. `intake_prompt.py` — system_instruction 문자열 + INTAKE_SCHEMA dict (CONTRACTS §4.2 + §11.3 환율)
2. `strategy_prompt.py` — system_instruction + STRATEGY_SCHEMA (CONTRACTS §6.2)
3. `evaluator_prompt.py` — system_instruction + EVALUATOR_SCHEMA (CONTRACTS §8.4)
4. `risk_agent_prompt.py` — system_instruction (Phase 3c가 사용)
5. `knowledge/wonyotti/principles.md` — 팀원 A or **mock 5~7개** (livermore 형식 참고)

**Acceptance**:
```bash
python -c "from autocoin_ai.prompts.intake_prompt import INTAKE_SCHEMA, INTAKE_SYSTEM_INSTRUCTION; print(INTAKE_SCHEMA['required'])"
# → ['symbol', 'side', 'type', 'size_usd', 'trader_id', 'inferred_persona', 'persona_override_reason', 'ambiguity_score']

python -c "from autocoin_ai.traders import load_trader; print(load_trader('wonyotti').display_name)"
# → "워뇨띠" 또는 등록된 이름
```

---

## Phase 1 — LLM/RAG/Tools 인프라

**Precondition**: 0a, 0b 통과. `.env`에 `GEMINI_API_KEY` 채워짐.

**Allowed files**:
- `src/autocoin_ai/llm.py` (수정)
- `src/autocoin_ai/rag/__init__.py`
- `src/autocoin_ai/rag/retriever.py`
- `src/autocoin_ai/tools/registry.py`

**Forbidden**:
- 노드 파일
- 도구 함수 (Phase 2)

**Tasks**:
1. `llm.py` 수정:
   - `gemini_generate(prompt, response_schema, system_instruction="")` (CONTRACTS §11.1)
   - `gemini_step_with_tools(contents, tools, system_instruction="")` (§11.2, optional risk_agent용)
   - `LlmSettings` / `create_gemini_client()` 기존 유지
   - 모듈 상단에 `_client` 캐싱 (Client 한 번만 생성)
2. `rag/retriever.py`:
   - `retrieve_relevant(trader_id, query, k=5) -> list[Principle]` (CONTRACTS §1.3)
   - 키워드 매칭 + top-k
3. `tools/registry.py`:
   - `Tool` dataclass
   - `REGISTRY: dict[str, Tool]`
   - `tool(schema)` 데코레이터
   - `dispatch(name, args, run_id=None) -> dict`

**Acceptance**:
```bash
python -c "
from autocoin_ai.llm import gemini_generate
r = gemini_generate('Hello in JSON format', {'type':'OBJECT','properties':{'msg':{'type':'STRING'}},'required':['msg']})
print(r)
"
# → 실제 Gemini 응답 dict

python -c "
from autocoin_ai.rag.retriever import retrieve_relevant
r = retrieve_relevant('livermore', 'BTCUSDT BUY trend', k=3)
print([p.title for p in r])
"
# → 3개 title 출력 (추세 관련 원칙 우선)
```

---

## Phase 2 — Tools 5개

**Precondition**: 1 통과.

**Allowed files**:
- `src/autocoin_ai/tools/account_tools.py`
- `src/autocoin_ai/tools/market_tools.py`
- `src/autocoin_ai/tools/policy_tools.py`

**Forbidden**:
- 노드 파일
- 새 mock 데이터 (Phase 0a의 `_mock_data.py` 수정 금지)

**Tasks**:
1. `account_tools.py`:
   - `get_balance(asset: str) -> dict`
   - `get_concentration_risk(symbol: str, proposed_size_usd: str) -> dict`
2. `market_tools.py`:
   - `get_volatility(symbol: str, days: int) -> dict`
3. `policy_tools.py`:
   - `check_persona_bounds(action: str, symbol: str, size_usd: str) -> dict`
   - `check_daily_loss_limit() -> dict` (Phase 3c용 placeholder)

각 도구는 `@tool` 데코레이터로 등록.

**Acceptance**:
```bash
python -c "
import autocoin_ai.tools.account_tools  # @tool 등록
import autocoin_ai.tools.market_tools
import autocoin_ai.tools.policy_tools
from autocoin_ai.tools.registry import REGISTRY, dispatch
print(sorted(REGISTRY.keys()))
# → ['check_daily_loss_limit', 'check_persona_bounds', 'get_balance', 'get_concentration_risk', 'get_volatility']
print(dispatch('get_balance', {'asset': 'USDT'}))
# → {'free': '5000.0', ...}
"
```

---

## Phase 3a-1 — Intake 노드

**Precondition**: 1, 2 통과. `tests/fixtures/intake_input_*.json`, `intake_output_*.json` 작성됨 (FIXTURES.md).

**Allowed files**:
- `src/autocoin_ai/nodes/intake.py`
- `tests/test_intake.py`

**Forbidden**:
- 다른 노드 파일
- `request_context` 직접 변경
- 새 lifecycle 상수

**Tasks**:
1. `intake_node(state)` 구현 (CONTRACTS §4)
   - text/dict 분기
   - LLM 모드: `gemini_generate(text, INTAKE_SCHEMA, INTAKE_SYSTEM_INSTRUCTION)`
   - dict 모드: 기존 로직
   - ambiguity_score > 0.5 → HOLD
   - schema 깨짐 → FAILED
2. 단위 테스트 (FIXTURES intake 4개 fixture 사용):
   - `test_intake_text_buy` — text 모드 happy
   - `test_intake_text_ambiguous` — HOLD_INPUT_AMBIGUOUS
   - `test_intake_dict_legacy` — dict 모드 회귀
   - `test_intake_missing_fields` — FAILED

**Acceptance**:
```bash
pytest tests/test_intake.py -v
# 4개 통과
```

**비고**: LLM 호출은 실 호출. 캐싱은 Phase 5에서 추가.

---

## Phase 3a-2 — Policy 노드 (수정)

**Precondition**: 3a-1 통과. FIXTURES `policy_output_*.json` 작성됨.

**Allowed files**:
- `src/autocoin_ai/nodes/policy.py`
- `tests/test_policy.py` (수정 또는 신규)

**Forbidden**:
- intake / strategy 등 다른 노드
- LLM 호출 (policy는 결정론)

**Tasks**:
1. `policy_node` 수정 (CONTRACTS §5):
   - 기존 정규화 로직은 intake로 이동 → policy는 검증만
   - `policy_context.persona = state["inferred_persona"]`
   - `policy_context.persona_bounds = PERSONA_PROFILES[persona]`
   - RAG 호출: `state["trader_principles"] = [asdict(p) for p in retrieve_relevant(trader_id, query, k=5)]`
2. 테스트:
   - `test_policy_grounding` — happy
   - `test_policy_passes_failed` — lifecycle FAILED일 때 no-op

**Acceptance**:
```bash
pytest tests/test_policy.py -v
```

---

## Phase 3a-3 — Strategy 노드

**Precondition**: 3a-2 통과. FIXTURES `strategy_output_*.json`.

**Allowed files**:
- `src/autocoin_ai/nodes/strategy.py`
- `tests/test_strategy.py`

**Forbidden**:
- 다른 노드
- 도구 호출

**Tasks**:
1. `strategy_node(state)` 구현 (CONTRACTS §6)
   - prompt = STRATEGY_SYSTEM_INSTRUCTION + (intent + principles + bounds 요약)
   - `gemini_generate(prompt, STRATEGY_SCHEMA, STRATEGY_SYSTEM_INSTRUCTION)`
   - matched_principle_titles 검증 (trader_principles에 실재하는 title인지)
2. 테스트:
   - `test_strategy_buy_proposal` — happy with conviction
   - `test_strategy_hold_action` — LLM이 HOLD 줄 때
   - `test_strategy_passes_failed` — lifecycle FAILED no-op
   - `test_strategy_invalid_principles` — 환각 title 시 schema_warning

**Acceptance**:
```bash
pytest tests/test_strategy.py -v
```

---

## Phase 3b-1 — Risk Gate 노드

**Precondition**: 3a-3 통과. FIXTURES `risk_gate_output_*.json`.

**Allowed files**:
- `src/autocoin_ai/nodes/risk_gate.py`
- `tests/test_risk_gate.py`

**Forbidden**:
- LLM 호출 (결정론)
- `llm_proposal` 수정

**Tasks**:
1. `risk_gate_node(state)` 구현 (CONTRACTS §7)
   - 7가지 검증 위→아래 순서
   - 첫 실패에서 short-circuit (그 이후 도구 호출 X)
   - 통과한 도구 호출은 `risk_tool_calls`에 append
2. 테스트 (각 실패 케이스마다):
   - `test_risk_gate_pass` — READY_FOR_BE
   - `test_risk_gate_low_conviction` — HOLD_LOW_CONVICTION
   - `test_risk_gate_size_exceeds` — NO_ORDER
   - `test_risk_gate_symbol_blocked` — NO_ORDER
   - `test_risk_gate_balance_short` — HOLD_DATA_INSUFFICIENT
   - `test_risk_gate_volatility_high` — HOLD_RISK_AGENT_FLAGGED

**Acceptance**:
```bash
pytest tests/test_risk_gate.py -v
# 6개 통과
```

---

## Phase 3b-2 — Evaluator 노드 (수정)

**Precondition**: 3b-1 통과. FIXTURES `evaluator_output_*.json`.

**Allowed files**:
- `src/autocoin_ai/nodes/evaluator.py`
- `tests/test_evaluator_summary.py`

**Forbidden**:
- `lifecycle_status` 변경
- `llm_proposal.action` 수정
- 신규 hold_reason 생성

**Tasks**:
1. `evaluator_node(state)` 수정 (CONTRACTS §8)
   - 모든 lifecycle 케이스 (HOLD/NO_ORDER/READY_FOR_BE) 항상 실행
   - LLM 호출: EVALUATOR_SCHEMA
   - schema_warnings 4개 sanity 체크 수행
   - LLM 실패 시 결정론 폴백 (CONTRACTS §8.8)
2. 테스트:
   - `test_evaluator_ready_for_be` — happy
   - `test_evaluator_hold_summary` — HOLD 케이스도 user_message 생성
   - `test_evaluator_no_order_summary` — NO_ORDER 케이스
   - `test_evaluator_llm_fallback` — LLM 호출 실패 시 결정론 폴백 (mock으로)

**Acceptance**:
```bash
pytest tests/test_evaluator_summary.py -v
```

---

## Phase 3c (Optional) — Risk Agent

**Precondition**: 3b-2 통과. **시간이 충분히 남음** (T+12h ~ T+15h 사이 진입 가능 시).

**Allowed files**:
- `src/autocoin_ai/nodes/risk_agent.py`
- `tests/test_risk_agent.py`

**Tasks**:
1. ReAct 루프 (CONTRACTS §11.2 + §11.4)
2. MAX_TOOL_CALLS=4 강제
3. 종료 후 structured output 1회로 risk_assessment 생성
4. graph.py에서 strategy → risk_agent → risk_gate 추가

**Acceptance**:
```bash
pytest tests/test_risk_agent.py -v  # 1~2개
# + e2e에서 risk_tool_calls 길이 ≥ 1 확인
```

**Cut Line**: 진입 시점에 새벽 4시 넘었으면 **포기**. 결정론 risk_gate만으로 진행.

---

## Phase 4 — Graph 통합

**Precondition**: 3b-2 통과 (3c는 선택).

**Allowed files**:
- `src/autocoin_ai/graph.py`
- `src/autocoin_ai/app.py` (resume guard)
- `tests/test_e2e_wonyotti.py`
- `tests/test_e2e_livermore.py`

**Forbidden**:
- 노드 코드 수정 (이미 잠긴 contract)

**Tasks**:
1. `graph.py`:
   - 새 노드 5개 wire (CONTRACTS §10)
   - 라우팅 함수 4개
2. `app.py:resume()`:
   - 새 흐름의 run이면 `ValueError("resume not supported in MVP")` (§9.2)
3. e2e 테스트:
   - `test_e2e_wonyotti_buy` — examples/wonyotti_buy.json → READY_FOR_BE + user_message 생성
   - `test_e2e_wonyotti_hold` — wonyotti_hold_low_conviction.json → HOLD
   - `test_e2e_livermore_buy` — livermore_buy.json → READY_FOR_BE
   - `test_e2e_ambiguous` — ambiguous_input.json → HOLD_INPUT_AMBIGUOUS

**Acceptance**:
```bash
pytest tests/test_e2e_*.py -v
pytest tests/                # 회귀 + 신규 모두 통과
```

---

## Phase 5 — 코드 품질 + Examples + README

**Precondition**: 4 통과.

**Allowed files**:
- `examples/wonyotti_buy.json` (신규)
- `examples/wonyotti_hold_low_conviction.json` (신규)
- `examples/wonyotti_no_order_size.json` (신규)
- `examples/livermore_buy.json` (신규)
- `examples/livermore_hold_patience.json` (신규)
- `examples/ambiguous_input.json` (신규)
- `examples/DISCLAIMER.md` (신규)
- `README.md` (수정)
- 모든 노드의 docstring (수정)

**Forbidden**:
- 노드 로직 변경 (단순 docstring/주석만)

**Tasks**:
1. examples/ 6개 시나리오 JSON (FIXTURES.md 참조)
2. examples/DISCLAIMER.md — 트레이더 이름 사용 고지
3. README.md:
   - 설치 / 실행 방법
   - 아키텍처 한 줄 그림
   - examples/ 가이드
   - LangSmith 트레이싱 (활성화 시)
4. docstring 정리:
   - 모든 노드 함수
   - 모든 도구 (LLM이 직접 읽음)
   - `Principle`, `TraderMeta`, `Tool` dataclass
5. `basedpyright` 통과 확인

**Acceptance**:
```bash
basedpyright src/                          # 0 errors
pytest tests/                              # 통과
python -m autocoin_ai.cli run examples/wonyotti_buy.json   # 정상 출력
python -m autocoin_ai.cli run examples/livermore_buy.json
```

---

## Phase 6 — 영상 + Git 정리

**Precondition**: 5 통과.

**Tasks**:
1. CLI 실행 화면 영상 1~3분 녹화:
   - `python -m autocoin_ai.cli run examples/wonyotti_buy.json` (READY_FOR_BE)
   - `python -m autocoin_ai.cli run examples/wonyotti_hold_low_conviction.json` (HOLD)
   - `python -m autocoin_ai.cli run examples/livermore_buy.json` (다른 트레이더 비교)
2. 화면에 표시되어야 할 것:
   - decision_trace (stage별)
   - evaluator_review.user_message
   - matched_principle_titles
3. git commit 정리:
   - phase 단위 atomic commit (가능하면)
   - 커밋 메시지에 phase 번호 명시
4. PR 생성 또는 main 푸시

**Acceptance**:
- 영상 파일 확보
- `git log --oneline` 정리됨
- README의 "실행 결과 예시" 섹션에 영상 링크 또는 캡처

---

## 작업 순서 요약 (cheat sheet)

```
0a → 0b → 1 → 2
              ↓
        3a-1 → 3a-2 → 3a-3
                          ↓
                   3b-1 → 3b-2
                              ↓
                          [수면]
                              ↓
                   (opt) 3c
                              ↓
                          4 → 5 → 6
```

각 단계 진입 전 **CONTRACTS.md의 해당 절 + FIXTURES.md의 해당 fixture 확인**.

---

## ralph 운용 권고

각 phase의 ralph 호출:
```
ralph "Phase X 실행. CONTRACTS.md §Y 계약과 tests/fixtures/Z*.json 픽스처 기준.
       acceptance: <pytest 명령>. 다른 파일 수정 금지."
```

ralph가 무한정 돌면:
- fixture가 부정확함 → 사람이 fixture 직접 작성
- contract가 모호함 → CONTRACTS.md 해당 절 보강
- LLM 응답이 비결정적 → temperature=0 + 단위 테스트는 LLM 호출 없이 mock으로
