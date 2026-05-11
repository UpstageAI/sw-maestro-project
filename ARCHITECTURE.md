# Coin Agent 시스템 아키텍처

## 문서 목적

이 문서는 현재 구현 기준의 canonical 구조를 설명한다. 핵심은 FE 입력/표시, BE 실행 권한, AI 판단 보조, Binance Testnet 실제 연결, run/report/session 경계를 흔들리지 않게 유지하는 것이다.

## 1. 시스템 구성

1. React Frontend (`autocoin-web`)
2. FastAPI Backend (`autocoin-api`)
3. Standalone HTTP AI Service (`autocoin-ai`)
4. SQLite 저장소
5. Binance Spot Testnet REST / WebSocket

## 2. 권한 경계

| 계층 | 책임 | 금지 사항 |
|---|---|---|
| FE | 입력 수집, 상태 polling, 결과 표시 | Binance 직접 호출, 로컬 auto-trading loop 소유 |
| BE | 공개 API, AI 호출, Binance 호출, 재검증, 세션 loop, 보고 저장 | AI 판단만 믿고 무검증 제출 |
| AI | 자연어 해석, 정책 grounding, 전략/리스크 판단, trace 생성, completion 해석 | Binance 직접 제출, 서명, 최종 실행 확정 |
| DB | checkpoint, 주문 로그, report 저장 | 실행 권한 결정 |
| Binance | 시장 데이터와 Testnet 주문 처리 | 내부 정책 해석 |

## 3. 공개 인터페이스

### FE → BE

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

### BE → AI

- `POST /runs/start`
- `POST /runs/agentic/start`
- `POST /runs/resume`
- `POST /runs/complete`
- `GET /runs/{run_id}/checkpoints/order`
- `GET /runs/{run_id}/checkpoints/completion`

### BE → Binance

- `GET /v3/account`
- `GET /v3/ticker/price`
- `GET /v3/ticker/bookTicker`
- `GET /v3/depth`
- `GET /v3/klines`
- `GET /v3/exchangeInfo`
- `POST /v3/order`
- `GET /v3/order`
- `DELETE /v3/order`

## 4. 수동 주문 run 흐름

1. FE가 `POST /orders` 호출
2. BE가 `run_id`, `request_context`, `policy_context` 생성
3. AI `/runs/start` 호출
4. AI가 `HOLD`, `NO_ORDER`, `READY_FOR_BE` 반환
5. `READY_FOR_BE` 일 때만 BE가 deterministic 재검증 수행
6. 통과하면 Binance 제출
7. 제출 결과 또는 차단 근거를 AI `/runs/complete` 로 주입
8. BE가 최종 run/report/checkpoint 저장 후 FE에 run 중심 응답 반환

## 5. 자연어 auto order 1회 실행 흐름

1. FE가 `POST /orders/auto` 호출
2. BE가 `rawText` 기반 요청을 받음
3. BE가 live account/price/book/5분 klines snapshot 을 수집
4. snapshot 을 포함한 `request_context.user_input` 로 AI `/runs/agentic/start` 호출
5. AI agentic graph가 `intake -> policy -> strategy -> risk_agent -> risk_gate -> evaluator` 수행
6. `READY_FOR_BE` 이면 BE가 `normalized_order_intent` 를 실제 주문 요청으로 변환
7. BE가 재검증 후 Binance 제출 또는 `BE_REJECTED`
8. AI `/runs/complete` 호출 및 report/checkpoint 저장

## 6. 연속 자연어 자동매매 세션 흐름

1. FE가 `POST /orders/auto/session/start` 호출
2. BE가 session 상태를 `ACTIVE` 로 만들고 tick interval(180/300/600초)을 결정
3. 각 tick 마다 BE가 fresh `run_id` 로 `create_auto_order()` 를 호출
4. tick 결과가 `REPORT_READY`, `NO_ORDER`, 일부 retryable `HOLD` 이면 다음 tick 대기
5. tick 결과가 non-retryable `HOLD`, `BE_REJECTED`, `FAILED` 이면 세션 `STOPPED`
6. FE는 `GET /orders/auto/session` polling 으로 상태를 본다

현재 retryable HOLD:

- `HOLD_INPUT_AMBIGUOUS`
- `HOLD_LOW_CONVICTION`
- `HOLD_RISK_AGENT_FLAGGED`

현재 non-retryable HOLD 예시:

- `HOLD_DATA_INSUFFICIENT`

## 7. 현재 구현 제약

- agentic run resume 는 현재 지원되지 않는다.
- Reports 페이지는 single-run `runId` 조회만 지원한다.
- FE Settings는 `/config` endpoint를 아직 실제 호출하지 않는다.
- stream status는 고정 `btcusdt@ticker` 기준 background task 이다.

## 8. 저장 경계

### BE 저장

- `agent_run_checkpoints`
- 주문 로그 / 상태 로그 / 취소 로그
- run report

### AI 저장

- 로컬 JSON run store

AI run 저장소와 BE checkpoint는 서로 다른 durability 계층이므로 동일한 durability로 간주하면 안 된다.
