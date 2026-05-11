# BE ↔ AI 연동 명세

## 문서 목적

이 문서는 `autocoin-api` 가 `autocoin-ai` 를 어떻게 호출하는지, 그리고 실행 권한이 어디까지 BE에 남아 있는지를 설명한다.

## 현재 AI 호출 경로

- `POST /runs/start` — 수동 주문 run 시작
- `POST /runs/agentic/start` — 자연어/agentic run 시작
- `POST /runs/resume` — non-agentic hold run 재개
- `POST /runs/complete` — execution 결과 또는 BE rejection 반영

## 수동 주문 경로

1. BE가 `request_context`, `policy_context` 생성
2. AI `/runs/start` 호출
3. AI가 `HOLD`, `NO_ORDER`, `READY_FOR_BE` 반환
4. `READY_FOR_BE` 이면 BE 재검증 및 Binance 제출
5. 결과를 AI `/runs/complete` 로 주입

## 자연어 auto order 경로

1. FE/세션이 `rawText` 전달
2. BE가 live account/price/book/klines snapshot 을 수집
3. snapshot 을 포함한 `request_context.user_input` 로 AI `/runs/agentic/start` 호출
4. AI가 `normalized_order_intent`, `trader_id`, `inferred_persona`, lifecycle 반환
5. `READY_FOR_BE` 이면 BE가 이를 실제 주문 요청으로 변환
6. BE 재검증 후 Binance 제출 또는 `BE_REJECTED`

## 자연어 연속 세션 경로

- session loop 는 BE가 소유한다.
- 각 tick 은 fresh `run_id` 다.
- retryable HOLD 에서는 세션이 다음 tick 으로 이어질 수 있다.
- non-retryable HOLD, `BE_REJECTED`, `FAILED` 에서는 세션이 중단된다.

## 현재 제약

- agentic run resume 는 현재 지원되지 않는다.
- AI는 제출 후보를 만들 뿐, 실행권자가 아니다.
- BE가 주입한 live snapshot 이 auto-trading 판단 품질에 직접 영향을 준다.
