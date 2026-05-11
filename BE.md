# Coin Agent Backend 명세

## 문서 목적

이 문서는 현재 구현 기준의 Backend 공개 API, Binance Testnet 실행 권한, run orchestration, 연속 자동매매 세션 제어를 설명한다.

## 1. BE 역할

- FE와 AI 사이의 orchestration coordinator
- Binance Spot Testnet 직접 호출
- timestamp / signature / API key 처리
- deterministic 재검증
- auto-trading session loop 소유
- checkpoint / report / 주문 로그 저장

## 2. 실행 권한 원칙

- BE만 Binance REST 호출을 수행한다.
- BE만 최종 실행 여부를 확정한다.
- AI의 `READY_FOR_BE` 는 제출 후보 상태일 뿐이다.

## 3. 공개 API 목록

- `GET /health`
- `GET /api/v1/testnet/account`
- `GET /api/v1/testnet/config`
- `GET /api/v1/testnet/ticker/price`
- `GET /api/v1/testnet/ticker/book`
- `GET /api/v1/testnet/klines`
- `POST /api/v1/testnet/orders`
- `POST /api/v1/testnet/orders/resume`
- `POST /api/v1/testnet/orders/auto`
- `POST /api/v1/testnet/orders/auto/session/start`
- `POST /api/v1/testnet/orders/auto/session/stop`
- `GET /api/v1/testnet/orders/auto/session`
- `GET /api/v1/testnet/orders/status`
- `GET /api/v1/testnet/orders/report`
- `DELETE /api/v1/testnet/orders`
- `GET /api/v1/testnet/stream/status`

## 4. 수동 주문 run 흐름

`POST /orders` 는 run 중심 응답을 반환한다.

가능한 대표 상태:

- `HOLD`
- `NO_ORDER`
- `BE_REJECTED`
- `REPORT_READY`

## 5. 자연어 auto order 흐름

`POST /orders/auto` 는 자연어 기반 agentic 실행 1회를 수행한다.

현재 구현 핵심:

- BE가 `rawText` 를 받음
- symbol hint / account / price / book / 5분 klines snapshot 을 수집
- 이 snapshot 을 AI `/runs/agentic/start` request_context에 주입
- AI가 `normalized_order_intent` 반환
- BE가 이를 실제 주문 요청으로 변환
- BE가 재검증 후 Binance 제출 또는 `BE_REJECTED`

## 6. 연속 자동매매 세션

### start

`POST /orders/auto/session/start`

- session 생성
- tick interval 결정 (180 / 300 / 600초)
- backend-owned background loop 시작

### stop

`POST /orders/auto/session/stop`

- 즉시 현재 loop 의 다음 tick 중단 요청
- 현재 in-flight tick 은 끝까지 진행한 뒤 stop

### status

`GET /orders/auto/session`

- `sessionStatus`
- `tickCount`
- `selectedTraderId`
- `selectedTickIntervalSeconds`
- `latestRun`
- `stopReason`
- `latestError`
- timestamps

현재 session continuation 규칙:

- 계속 진행: `REPORT_READY`, `NO_ORDER`, retryable `HOLD`
- 중단: non-retryable `HOLD`, `BE_REJECTED`, `FAILED`, user stop

retryable HOLD:

- `HOLD_INPUT_AMBIGUOUS`
- `HOLD_LOW_CONVICTION`
- `HOLD_RISK_AGENT_FLAGGED`

## 7. deterministic 재검증 범위

- 허용 심볼 확인
- `exchangeInfo` 기반 최소 수량 / 최소 notion 확인
- 잔고 확인
- 파라미터 검증

AI가 통과시켜도 이 재검증을 통과하지 못하면 `BE_REJECTED` 다.

## 8. AI 연동 계약

- `/runs/start`
- `/runs/agentic/start`
- `/runs/resume`
- `/runs/complete`

중요 사실:

- `policy_context` 는 BE가 만든다.
- auto-trading tick 에서는 live snapshot 도 BE가 request_context에 주입한다.
- agentic resume 는 현재 지원되지 않는다.

## 9. Settings / Reports 관련 현재 구현 메모

- `GET /config` endpoint 는 구현되어 있다.
- `GET /orders/report` endpoint 는 구현되어 있다.
- Reports FE 는 live report 와 연결돼 있다.
- Settings FE 는 아직 `/config` 를 live 호출하지 않는다.
