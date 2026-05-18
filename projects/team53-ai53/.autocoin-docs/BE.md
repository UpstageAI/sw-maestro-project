# Coin Agent Backend 명세

## 문서 목적

이 문서는 현재 구현 기준의 Backend 공개 API, Binance Testnet 실행 권한, run orchestration, 연속 자동매매 세션 제어를 설명한다. 핵심은 BE가 자연어 자동매매를 대신 판단하는 화면 뒤에서, defensive rule base 와 deterministic 재검증을 통해 끝까지 fail-closed 실행 경계를 지킨다는 점이다.

## 1. BE 역할

- FE와 AI 사이의 orchestration coordinator
- Binance Spot Testnet 직접 호출
- timestamp / signature / API key 처리
- deterministic 재검증
- defensive rule base 집행
- auto-trading session loop 소유
- checkpoint / report / 주문 로그 저장

## 2. 실행 권한 원칙

- BE만 Binance REST 호출을 수행한다.
- BE만 최종 실행 여부를 확정한다.
- AI의 `READY_FOR_BE` 는 제출 후보 상태일 뿐이다.
- 사용자가 세션을 시작해도, 세션 지속/중단의 마지막 판정은 BE safety rule 이 가진다.

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
- AI 응답에는 `traderId`, `inferredPersona` 가 포함될 수 있고, BE는 이를 session metadata와 함께 다룬다.
- AI가 `normalized_order_intent` 반환
- BE가 이를 실제 주문 요청으로 변환
- BE가 defensive rule base 와 deterministic 재검증 후 Binance 제출 또는 `BE_REJECTED`

## 6. 연속 자동매매 세션

### start

`POST /orders/auto/session/start`

- session 생성
- tick interval 결정 (180 / 300 / 600초)
- backend-owned background loop 시작
- start 이후에는 FE가 아니라 BE가 same prompt 계열 판단 스타일을 이어가며 각 tick을 다시 검토

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

즉, "사용자가 멈출 때까지 계속" 이 기본 UX 설명에 가깝지만, 실제 구현에서는 BE defensive rule base 가 더 먼저 세션을 종료시킬 수 있다.

retryable HOLD:

- `HOLD_INPUT_AMBIGUOUS`
- `HOLD_LOW_CONVICTION`
- `HOLD_RISK_AGENT_FLAGGED`

## 7. defensive rule base / deterministic 재검증 범위

- 허용 심볼 확인
- `exchangeInfo` 기반 최소 수량 / 최소 notion 확인
- 잔고 확인
- 파라미터 검증

이 문서에서 defensive rule base 는 위와 같은 규칙 기반 차단 로직과, AI 결과를 다시 검토하는 deterministic 재검증 묶음을 함께 가리키는 이름이다.

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
- persona 전용 FE picker 가 없어도, 세션 시작 prompt 와 AI 추론 결과를 통해 `selectedTraderId` 가 정해질 수 있다.

## 9. Settings / Reports 관련 현재 구현 메모

- `GET /config` endpoint 는 구현되어 있다.
- `GET /orders/report` endpoint 는 구현되어 있다.
- Reports FE 는 live report 와 연결돼 있다.
- Settings FE 는 아직 `/config` 를 live 호출하지 않는다.
- report history 누적, 시간대별 cadence 조회, 다회차 축적 리포트 API는 아직 없다.
