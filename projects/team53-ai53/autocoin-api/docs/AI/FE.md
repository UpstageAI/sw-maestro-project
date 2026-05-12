# autocoin-ai FE boundary 계약

## 문서 목적

이 문서는 `autocoin-ai`를 사용하는 FE가 어떤 입력과 표시 책임을 가지는지 최소 boundary-only 기준으로 정의한다. 새 기능을 추가하지 않고, FE가 무엇을 보내고 무엇을 보여야 하는지만 정리한다.

## 관련 문서

- 범위와 요구사항: `SPEC.md`
- 전체 흐름: `ARCHITECTURE.md`
- BE boundary 계약: `BE.md`
- AI 상태 해석: `AI.md`
- 데이터 계약: `DATA.md`
- 검증 기준: `TEST_AND_DEMO.md`

## 1. FE 책임

- 사용자 입력을 구조화 요청으로 정리해 BE에 전달한다.
- `run_id`, `hold_reason`, `decision_trace`, `verification_checks` 기반 상태를 표시한다.
- same `run_id` resume에 필요한 보완 입력을 다시 전달한다.

## 2. FE가 하지 않는 일

- Binance REST 또는 WebSocket 직접 호출
- API Key / Secret 원문 처리
- 서명 생성
- 최종 실행 승인 판단

## 3. FE 최소 입력/표시 계약

- 입력: 최소 `request_context`를 포함한 주문 테스트 요청, 보완 입력, 승인/거절 결과
- 표시: `HOLD`, `READY_FOR_BE`, `BE_REJECTED`, `FAILED`, `REPORT_READY`, `NO_ORDER`
- 설명: `decision_trace`와 `hold_reason` 기반 사용자 설명

최초 요청의 `request_context`는 `request_id`, `request_type`, `requested_at`, `user_input`을 포함해야 한다.

## 4. FE resume 규칙

- resume는 같은 `run_id`에서만 수행한다.
- FE는 이전 `decision_trace`를 덮어쓰지 않고, BE가 돌려준 기존 상태를 그대로 보여준다.
- FE는 patchable 입력만 다시 전송하고 lifecycle semantics를 임의로 바꾸지 않는다.

## 5. 검증 포인트

- FE는 Binance 직접 호출 없이도 모든 주문 테스트 흐름을 표시할 수 있어야 한다.
- FE는 `PASS`를 최종 체결 승인처럼 표현하면 안 된다.
- FE는 `READY_FOR_BE`를 최종 성공이 아니라 BE 재검증 전 상태로 표시해야 한다.
