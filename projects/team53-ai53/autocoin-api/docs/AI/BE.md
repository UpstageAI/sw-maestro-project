# autocoin-ai BE boundary 계약

## 문서 목적

이 문서는 `autocoin-ai`를 감싸는 BE가 어떤 실행 권한과 검증 책임을 가지는지 최소 boundary-only 기준으로 정의한다. 새 기능을 추가하지 않고, AI와 Binance Testnet 사이 handoff와 deterministic revalidation 책임만 정리한다.

## 관련 문서

- 범위와 요구사항: `SPEC.md`
- 전체 흐름: `ARCHITECTURE.md`
- FE boundary 계약: `FE.md`
- AI 상태 해석: `AI.md`
- 데이터 계약: `DATA.md`
- 검증 기준: `TEST_AND_DEMO.md`

## 1. BE 책임

- `policy_context` retrieval과 정규화 입력 준비
- AI run 시작과 same `run_id` resume orchestration
- Binance Spot Testnet 호출, 서명, deterministic 재검증
- `BE_REJECTED` 또는 execution result 생성

## 2. BE가 하지 않는 일

- AI 판단을 무검증으로 최종 실행 권한처럼 취급
- FE에 Binance 직접 호출 책임을 위임
- Production host 사용

## 3. BE handoff 계약

- AI가 proposal을 통과시키면 lifecycle은 `READY_FOR_BE`로 정리된다.
- `PASS`는 BE가 받는 trace/gate 근거일 뿐, lifecycle 상태가 아니다.
- BE는 `READY_FOR_BE` 이후 deterministic revalidation을 수행한다.
- 재검증 실패는 `BE_REJECTED`, schema mismatch 또는 복구 불가 실패는 `FAILED`로 구분한다.
- BE는 AI에 `execution_result` 또는 `be_rejection_evidence` 중 하나를 포함한 completion payload를 되돌려 준다.

## 4. BE resume 규칙

- 같은 `run_id`의 checkpoint를 복원한다.
- immutable 컨텍스트(`run_id`, 최초 `policy_context`, 이전 trace)는 유지한다.
- approval 결과, 보완 입력, execution result 같은 patchable 필드만 병합한다.

## 5. 검증 포인트

- BE만 Binance 서명과 제출 권한을 가진다.
- `HOLD`에서는 cadence를 멈추고 resume을 기다린다.
- `FAILED`는 terminal failure로 취급하고 `REPORT_READY`로 강제 승격하지 않는다.
- FE와 AI가 같은 canonical 필드/상태명을 보도록 계약을 유지한다.
