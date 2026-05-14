# autocoin-ai 데이터 계약

## 문서 목적

이 문서는 `autocoin-ai` 서브프로젝트에서 FE, BE, AI가 함께 맞춰 써야 하는 최소 canonical 필드와 상태 용어를 정리한다. 전체 API 상세를 재작성하지 않고, AI 중심 경계에서 꼭 필요한 계약만 남긴다.

## 관련 문서

- 진입점: `README.md`
- 범위와 요구사항: `SPEC.md`
- 책임 경계: `ARCHITECTURE.md`
- AI 계층 상세: `AI.md`
- FE boundary 계약: `FE.md`
- BE boundary 계약: `BE.md`
- 이 문서: `DATA.md`
- 테스트 기준: `TEST_AND_DEMO.md`

## 1. 고정 엔드포인트

| 항목 | 값 |
|---|---|
| REST Base URL | `https://testnet.binance.vision/api` |
| WebSocket Streams | `wss://stream.testnet.binance.vision/ws` |
| WebSocket API | `wss://ws-api.testnet.binance.vision/ws-api/v3` |

## 2. canonical 용어

| 용어 | 의미 |
|---|---|
| `run_id` | 하나의 주문 테스트 AI run 식별자 |
| `policy_context` | 정책 artifact 기반 grounding 컨텍스트 |
| `decision_trace` | 단계별 판단 근거와 final action 기록 |
| `verification_checks` | 단계별 검증 결과를 append 하는 공통 체크 목록 |
| `hold_reason` | `HOLD` 상태의 세부 원인 |
| `trader_id` | 트레이더 스타일 식별자 (예: `wonyotti`, `livermore`) |
| `inferred_persona` | intake 결정 페르소나 (`CONSERVATIVE` / `MODERATE` / `AGGRESSIVE`) |
| `persona_override_reason` | 발화 명시 단어로 persona가 override된 사유 (선택) |
| `trader_principles` | RAG retrieval된 트레이더 원칙 목록 |
| `normalized_order_intent` | intake가 정규화한 주문 의도 dict |
| `llm_proposal` | strategy 노드의 LLM 제안 |
| `risk_assessment` | risk_gate 판정 결과 |
| `risk_tool_calls` | risk_gate가 호출한 도구 기록 (append-only) |
| `evaluator_review` | evaluator가 생성한 최종 사용자 리포트 |
| `NO_ORDER` | 신규 주문 생성 없이 종료 |
| `BE_REJECTED` | AI proposal 이후 BE 재검증에서 차단 |
| `FAILED` | schema mismatch 또는 기술 실패로 정상 리포트 계약을 만들지 못한 상태 |
| `REPORT_READY` | 사용자용 최종 설명이 준비된 상태 |
| `HOLD_INPUT_AMBIGUOUS` | 자연어 입력 모호도 초과로 인한 보류 (`ambiguity_score > 0.5`) |
| `HOLD_LOW_CONVICTION` | LLM proposal conviction 미달로 인한 보류 |
| `HOLD_RISK_AGENT_FLAGGED` | 변동성 또는 집중 리스크 임계 초과로 인한 보류 |
| `HOLD_DATA_INSUFFICIENT` | 데이터 부족 또는 필수 입력 부족으로 인한 보류 |
| `HOLD_REVIEW_REQUIRED` | 사람 승인 또는 운영 검토가 필요한 보류 |
| `READY_FOR_BE` | AI proposal이 BE deterministic revalidation으로 handoff 된 lifecycle 상태 |

## 3. lifecycle_status 최소 집합

| 값 | 의미 |
|---|---|
| `HOLD` | 사람 검토 또는 데이터 보완 대기. `hold_reason`으로 세분화 |
| `READY_FOR_BE` | AI->BE handoff 완료 |
| `NO_ORDER` | 신규 주문 없음 |
| `BE_REJECTED` | BE 재검증 차단 |
| `FAILED` | schema mismatch 또는 복구 불가 기술 실패 |
| `REPORT_READY` | 최종 사용자 보고 준비 완료 |

`HOLD`의 `hold_reason` 값:

| 값 | 발생 시점 |
|---|---|
| `HOLD_INPUT_AMBIGUOUS` | intake — `ambiguity_score > 0.5` |
| `HOLD_LOW_CONVICTION` | risk_gate — LLM proposal conviction 미달 |
| `HOLD_RISK_AGENT_FLAGGED` | risk_gate — 변동성/집중 리스크 임계 초과 |
| `HOLD_DATA_INSUFFICIENT` | risk_gate — 잔고 부족 또는 데이터 누락 |
| `HOLD_REVIEW_REQUIRED` | BE 또는 정책 — 수동 운영 검토 필요 |

## 4. 최초 요청 계약

Agentic MVP (자연어 모드):

```json
{
  "request_context": {
    "request_id": "req_001",
    "request_type": "PLACE_ORDER_TEST",
    "requested_at": "2026-05-10T10:00:00+09:00",
    "user_input": {
      "raw_text": "공격적으로 비트코인 5만원어치 사줘"
    }
  }
}
```

기존 dict 모드 (회귀 호환):

```json
{
  "request_context": {
    "request_id": "req_001",
    "request_type": "PLACE_ORDER_TEST",
    "requested_at": "2026-05-07T10:00:00+09:00",
    "user_input": {
      "symbol": "BTCUSDT",
      "side": "BUY",
      "type": "MARKET",
      "quoteOrderQty": "50"
    }
  }
}
```

`request_context`는 immutable envelope로 취급한다. `user_input.raw_text`가 있으면 intake 노드가 LLM 파싱 모드로 처리한다. 없으면 기존 dict 모드를 유지한다.

## 5. 최소 상태 예시

```json
{
  "run_id": "airun_001",
  "policy_context": {
    "policy_refs": ["policy.symbol_allowlist"]
  },
  "decision_trace": {
    "risk": {
      "reason_codes": ["STALE_MARKET_SNAPSHOT"],
      "final_action": "HOLD"
    }
  },
  "verification_checks": [
    {
      "name": "market_snapshot_freshness",
      "result": "fail"
    }
  ],
  "hold_reason": "HOLD_DATA_INSUFFICIENT"
}
```

## 6. 최소 trace 계약

`decision_trace`는 자유 서술만으로 끝나면 안 되고, 최소한 다음 구조를 유지한다.

```json
{
  "policy": {
    "reason_codes": ["ORDER_INTENT_NORMALIZED"],
    "evidence_refs": ["policy_context.policy_refs[0]"],
    "final_action": "PASS"
  },
  "risk": {
    "reason_codes": ["ALL_CHECKS_PASSED"],
    "evidence_refs": ["verification_checks[1]"],
    "final_action": "PASS"
  },
  "evaluator": {
    "reason_codes": ["EVIDENCE_SUFFICIENT"],
    "evidence_refs": ["verification_checks[2]"],
    "final_action": "PASS"
  },
  "execution": {
    "reason_codes": ["ORDER_RESPONSE_VERIFIED"],
    "evidence_refs": ["execution_result.orderId"],
    "final_action": "REPORT_READY"
  },
  "run_summary": {
    "final_action": "REPORT_READY"
  }
}
```

`PASS`는 `decision_trace` 또는 gate 의미로만 사용하고, lifecycle 필드에는 쓰지 않는다. lifecycle handoff는 `READY_FOR_BE`로 구분한다.

`decision_trace`의 canonical container는 stage-keyed 구조이며, 최소 키는 `policy`, `risk`, `evaluator`, `execution`, `run_summary`다.

## 7. verification_checks 최소 shape

```json
{
  "name": "policy_symbol_allowed",
  "stage": "policy",
  "result": "pass",
  "evidence_refs": ["policy_context.policy_refs[0]"]
}
```

- `verification_checks`는 append-only로 누적한다.
- 각 stage는 자기 stage의 entry만 추가한다.
- 전체 stage 집합은 `intake`, `policy`, `strategy`, `risk`, `evaluator`, `execution`, `be_revalidation`이다.
- 기존 테스트 회귀 보호를 위해 `intake`와 `strategy`는 optional이며 기존 24개 테스트는 영향 없다.

## 8. 최소 resume payload

```json
{
  "run_id": "airun_001",
  "resume_reason": "USER_APPROVED_ORDER",
  "patch_fields": {
    "approval": {
      "approved": true
    }
  }
}
```

## 9. BE->AI completion payload 계약

### 9.1 execution_result

```json
{
  "execution_result": {
    "status": "FILLED",
    "orderId": 123456789,
    "clientOrderId": "demo-order-001"
  }
}
```

### 9.2 be_rejection_evidence

```json
{
  "be_rejection_evidence": {
    "reason_codes": ["MIN_NOTIONAL_NOT_MET"],
    "notes": "Deterministic revalidation blocked the order before submit."
  }
}
```

성공 축에서는 `execution_result`, 차단 축에서는 `be_rejection_evidence`를 사용한다.

## 10. 상태 해석 규칙

- `PASS`는 내부 gate 통과 제안이다.
- `PASS`는 최종 실행 완료나 체결 완료가 아니다.
- `READY_FOR_BE`는 lifecycle handoff 상태다.
- BE가 차단하면 최종 구분 값은 `BE_REJECTED`다.
- schema mismatch, 필수 필드 결손, 복구 불가 기술 실패는 `FAILED`로 구분한다.
- `HOLD`의 의미는 `hold_reason` 없이는 완결되지 않는다.
- 최종 사용자 보고 준비 상태는 `REPORT_READY`다.
- `NO_ORDER`, `BE_REJECTED`, `FAILED`는 lifecycle 종료 의미를 유지할 수 있고, 사용자 설명 payload는 별도로 생성될 수 있다.

## 11. cadence event 최소 집합

- `request accepted`
- `policy retrieval complete`
- `policy complete`
- `risk gate complete`
- `evaluator complete`
- `BE revalidation complete`
- `final report ready`

`HOLD`에서는 cadence가 멈추고 resume을 기다린다. `FAILED`에서는 cadence가 terminal failure로 종료된다.

## 12. casing 규칙

- REST 심볼 예시는 `BTCUSDT`, `ETHUSDT`처럼 대문자를 사용한다.
- stream 이름 예시는 `btcusdt@ticker`처럼 소문자를 사용한다.

## 13. boundary contract

- FE는 이 필드들을 표시만 하고, Binance 직접 호출과 서명을 하지 않는다.
- BE는 `policy_context` 구성, Binance Testnet 호출, deterministic 재검증, 최종 실행 또는 `BE_REJECTED` 생성을 담당한다.
- AI는 `decision_trace`, `hold_reason`, run 상태 해석을 담당한다.

## 14. 참조 기준

- 범위와 요구사항은 `SPEC.md`
- 상태 흐름과 run 규칙은 `AI.md`
- 전체 구조와 cadence는 `ARCHITECTURE.md`
- 시나리오 검증은 `TEST_AND_DEMO.md`
