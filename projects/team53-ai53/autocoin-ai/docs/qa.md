# autocoin-ai AI Agent 단독 QA 계획

## 문서 목적

이 문서는 FE, BE와 아직 통합되지 않은 `autocoin-ai` AI Agent 프로그램을 사람 3명이 분담 검수할 수 있도록 standalone QA 시나리오를 정의한다. 범위는 로컬 문서 세트가 정의한 AI Agent 계약만 다루며, 실제 Binance 호출, FE UI 동작, BE 통합 동작은 포함하지 않는다.

## 관련 문서

- 범위와 요구사항: `SPEC.md`
- 전체 흐름: `ARCHITECTURE.md`
- FE boundary 계약: `FE.md`
- BE boundary 계약: `BE.md`
- AI 계층 규칙: `AI.md`
- 데이터와 상태 계약: `DATA.md`
- 테스트와 데모 기준: `TEST_AND_DEMO.md`

## 1. QA 기본 원칙

- 이 문서는 **AI Agent 단독 검수**만 다룬다.
- FE 화면, 실제 Binance 제출, 실제 서명, 실제 WebSocket 연결은 테스트 대상이 아니다.
- 모든 검수는 로컬 문서 기준의 canonical 용어를 그대로 사용한다.
- 특히 `PASS`, `READY_FOR_BE`, `HOLD_REVIEW_REQUIRED`, `HOLD_DATA_INSUFFICIENT`, `BE_REJECTED`, `FAILED`, `REPORT_READY`, `NO_ORDER`를 혼용하면 실패다.
- 각 검수자는 자기 담당 시나리오마다 **입력**, **기대 상태**, **남아야 하는 trace/check**, **증빙**을 기록해야 한다.

## 2. 검수 준비물

- AI Agent 실행 환경 또는 테스트 harness
- 요청 payload를 직접 넣을 수 있는 방법
- run 결과 JSON 또는 로그를 저장할 수 있는 방법
- 각 시나리오별 증빙 캡처 파일 또는 로그 경로

## 3. 증빙 기록 규칙

각 시나리오마다 최소한 다음 항목을 남긴다.

- 시나리오 ID
- 검수자 이름
- 입력 payload
- 최종 lifecycle 상태
- `decision_trace` 핵심 내용
- `verification_checks` 핵심 내용
- 실패 시 원인 메모
- 증빙 파일 경로 또는 로그 발췌

## 4. 3인 분담 원칙

### 검수자 A — 입력 / 정책 / 리스크 게이트

검수자 A는 **초기 요청 계약**, **정규화**, **policy grounding**, **risk gate**가 올바른지 본다.

### 검수자 B — Hold / Evaluator / Resume

검수자 B는 **보류 흐름**, **evaluator/reflection**, **same `run_id` resume**가 올바른지 본다.

### 검수자 C — Completion / Reporting / Failure / Boundary

검수자 C는 **completion payload**, **reporting semantics**, **실패 축**, **권한 경계**가 올바른지 본다.

## 5. 시나리오 목록

### QA-A-01 최초 요청 계약 검증

- 담당: 검수자 A
- 목적: 최초 요청이 `request_context` 최소 shape를 만족하는지 확인
- 입력:
  - `request_id`
  - `request_type`
  - `requested_at`
  - `user_input`
- 절차:
  1. 최소 필드를 모두 가진 요청을 넣는다.
  2. run 시작 시점 결과를 확인한다.
- 기대 결과:
  - `request_context`가 그대로 보존된다.
  - 필수 필드 누락 없이 다음 단계로 진행 가능하다.
- 확인 포인트:
  - `request_context`가 immutable envelope로 해석되는지
- 증빙:
  - 입력 payload
  - run 시작 직후 상태/로그

### QA-A-02 정규화 시 immutable 보존 검증

- 담당: 검수자 A
- 목적: Policy/Planning 단계가 `request_context`를 수정하지 않고 정규화 결과만 추가하는지 확인
- 절차:
  1. 정상 주문 테스트 요청을 넣는다.
  2. Policy/Planning 단계 산출물을 확인한다.
- 기대 결과:
  - 원래 `request_context`는 변하지 않는다.
  - `normalized_order_intent`, `decision_trace.policy`만 추가된다.
- 증빙:
  - 입력 대비 출력 diff

### QA-A-03 policy grounding 검증

- 담당: 검수자 A
- 목적: `policy_context`가 trace와 함께 연결되는지 확인
- 절차:
  1. 허용 정책 근거가 있는 요청을 사용한다.
  2. Policy 단계 trace를 확인한다.
- 기대 결과:
  - `policy_context`가 사용된다.
  - `decision_trace.policy.evidence_refs`에 정책 근거가 남는다.
  - `verification_checks`에 policy stage entry가 append 된다.
- 증빙:
  - `decision_trace.policy`
  - `verification_checks`

### QA-A-04 decision_trace container shape 검증

- 담당: 검수자 A
- 목적: `decision_trace`가 flat object가 아니라 stage-keyed canonical container인지 확인
- 절차:
  1. 정상 흐름 또는 부분 진행 흐름을 만든다.
  2. 반환된 `decision_trace` 구조를 확인한다.
- 기대 결과:
  - 최소 key 집합: `policy`, `risk`, `evaluator`, `execution`, `run_summary`
  - 각 stage key 아래에 `reason_codes`, `evidence_refs`, `final_action`이 있다.
- 증빙:
  - `decision_trace` 전체 JSON

### QA-A-05 Risk Gate PASS / READY_FOR_BE 분리 검증

- 담당: 검수자 A
- 목적: `PASS`와 `READY_FOR_BE`가 같은 값으로 취급되지 않는지 확인
- 절차:
  1. 정책과 규칙을 모두 만족하는 요청을 넣는다.
  2. Risk/Evaluator 이후 상태와 trace를 확인한다.
- 기대 결과:
  - trace 또는 gate 차원에서 `PASS`가 남는다.
  - lifecycle 상태는 `READY_FOR_BE`다.
  - 두 값이 혼동되지 않는다.
- 증빙:
  - lifecycle 상태
  - `decision_trace.risk`, `decision_trace.evaluator`

### QA-A-06 `HOLD_REVIEW_REQUIRED` 검증

- 담당: 검수자 A
- 목적: 사람 승인 필요 흐름이 일반 실패가 아니라 review hold로 분기되는지 확인
- 절차:
  1. 사람 승인 필요 조건의 요청을 사용한다.
  2. 결과 상태와 hold reason을 확인한다.
- 기대 결과:
  - lifecycle이 `HOLD`다.
  - `hold_reason=HOLD_REVIEW_REQUIRED`다.
- 증빙:
  - 최종 상태
  - `hold_reason`

### QA-B-01 `HOLD_DATA_INSUFFICIENT` 검증

- 담당: 검수자 B
- 목적: 데이터 부족이 generic failure가 아니라 data hold로 분리되는지 확인
- 절차:
  1. 필수 데이터 또는 freshness가 부족한 상황을 만든다.
  2. 결과 상태를 확인한다.
- 기대 결과:
  - lifecycle이 `HOLD`다.
  - `hold_reason=HOLD_DATA_INSUFFICIENT`다.
- 증빙:
  - 최종 상태
  - `decision_trace.risk`

### QA-B-02 evaluator/reflection 차단 검증

- 담당: 검수자 B
- 목적: 초기 단계가 통과해도 evaluator가 근거 부족이면 승격을 막는지 확인
- 절차:
  1. 애매한 근거를 가진 요청을 만든다.
  2. Evaluator 결과를 확인한다.
- 기대 결과:
  - evaluator가 그대로 통과시키지 않는다.
  - `READY_FOR_BE` 승격이 막히거나 hold/no-order로 남는다.
- 증빙:
  - `decision_trace.evaluator`
  - evaluator stage `verification_checks`

### QA-B-03 verification_checks append-only 검증

- 담당: 검수자 B
- 목적: stage별 검증 결과가 누적되고 덮어써지지 않는지 확인
- 절차:
  1. 여러 단계를 거치는 요청을 사용한다.
  2. 각 단계 후 `verification_checks`를 비교한다.
- 기대 결과:
  - 이전 entry가 사라지지 않는다.
  - 새 stage entry만 append 된다.
  - stage 값은 `policy`, `risk`, `evaluator`, `execution`, `be_revalidation` 중 하나다.
- 증빙:
  - 단계별 `verification_checks` 스냅샷

### QA-B-04 same `run_id` resume 검증

- 담당: 검수자 B
- 목적: hold 후 같은 `run_id`로 resume 되는지 확인
- 절차:
  1. hold 상태를 만든다.
  2. patchable 필드만 보완해서 같은 `run_id`로 resume 한다.
- 기대 결과:
  - `run_id`가 유지된다.
  - 이전 `decision_trace`, `verification_checks`가 보존된다.
  - 보완된 결과만 추가된다.
- 증빙:
  - resume 전/후 payload
  - resume 전/후 trace/check diff

### QA-B-05 resume은 자동 승인 아님 검증

- 담당: 검수자 B
- 목적: resume 자체가 바로 승인/실행을 의미하지 않는지 확인
- 절차:
  1. hold 상태에서 resume을 수행한다.
  2. 결과 상태와 trace를 확인한다.
- 기대 결과:
  - resume만으로 `READY_FOR_BE` 또는 최종 성공이 보장되지 않는다.
  - 필요한 검증이 다시 수행된다.
- 증빙:
  - resume 후 stage별 결과

### QA-C-01 completion payload `execution_result` 검증

- 담당: 검수자 C
- 목적: 성공 축 completion payload를 AI가 해석할 수 있는지 확인
- 절차:
  1. `execution_result`를 가진 completion payload를 넣는다.
  2. Execution/Report 결과를 확인한다.
- 기대 결과:
  - `decision_trace.execution`이 완성된다.
  - `decision_trace.run_summary`가 완성된다.
  - reporting 상태가 `REPORT_READY`로 정리된다.
- 증빙:
  - completion payload
  - execution trace

### QA-C-02 completion payload `be_rejection_evidence` 검증

- 담당: 검수자 C
- 목적: BE 차단이 일반 실패와 분리되는지 확인
- 절차:
  1. `be_rejection_evidence`를 가진 completion payload를 넣는다.
  2. AI 결과를 확인한다.
- 기대 결과:
  - 최종 lifecycle 의미가 `BE_REJECTED`다.
  - rejection reason이 trace에 반영된다.
- 증빙:
  - completion payload
  - `decision_trace.execution`
  - `decision_trace.run_summary`

### QA-C-03 `NO_ORDER` reporting 검증

- 담당: 검수자 C
- 목적: no-trade 결과가 `REPORT_READY`에 덮어써지지 않는지 확인
- 절차:
  1. 명백한 금지 요청 또는 필수 입력 누락 요청을 넣는다.
  2. 결과 상태와 설명 payload를 확인한다.
- 기대 결과:
  - lifecycle 종료 의미는 `NO_ORDER`다.
  - 설명 payload는 별도로 존재할 수 있다.
  - lifecycle 자체가 `REPORT_READY`로 바뀌면 안 된다.
- 증빙:
  - 최종 상태
  - 설명 payload

### QA-C-04 `FAILED` 검증

- 담당: 검수자 C
- 목적: schema mismatch 또는 기술 실패가 hold/reject와 분리되는지 확인
- 절차:
  1. 필수 필드 누락 또는 schema mismatch 상황을 만든다.
  2. 결과 상태를 확인한다.
- 기대 결과:
  - lifecycle은 `FAILED`다.
  - `BE_REJECTED`나 `HOLD`와 혼동되지 않는다.
- 증빙:
  - 실패 입력
  - 최종 상태
  - 실패 사유 로그

### QA-C-05 권한 경계 검증

- 담당: 검수자 C
- 목적: AI Agent 단독 프로그램이 금지된 책임을 침범하지 않는지 확인
- 절차:
  1. 실행/설정/로그를 검토한다.
  2. 문서 기준과 실제 동작을 비교한다.
- 기대 결과:
  - Binance 직접 호출 없음
  - 서명/API Key/timestamp 처리 없음
  - 최종 실행 승인처럼 `PASS`를 설명하지 않음
- 증빙:
  - 실행 로그
  - 호출 기록 또는 코드/도구 사용 흔적

### QA-C-06 canonical 용어 안정성 검증

- 담당: 검수자 C
- 목적: 로컬 문서의 핵심 용어가 실제 결과에서도 그대로 유지되는지 확인
- 절차:
  1. 여러 시나리오 결과를 비교한다.
  2. 상태명과 필드명을 대조한다.
- 기대 결과:
  - `run_id`, `policy_context`, `decision_trace`, `verification_checks`, `hold_reason`
  - `PASS`, `READY_FOR_BE`, `BE_REJECTED`, `FAILED`, `REPORT_READY`, `NO_ORDER`
  - 위 용어가 임의로 변형되지 않는다.
- 증빙:
  - 결과 JSON 모음

## 6. 3인 최종 분담표

| 검수자 | 담당 시나리오 | 핵심 초점 |
|---|---|---|
| 검수자 A | QA-A-01 ~ QA-A-06 | 입력 계약, 정책 grounding, risk gate, hold reason 분리 |
| 검수자 B | QA-B-01 ~ QA-B-05 | evaluator/reflection, verification_checks, same `run_id` resume |
| 검수자 C | QA-C-01 ~ QA-C-06 | completion payload, reporting semantics, FAILED, boundary 검증 |

## 7. 공통 판정 규칙

- 한 시나리오라도 canonical 상태/필드명이 틀리면 실패다.
- `PASS`를 최종 승인처럼 설명하면 실패다.
- `READY_FOR_BE`를 lifecycle handoff가 아닌 최종 성공처럼 설명하면 실패다.
- `HOLD_REVIEW_REQUIRED`, `HOLD_DATA_INSUFFICIENT`, `BE_REJECTED`, `FAILED`, `NO_ORDER`가 서로 섞이면 실패다.
- 같은 `run_id` resume에서 immutable 필드가 바뀌면 실패다.

## 8. 검수 완료 산출물

검수 종료 후 사람 3명은 다음 산출물을 남긴다.

- 시나리오별 pass/fail 표
- 대표 실패 사례 1개 이상
- canonical 용어 일치 여부 체크리스트
- AI Agent 단독 검수 통과 여부 최종 결론
