# autocoin-ai FE boundary 계약

## 문서 목적

이 문서는 `autocoin-ai`를 사용하는 FE가 어떤 입력과 표시 책임을 가지는지 최소 boundary-only 기준으로 정의한다. Agentic MVP에서는 FE가 자연어 입력을 AI에 전달하고, AI가 만든 판단/요약/trace를 표시하는 역할까지 포함한다.

## 관련 문서

- 범위와 요구사항: `SPEC.md`
- 전체 흐름: `ARCHITECTURE.md`
- BE boundary 계약: `BE.md`
- AI 상태 해석: `AI.md`
- 데이터 계약: `DATA.md`
- 검증 기준: `TEST_AND_DEMO.md`

## 1. FE 책임

- 사용자 입력을 `raw_text` 중심으로 받아 BE/AI에 전달한다. 구조화 form은 보조 입력으로 유지할 수 있다.
- `run_id`, `hold_reason`, `decision_trace`, `verification_checks` 기반 상태를 표시한다.
- `evaluator_review.summary`, `evaluator_review.user_message`가 있으면 사용자용 설명으로 우선 표시한다.
- same `run_id` resume에 필요한 보완 입력을 다시 전달한다.

## 2. FE가 하지 않는 일

- Binance REST 또는 WebSocket 직접 호출
- API Key / Secret 원문 처리
- 서명 생성
- 최종 실행 승인 판단
- persona/trader override 직접 판정
- `PASS` 또는 `READY_FOR_BE`를 최종 주문 성공처럼 표현

## 3. FE 최소 입력/표시 계약

- 입력: 최소 `request_context`를 포함한 주문 테스트 요청, 자연어 `user_input.raw_text`, 보완 입력, 승인/거절 결과
- 표시: `HOLD`, `READY_FOR_BE`, `BE_REJECTED`, `FAILED`, `REPORT_READY`, `NO_ORDER`
- 설명: `evaluator_review`가 있으면 우선 사용하고, 없으면 `decision_trace`와 `hold_reason` 기반 사용자 설명

최초 요청의 `request_context`는 `request_id`, `request_type`, `requested_at`, `user_input`을 포함해야 한다.

Agentic MVP 입력 예시:

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

## 4. FE resume 규칙

- resume는 같은 `run_id`에서만 수행한다.
- FE는 이전 `decision_trace`를 덮어쓰지 않고, BE가 돌려준 기존 상태를 그대로 보여준다.
- FE는 patchable 입력만 다시 전송하고 lifecycle semantics를 임의로 바꾸지 않는다.

## 5. 검증 포인트

- FE는 Binance 직접 호출 없이도 모든 주문 테스트 흐름을 표시할 수 있어야 한다.
- FE는 `PASS`를 최종 체결 승인처럼 표현하면 안 된다.
- FE는 `READY_FOR_BE`를 최종 성공이 아니라 BE 재검증 전 상태로 표시해야 한다.
- FE는 AI가 반환한 `decision_trace`, `verification_checks`, `evaluator_review`를 숨기지 않고 데모에서 확인 가능하게 해야 한다.
