# Coin Agent 테스트 및 데모 기준

## 문서 목적

이 문서는 현재 구현 기준에서 무엇을 검증해야 하는지 정의한다. 수동 주문 happy path 뿐 아니라 자연어 auto order, continuous session, live snapshot grounding, run/report 흐름을 모두 포함한다.

## 1. 테스트 원칙

- Binance Spot Testnet 기준
- FE는 Binance를 직접 호출하지 않음
- AI는 Binance를 직접 제출/서명하지 않음
- BE만 실행 권한을 가짐
- 수동 주문과 auto-trading session은 각각 별도 시나리오로 검증

## 2. 핵심 계약 테스트

| ID | 대상 | 검증 포인트 |
|---|---|---|
| T-00 | `GET /config` | camelCase 설정 응답 |
| T-01 | `POST /orders` | run 중심 응답 |
| T-02 | `POST /orders/resume` | 수동 hold resume |
| T-03 | `POST /orders/auto` | natural language auto order 응답 |
| T-04 | `POST /orders/auto/session/start` | session start |
| T-05 | `POST /orders/auto/session/stop` | stop 요청 |
| T-06 | `GET /orders/auto/session` | session status / latestRun |
| T-07 | AI `/runs/agentic/start` | agentic state 생성 |
| T-08 | AI checkpoint endpoints | order/completion checkpoint evidence |
| T-09 | live snapshot grounding | auto tick 요청에 account/market snapshot 포함 |

## 3. 필수 API 검증 묶음

### AI

```bash
pytest tests/test_intake.py tests/test_strategy.py tests/test_risk_gate.py tests/test_http_api.py -v
```

### BE

```bash
pytest tests/test_orders_auto.py tests/test_auto_session.py tests/test_reports.py -v
```

### FE

```bash
npm run lint
npm run build
```

## 4. 필수 데모 시나리오

### S-01 수동 주문 run 성공

`POST /orders` → `READY_FOR_BE` → BE 재검증 → Binance submit → `REPORT_READY`

### S-02 수동 hold resume

`HOLD_REVIEW_REQUIRED` 또는 `HOLD_DATA_INSUFFICIENT` 이후 `POST /orders/resume`

### S-03 자연어 auto order 1회 실행

`POST /orders/auto` 로 `normalizedOrderIntent`, `traderId`, `inferredPersona`, `lifecycleStatus` 확인

### S-04 연속 자동매매 세션

`/auto-trading` 에서 세션 시작 후:

- session status polling
- selected trader 표시
- latest run / latest report 표시
- stop 요청 가능

### S-05 live snapshot grounding 확인

명시적 BTCUSDT BUY 문장으로 auto session 실행 시 first tick 이 live snapshot 기반 판단을 거쳐 `REPORT_READY` 또는 retryable 상태로 진행되는지 확인

## 5. 데모 메시지 기준

- FE는 Binance를 직접 호출하지 않는다.
- AI는 실행권자가 아니다.
- `READY_FOR_BE` 는 실행 완료가 아니라 BE 재검증 대기다.
- auto-trading session loop 는 BE가 소유한다.
- 각 tick 은 fresh `run_id` 다.
- auto-trading path는 live account/market snapshot 을 AI에 주입한다.
- Reports는 single-run live report 조회고 cadence/history는 placeholder다.
- Settings는 현재 placeholder 중심이며 `/config` live 연동은 아직 없다.
