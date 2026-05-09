# autocoin-ai · 테스트 픽스처(Fixtures) 명세

> **상태**: 캐노니컬 / 코드 작성 전 필수 산출물
> **작성일**: 2026-05-10
> **연관 문서**: `CONTRACTS.md` (계약 정의), `PHASES.md` (작업 단위)

이 문서는 **각 노드의 입력/출력 state JSON 픽스처**를 명세한다.
**fixture-first 원칙**: 노드 코드 작성 전에 fixture가 작성되어 있어야 한다.
fixture는 **contract의 객관적 검증 도구**다.

---

## §1. 픽스처 디렉토리 구조

```
tests/fixtures/
├── _scenarios/               ← 시나리오별 (세트)
│   ├── wonyotti_buy/
│   │   ├── 00_initial_state.json
│   │   ├── 01_after_intake.json
│   │   ├── 02_after_policy.json
│   │   ├── 03_after_strategy.json
│   │   ├── 04_after_risk_gate.json
│   │   └── 05_after_evaluator.json
│   ├── wonyotti_hold_low_conviction/...
│   ├── wonyotti_no_order_size/...
│   ├── livermore_buy/...
│   ├── livermore_hold_patience/...
│   └── ambiguous_input/...
│
└── _mocks/                   ← LLM 응답 mock
    ├── intake/
    │   ├── buy_aggressive.json
    │   └── ambiguous.json
    ├── strategy/
    │   ├── buy_high_conviction.json
    │   └── hold_no_signal.json
    └── evaluator/
        └── happy_path.json

examples/                     ← 사용자 인풋 (CLI 실행용)
├── wonyotti_buy.json
├── wonyotti_hold_low_conviction.json
├── wonyotti_no_order_size.json
├── livermore_buy.json
├── livermore_hold_patience.json
├── ambiguous_input.json
└── DISCLAIMER.md
```

---

## §2. 6개 시나리오 정의

| # | 이름 | 트레이더 | 입력 | 기대 lifecycle | 발동 룰 |
|---|---|---|---|---|---|
| 1 | wonyotti_buy | wonyotti | "BTC 5만원 사줘" | READY_FOR_BE | 모든 검증 통과 |
| 2 | wonyotti_hold_low_conviction | wonyotti | text + market_snapshot.trend=SIDEWAYS | HOLD_LOW_CONVICTION | strategy conviction < 0.65 |
| 3 | wonyotti_no_order_size | wonyotti | "BTC 200만원 사줘 (보수적)" | NO_ORDER | size > persona.max_order_usd |
| 4 | livermore_buy | livermore | "BTCUSDT 100 USDT 매수" | READY_FOR_BE | 추세 확인 원칙 매칭 |
| 5 | livermore_hold_patience | livermore | "DOGE 사봐" + market trend=SIDEWAYS | HOLD_LOW_CONVICTION | "기다림" 원칙 발동, conviction 낮음 |
| 6 | ambiguous_input | (default) | "비트코인 좀 사봐" | HOLD_INPUT_AMBIGUOUS | ambiguity_score > 0.5 |

---

## §3. 시나리오 1 — wonyotti_buy (Happy Path) 상세

### 3.1 `examples/wonyotti_buy.json` (사용자 입력)
```json
{
  "run_id": "demo_wonyotti_buy_001",
  "request_context": {
    "request_id": "req_demo_wonyotti_001",
    "request_type": "PLACE_ORDER_TEST",
    "requested_at": "2026-05-10T14:00:00+09:00",
    "user_input": {
      "text": "BTC 5만원치 사줘",
      "trader_id": "wonyotti",
      "market_snapshot": {
        "trend": "UP",
        "fetched_at": "2026-05-10T14:00:00+09:00"
      }
    }
  },
  "policy_context": {
    "policy_refs": ["policy.symbol_allowlist", "policy.spot_testnet_only"]
  }
}
```

### 3.2 `tests/fixtures/_scenarios/wonyotti_buy/00_initial_state.json`
`examples/wonyotti_buy.json`과 동일 + `models.ensure_state_shape()`로 빈 필드 채워짐.

### 3.3 `01_after_intake.json` (intake 통과 후)
```json
{
  "run_id": "demo_wonyotti_buy_001",
  "request_context": {...},
  "trader_id": "wonyotti",
  "inferred_persona": "MODERATE",
  "normalized_order_intent": {
    "symbol": "BTCUSDT",
    "side": "BUY",
    "type": "MARKET",
    "quoteOrderQty": "37.04"
  },
  "lifecycle_status": "",
  "decision_trace": {
    "intake": {"reason_codes": ["NL_PARSED"], "evidence_refs": ["request_context.user_input.text"], "final_action": "PASS"},
    "policy": {...empty...},
    "strategy": {...empty...},
    "risk": {...empty...},
    "evaluator": {...empty...},
    "execution": {...empty...},
    "run_summary": {...empty...}
  },
  "verification_checks": [
    {"name": "intake_parse_complete", "stage": "intake", "result": "pass", "evidence_refs": ["normalized_order_intent"]}
  ]
}
```

### 3.4 `02_after_policy.json` (policy 통과 후)
01과 비교한 변경점:
- `policy_context.persona = "MODERATE"`
- `policy_context.persona_bounds` (PERSONA_PROFILES["MODERATE"] 그대로)
- `trader_principles`: 5개 워뇨띠 원칙 dict
- `decision_trace.policy` 채워짐
- `verification_checks` += policy_context_grounded

### 3.5 `03_after_strategy.json` (strategy 통과 후)
변경점:
```json
"llm_proposal": {
  "action": "BUY",
  "size_usd": "37.04",
  "conviction": 0.72,
  "rationale": "추세 확인 원칙에 부합하는 매수 진입.",
  "matched_principle_titles": ["추세 확인 후 진입", "거래량 동반 확인"]
},
"decision_trace.strategy": {
  "reason_codes": ["BUY", "CONVICTION_0.72"],
  "evidence_refs": ["추세 확인 후 진입", "거래량 동반 확인"],
  "final_action": "BUY",
  "notes": "추세 확인 원칙에 부합하는 매수 진입."
}
```

### 3.6 `04_after_risk_gate.json` (risk_gate 통과 후)
변경점:
```json
"risk_assessment": {
  "verdict": "ALLOW",
  "fail_reason": null,
  "tools_called": ["get_balance", "get_volatility"]
},
"risk_tool_calls": [
  {"step": 1, "thought": "", "tool": "get_balance", "args": {"asset": "USDT"}, "result": {"free": "5000.0", ...}},
  {"step": 2, "thought": "", "tool": "get_volatility", "args": {"symbol": "BTCUSDT", "days": 7}, "result": {"atr_pct": 0.045, ...}}
],
"lifecycle_status": "READY_FOR_BE",
"decision_trace.risk": {
  "reason_codes": ["ALL_CHECKS_PASSED"],
  "evidence_refs": ["risk_tool_calls[0]", "risk_tool_calls[1]"],
  "final_action": "PASS"
}
```

### 3.7 `05_after_evaluator.json` (evaluator 통과 후, 최종)
변경점:
```json
"evaluator_review": {
  "summary": "BTCUSDT 매수 제안이 모든 검증을 통과했습니다.",
  "user_message": "워뇨띠의 '추세 확인 후 진입' 원칙에 부합하며, 잔고와 변동성 모두 정상 범위입니다. BE 재검증으로 핸드오프됩니다.",
  "reason_codes": ["EVIDENCE_SUMMARIZED", "RISK_GATE_PASSED"],
  "schema_warnings": []
},
"decision_trace.evaluator": {
  "reason_codes": ["EVIDENCE_SUMMARIZED", "RISK_GATE_PASSED"],
  "evidence_refs": ["evaluator_review"],
  "final_action": "READY_FOR_BE"
},
"decision_trace.run_summary": {
  "reason_codes": ["RUN_COMPLETE"],
  "evidence_refs": ["evaluator_review"],
  "final_action": "READY_FOR_BE"
}
```

---

## §4. 시나리오 2 — wonyotti_hold_low_conviction

### 4.1 사용자 입력
```json
{
  "run_id": "demo_wonyotti_hold_002",
  "request_context": {
    "request_id": "req_demo_wonyotti_002",
    "request_type": "PLACE_ORDER_TEST",
    "requested_at": "2026-05-10T14:05:00+09:00",
    "user_input": {
      "text": "BTC 5만원치 사줘",
      "trader_id": "wonyotti",
      "market_snapshot": {"trend": "SIDEWAYS"}
    }
  },
  "policy_context": {"policy_refs": ["policy.symbol_allowlist", "policy.spot_testnet_only"]}
}
```

### 4.2 흐름
- intake → policy → strategy
- strategy 단계에서 LLM이 SIDEWAYS 추세 인지 → **conviction = 0.50** (MODERATE.min_conviction = 0.65 미달)
- risk_gate 검증 #2 (conviction < min) → `HOLD_LOW_CONVICTION`
- evaluator 실행 → `user_message` 생성

### 4.3 최종 lifecycle
- `lifecycle_status = "HOLD"`
- `hold_reason = "HOLD_LOW_CONVICTION"`
- `evaluator_review.user_message`: "워뇨띠 원칙 중 추세 확인이 모호해 conviction이 낮습니다. 추세가 명확해질 때까지 보류를 권합니다."

---

## §5. 시나리오 3 — wonyotti_no_order_size (한도 초과)

### 5.1 사용자 입력
```json
{
  "run_id": "demo_wonyotti_no_order_003",
  "request_context": {
    "request_id": "req_demo_wonyotti_003",
    "request_type": "PLACE_ORDER_TEST",
    "requested_at": "2026-05-10T14:10:00+09:00",
    "user_input": {
      "text": "BTC 200만원치 사줘 보수적으로",
      "trader_id": "wonyotti"
    }
  },
  "policy_context": {"policy_refs": ["policy.symbol_allowlist", "policy.spot_testnet_only"]}
}
```

### 5.2 흐름
- intake: `inferred_persona = "CONSERVATIVE"` (발화 override)
- policy: `persona_bounds.max_order_usd = "100"`
- strategy: `size_usd = "1481.48"` (200만원 환산)
- risk_gate 검증 #3 (size > max) → `NO_ORDER`

### 5.3 최종
- `lifecycle_status = "NO_ORDER"`
- `risk_assessment.fail_reason = "SIZE_EXCEEDS_PERSONA"`
- `evaluator_review.user_message`: "보수적 페르소나의 단일 주문 한도 $100를 초과합니다. 금액을 줄이거나 페르소나를 조정해주세요."

---

## §6. 시나리오 4 — livermore_buy (다른 트레이더)

### 6.1 사용자 입력
```json
{
  "run_id": "demo_livermore_buy_004",
  "request_context": {
    "request_id": "req_demo_livermore_004",
    "request_type": "PLACE_ORDER_TEST",
    "requested_at": "2026-05-10T14:15:00+09:00",
    "user_input": {
      "text": "BTCUSDT 100 USDT 매수",
      "trader_id": "livermore"
    }
  },
  "policy_context": {"policy_refs": ["policy.symbol_allowlist", "policy.spot_testnet_only"]}
}
```

### 6.2 흐름
- intake: `trader_id = "livermore"`, `inferred_persona = "MODERATE"` (livermore.default)
- policy: livermore 원칙 retrieval (추세 방향, 강한 종목, 손실 제한)
- strategy: BUY conviction 0.78 — `matched_principle_titles = ["추세 방향으로만 거래", "강한 종목만 선택"]`
- risk_gate: 모두 통과 → READY_FOR_BE
- evaluator: livermore 원칙 인용

### 6.3 데모 가치
**같은 시장 상태에서 워뇨띠 vs 리버모어가 다른 원칙을 인용**한다는 게 보임. 영상 시연 핵심.

---

## §7. 시나리오 5 — livermore_hold_patience (기다림 원칙)

### 7.1 사용자 입력
```json
{
  "run_id": "demo_livermore_patience_005",
  "request_context": {
    "request_id": "req_demo_livermore_005",
    "request_type": "PLACE_ORDER_TEST",
    "requested_at": "2026-05-10T14:20:00+09:00",
    "user_input": {
      "text": "DOGE 좀 사봐",
      "trader_id": "livermore",
      "market_snapshot": {"trend": "SIDEWAYS"}
    }
  },
  "policy_context": {"policy_refs": ["policy.symbol_allowlist", "policy.spot_testnet_only"]}
}
```

### 7.2 흐름
- intake: ambiguity 약간 (size 미명시 → 기본값 시도)
- policy: livermore의 "기다림도 전략" 원칙 retrieval
- strategy: conviction = 0.45 (기다림 원칙 발동) → action = "HOLD"
- risk_gate 검증 #1 (action == HOLD) → `HOLD_LOW_CONVICTION`
- evaluator: livermore.patience 원칙 인용

---

## §8. 시나리오 6 — ambiguous_input

### 8.1 사용자 입력
```json
{
  "run_id": "demo_ambiguous_006",
  "request_context": {
    "request_id": "req_demo_amb_006",
    "request_type": "PLACE_ORDER_TEST",
    "requested_at": "2026-05-10T14:25:00+09:00",
    "user_input": {
      "text": "비트코인 좀 사봐"
    }
  },
  "policy_context": {"policy_refs": ["policy.symbol_allowlist", "policy.spot_testnet_only"]}
}
```

### 8.2 흐름
- intake: ambiguity_score = 0.8 → `HOLD_INPUT_AMBIGUOUS`
- policy / strategy / risk_gate: 스킵 (라우팅에서 evaluator로 직행)
- evaluator: "금액과 매매 의도가 명확하지 않습니다" user_message

### 8.3 최종
- `lifecycle_status = "HOLD"`
- `hold_reason = "HOLD_INPUT_AMBIGUOUS"`

---

## §9. LLM Mock 픽스처 (`_mocks/`)

단위 테스트는 실 LLM 호출 없이 동작해야 함. 다음 mock 응답 사용:

### 9.1 `_mocks/intake/buy_aggressive.json`
```json
{
  "symbol": "BTCUSDT",
  "side": "BUY",
  "type": "MARKET",
  "size_usd": "37.04",
  "trader_id": "wonyotti",
  "inferred_persona": "AGGRESSIVE",
  "persona_override_reason": "공격적으로 명시",
  "ambiguity_score": 0.0
}
```

### 9.2 `_mocks/intake/ambiguous.json`
```json
{
  "symbol": "BTCUSDT",
  "side": "BUY",
  "type": "MARKET",
  "size_usd": "",
  "trader_id": "",
  "inferred_persona": "MODERATE",
  "persona_override_reason": "",
  "ambiguity_score": 0.8
}
```

### 9.3 `_mocks/strategy/buy_high_conviction.json`
```json
{
  "action": "BUY",
  "size_usd": "37.04",
  "conviction": 0.72,
  "rationale": "추세 확인 원칙에 부합하는 매수 진입.",
  "matched_principle_titles": ["추세 확인 후 진입", "거래량 동반 확인"]
}
```

### 9.4 `_mocks/strategy/hold_no_signal.json`
```json
{
  "action": "HOLD",
  "size_usd": "0",
  "conviction": 0.40,
  "rationale": "추세가 명확하지 않아 진입 보류.",
  "matched_principle_titles": ["추세 확인 후 진입"]
}
```

### 9.5 `_mocks/evaluator/happy_path.json`
```json
{
  "summary": "BTCUSDT 매수 제안이 모든 검증을 통과했습니다.",
  "user_message": "워뇨띠의 '추세 확인 후 진입' 원칙에 부합하며 잔고와 변동성 모두 정상 범위입니다.",
  "reason_codes": ["EVIDENCE_SUMMARIZED", "RISK_GATE_PASSED"],
  "schema_warnings": []
}
```

---

## §10. 테스트에서 mock 주입 방법

```python
# tests/conftest.py
import json
from pathlib import Path
from unittest.mock import patch

@pytest.fixture
def mock_llm_intake_buy(monkeypatch):
    fixture = json.loads(Path("tests/fixtures/_mocks/intake/buy_aggressive.json").read_text())
    def fake_generate(prompt, response_schema, system_instruction=""):
        return fixture
    monkeypatch.setattr("autocoin_ai.llm.gemini_generate", fake_generate)

# tests/test_intake.py
def test_intake_text_buy(mock_llm_intake_buy):
    state = json.loads(Path("tests/fixtures/_scenarios/wonyotti_buy/00_initial_state.json").read_text())
    out = intake_node(state)
    expected = json.loads(Path("tests/fixtures/_scenarios/wonyotti_buy/01_after_intake.json").read_text())
    assert out["normalized_order_intent"] == expected["normalized_order_intent"]
    assert out["trader_id"] == "wonyotti"
```

---

## §11. 픽스처 작성 우선순위

**Phase 0a 시작 전 작성 필수**:
1. `examples/wonyotti_buy.json` (입력 1개)
2. `tests/fixtures/_scenarios/wonyotti_buy/00_initial_state.json` ~ `05_after_evaluator.json` (6개)
3. `tests/fixtures/_mocks/intake/buy_aggressive.json`
4. `tests/fixtures/_mocks/strategy/buy_high_conviction.json`
5. `tests/fixtures/_mocks/evaluator/happy_path.json`

**Phase 3a-1 (intake) 시작 전**:
- `_mocks/intake/ambiguous.json`
- `_scenarios/ambiguous_input/00_initial_state.json` ~ `01_after_intake.json` (intake에서 종료)

**Phase 3a-3 (strategy) 시작 전**:
- `_mocks/strategy/hold_no_signal.json`
- `_scenarios/wonyotti_hold_low_conviction/00`~`03`

**Phase 4 (e2e) 시작 전**:
- 시나리오 4, 5, 6 모두 `00_initial_state.json` (입력만)

---

## §12. 픽스처 검증 스크립트 (선택)

```python
# scripts/validate_fixtures.py
"""모든 _scenarios/ 픽스처가 schema와 일치하는지 검증."""
from autocoin_ai.models import ensure_state_shape
from autocoin_ai.validators import assert_contract_state
from pathlib import Path
import json

def main():
    fixtures = Path("tests/fixtures/_scenarios").rglob("*.json")
    for f in fixtures:
        state = json.loads(f.read_text())
        normalized = ensure_state_shape(state)
        try:
            assert_contract_state(normalized)
            print(f"OK: {f}")
        except AssertionError as e:
            print(f"FAIL: {f} — {e}")

if __name__ == "__main__":
    main()
```

`make test-fixtures` 또는 CI에서 호출.
