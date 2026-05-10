# QA 검수 결과 — 검수자 C

## 검수자 정보

- 검수자: 검수자 C
- 담당 범위: QA-C-01 ~ QA-C-06
- 검수 일자: 2026-05-08
- 검수 환경: autocoin-ai 로컬 standalone 실행 (LangGraph, Python 3.13)
- 검수 방법: `autocoin-ai` CLI 직접 실행 + 소스코드 전수 분석 + 스펙 문서(AI.md, DATA.md, TEST_AND_DEMO.md) 대조

---

## 1. 시나리오별 pass/fail 표

| 시나리오 | 목적 | 판정 | 메모 |
|---|---|---|---|
| QA-C-01 | completion payload `execution_result` 검증 | **PASS** | REPORT_READY 정상 |
| QA-C-02 | completion payload `be_rejection_evidence` 검증 | **PASS** | 차단 원인은 evidence_refs 간접 참조 (스펙 허용 범위) |
| QA-C-03 | `NO_ORDER` reporting 검증 | **PASS** | 미실행 stage trace 빈값 — 스펙 명시 부재 FLAG |
| QA-C-04 | `FAILED` 검증 | **PASS** | 실패 원인 notes 기록, report 비어있음 허용 |
| QA-C-05 | 권한 경계 검증 | **PASS** | Binance 호출 없음, LLM 실제 미호출 확인 |
| QA-C-06 | canonical 용어 안정성 검증 | **PASS** | 5개 결과 파일 전체 용어 변형 없음 |

---

## 2. 시나리오별 상세 증빙

### QA-C-01 completion payload `execution_result` 검증

- **시나리오 ID**: QA-C-01
- **입력 payload**: `examples/allowed_request.json` + `examples/execution_result.json`
- **실행 명령**: `autocoin-ai complete examples/allowed_request.json examples/execution_result.json`
- **최종 lifecycle 상태**: `REPORT_READY`
- **decision_trace 핵심**:
  - `execution.final_action` = `REPORT_READY`
  - `execution.reason_codes` = `["ORDER_RESPONSE_VERIFIED"]`
  - `execution.evidence_refs` = `["execution_result.orderId"]`
  - `run_summary.final_action` = `REPORT_READY`
  - `run_summary.reason_codes` = `["FINAL_REPORT_READY"]`
- **verification_checks 핵심**:
  - `execution_result_contract` / stage=`execution` / result=`pass`
- **실패 사유**: 해당 없음
- **증빙 파일**:
  - input: `qa/C/evidence/qa_c01_input_request.json`, `qa/C/evidence/qa_c01_input_completion.json`
  - result: `qa/C/evidence/qa_c01_result.json`

---

### QA-C-02 completion payload `be_rejection_evidence` 검증

- **시나리오 ID**: QA-C-02
- **입력 payload**: `examples/allowed_request.json` + `examples/rejection_result.json`
- **실행 명령**: `autocoin-ai complete examples/allowed_request.json examples/rejection_result.json`
- **최종 lifecycle 상태**: `BE_REJECTED`
- **decision_trace 핵심**:
  - `execution.final_action` = `BE_REJECTED`
  - `execution.reason_codes` = `["BE_REVALIDATION_REJECTED"]`
  - `execution.evidence_refs` = `["be_rejection_evidence"]`
  - `run_summary.final_action` = `BE_REJECTED`
  - `run_summary.reason_codes` = `["BE_REJECTED_REPORTED"]`
- **verification_checks 핵심**:
  - `be_revalidation_result` / stage=`be_revalidation` / result=`fail`
- **기재 사항**: 실제 차단 원인 `MIN_NOTIONAL_NOT_MET`는 `be_rejection_evidence.reason_codes`에 있고, `decision_trace.execution.evidence_refs`가 이를 참조함. trace reason_codes에 직접 기재되지 않으나 스펙 문서에 직접 기재 요구 없음.
- **실패 사유**: 해당 없음
- **증빙 파일**:
  - input: `qa/C/evidence/qa_c02_input_request.json`, `qa/C/evidence/qa_c02_input_completion.json`
  - result: `qa/C/evidence/qa_c02_result.json`

---

### QA-C-03 `NO_ORDER` reporting 검증

- **시나리오 ID**: QA-C-03
- **입력 payload**: `qa/C/evidence/qa_c03_input.json` (quoteOrderQty=0)
- **실행 명령**: `autocoin-ai run qa_c03_input.json`
- **최종 lifecycle 상태**: `NO_ORDER`
- **decision_trace 핵심**:
  - `risk.final_action` = `NO_ORDER`
  - `risk.reason_codes` = `["ORDER_AMOUNT_INVALID"]`
  - evaluator/execution/run_summary는 미실행으로 빈값 (graph.py route_after_risk에서 READY_FOR_BE가 아닐 경우 END로 분기)
- **verification_checks 핵심**:
  - `order_amount_positive` / stage=`risk` / result=`fail`
- **REPORT_READY 덮어쓰기 여부**: 없음. `lifecycle_status = "NO_ORDER"` 유지. `report = {}`.
- **기재 사항 (FLAG)**: NO_ORDER 종료 시 evaluator/execution/run_summary trace가 빈 문자열로 남는 케이스에 대해 스펙 문서가 명시적으로 다루지 않음. 설계 의도에는 부합하나 스펙 보완 검토 권장.
- **실패 사유**: 해당 없음
- **증빙 파일**: `qa/C/evidence/qa_c03_input.json`, `qa/C/evidence/qa_c03_result.json`

---

### QA-C-04 `FAILED` 검증

- **시나리오 ID**: QA-C-04
- **입력 payload**: `qa/C/evidence/qa_c04_input.json` (request_type 필드 누락)
- **실행 명령**: `autocoin-ai run qa_c04_input.json`
- **최종 lifecycle 상태**: `FAILED`
- **decision_trace 핵심**:
  - `policy.final_action` = `FAILED`
  - `policy.reason_codes` = `["INITIAL_REQUEST_CONTRACT_FAILED"]`
  - `policy.notes` = `"Missing fields: request_type"`
  - risk/evaluator/execution/run_summary 미실행 (graph.py route_after_policy에서 FAILED 시 END)
- **verification_checks 핵심**:
  - `initial_request_contract` / stage=`policy` / result=`fail`
- **FAILED / BE_REJECTED / HOLD 분리**: `hold_reason = null`, `be_rejection_evidence = {}` — 혼동 없음.
- **resume 불가 확인**: `app.py resume()`에서 FAILED 상태 resume 시 `ValueError` 발생으로 코드 레벨 차단.
- **실패 사유**: 해당 없음
- **증빙 파일**: `qa/C/evidence/qa_c04_input.json`, `qa/C/evidence/qa_c04_result.json`

---

### QA-C-05 권한 경계 검증

- **시나리오 ID**: QA-C-05
- **입력 payload**: `examples/allowed_request.json`
- **실행 명령**: `autocoin-ai run examples/allowed_request.json`
- **최종 lifecycle 상태**: `READY_FOR_BE`
- **Binance 직접 호출**: 없음. HTTP 클라이언트(requests, httpx, aiohttp, urllib) import 없음. Binance URL 없음.
- **서명/API Key/timestamp 처리**: 없음. GEMINI_API_KEY만 존재하며 이는 Google Gemini용.
- **PASS 사용 범위**: `validators.py`에서 `lifecycle_status == PASS`이면 `AssertionError` 발생으로 코드 강제 차단. PASS는 decision_trace 내 gate 의미로만 사용됨.
- **추가 발견**: `llm.py`의 `create_gemini_client()`가 정의되어 있으나 어떤 노드에서도 호출되지 않음. 모든 판단이 순수 Python 로직으로 동작.
- **실패 사유**: 해당 없음
- **증빙 파일**:
  - input: `qa/C/evidence/qa_c05_input_request.json`
  - result: `qa/C/evidence/qa_c05_result.json`

---

### QA-C-06 canonical 용어 안정성 검증

- **시나리오 ID**: QA-C-06
- **검증 대상**: C-01~C-05 결과 파일 5개 전체
- **최종 lifecycle 상태**: 해당 없음 (다중 결과 비교)
- **필드명 검증**: `run_id`, `policy_context`, `decision_trace`, `verification_checks`, `hold_reason`, `lifecycle_status` — 5개 파일 모두 camelCase 또는 기타 변형 없음.
- **상태값 검증**: `REPORT_READY`, `BE_REJECTED`, `NO_ORDER`, `FAILED`, `READY_FOR_BE`, `PASS` — 하이픈 표기, 소문자 표기 없음.
- **stage 값 검증**: `policy`, `risk`, `evaluator`, `execution`, `be_revalidation` — 허용 집합 외 값 없음.
- **decision_trace 최소 키**: `policy`, `risk`, `evaluator`, `execution`, `run_summary` — 5개 파일 모두 존재.
- **실패 사유**: 해당 없음
- **증빙 파일**: `qa/C/evidence/qa_c01_result.json` ~ `qa_c05_result.json`

---

## 3. 대표 실패 사례

### QA-C-04 — `FAILED` (schema mismatch: request_type 누락)

```json
// 입력 (qa_c04_input.json) — request_type 필드 누락
{
  "run_id": "qa-c-04-failed-001",
  "request_context": {
    "request_id": "req_c04_001",
    "requested_at": "2026-05-08T10:00:00+09:00",
    "user_input": { ... }
  }
}

// 결과
{
  "lifecycle_status": "FAILED",
  "decision_trace": {
    "policy": {
      "final_action": "FAILED",
      "reason_codes": ["INITIAL_REQUEST_CONTRACT_FAILED"],
      "notes": "Missing fields: request_type"
    }
  }
}
```

**확인 사항**: `BE_REJECTED`, `HOLD`와 혼동 없이 `FAILED`로 분리됨. `hold_reason = null`. 이후 resume 불가.

---

## 4. canonical 용어 일치 여부 체크리스트

| 용어 | 스펙 정의 문서 | 결과 파일 사용 여부 | 변형 존재 여부 |
|---|---|---|---|
| `run_id` | DATA.md 2항 | ✓ | 없음 |
| `policy_context` | DATA.md 2항 | ✓ | 없음 |
| `decision_trace` | DATA.md 2항 | ✓ | 없음 |
| `verification_checks` | DATA.md 2항 | ✓ | 없음 |
| `hold_reason` | DATA.md 2항 | ✓ | 없음 |
| `PASS` | DATA.md 10항 | trace에만 ✓ | lifecycle 사용 없음 |
| `READY_FOR_BE` | DATA.md 3항 | ✓ | 없음 |
| `BE_REJECTED` | DATA.md 3항 | ✓ | 없음 |
| `FAILED` | DATA.md 3항 | ✓ | 없음 |
| `REPORT_READY` | DATA.md 3항 | ✓ | 없음 |
| `NO_ORDER` | DATA.md 3항 | ✓ | 없음 |
| `HOLD_REVIEW_REQUIRED` | DATA.md 2항 | 해당 시나리오 없음 (C 담당 외) | — |
| `HOLD_DATA_INSUFFICIENT` | DATA.md 2항 | 해당 시나리오 없음 (C 담당 외) | — |

---

## 5. AI Agent 단독 검수 통과 여부 최종 결론

**검수자 C 담당 시나리오(QA-C-01 ~ QA-C-06) 전체 PASS.**

- completion payload 두 축(`execution_result`, `be_rejection_evidence`) 모두 정상 해석됨
- `REPORT_READY`, `BE_REJECTED`, `NO_ORDER`, `FAILED` 각각 독립적으로 유지되며 상호 혼동 없음
- Binance 직접 호출, 서명, API Key, timestamp 처리 일체 없음
- `PASS`는 trace/gate 의미로만 사용되며 lifecycle에 사용 불가 (코드 레벨 강제)
- 5개 결과 파일 전체에서 canonical 용어 변형 없음

**FLAG 사항 (스펙 보완 권장):**
- NO_ORDER 종료 시 미실행 stage(evaluator, execution, run_summary)의 trace 빈값 처리에 대해 스펙 문서(AI.md, DATA.md)에 명시적 기술 없음. 실제 동작은 설계 의도에 부합하나 문서화 권장.
