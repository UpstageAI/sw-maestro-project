# Coin Agent 데이터 및 API 계약

## 문서 목적

이 문서는 현재 구현 기준의 canonical 공개 계약을 정의한다. FE, BE, AI가 공유해야 하는 공개 요청/응답, run 상태, 세션 상태, 명명 규칙을 다룬다. 특히 자연어 자동매매 계약에서는 사용자 입력 기반 persona 추론 결과와, user stop 외에 safety stop 이 존재할 수 있다는 의미를 숨기지 않는다.

## 1. 명명 규칙

- 공개 성공 응답: camelCase
- 공개 오류 응답: snake_case
- AI 내부 payload: snake_case

## 2. 공개 BE API 목록

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

## 3. 수동 주문 요청 계약

### SpotOrderRequest

```json
{
  "symbol": "BTCUSDT",
  "side": "BUY",
  "type": "MARKET",
  "quoteOrderQty": "10"
}
```

`traderId`, `inferredPersona` 는 전용 FE picker 입력값이 아니라, 현재 구현에서는 자연어 입력과 AI 추론 결과에서 파생될 수 있는 응답 필드다.

## 4. 수동 주문 응답 계약

### OrderRunResponse

```json
{
  "runId": "run_xxx",
  "lifecycleStatus": "REPORT_READY",
  "holdReason": null,
  "orderId": 123456789,
  "symbol": "BTCUSDT",
  "status": "NEW",
  "type": "MARKET",
  "side": "BUY",
  "reasonCodes": []
}
```

이 응답은 수동 주문 요청이 어떤 run 상태로 귀결됐는지 보여주는 계약이다. 즉 세션 상태를 설명하는 응답이 아니라, 개별 주문 run의 lifecycle 결과를 반환하는 응답이다.

주요 상태:

- `HOLD`
- `NO_ORDER`
- `BE_REJECTED`
- `REPORT_READY`
- `FAILED`

## 5. 자연어 auto order 계약

### AutoOrderRequest

```json
{
  "rawText": "BTCUSDT를 50 USDT만큼 시장가 매수해줘"
}
```

### AutoOrderRunResponse

```json
{
  "runId": "run_xxx",
  "lifecycleStatus": "HOLD",
  "holdReason": "HOLD_INPUT_AMBIGUOUS",
  "reasonCodes": ["INPUT_AMBIGUOUS"],
  "normalizedOrderIntent": {
    "symbol": "BTCUSDT",
    "side": "BUY",
    "type": "MARKET",
    "quoteOrderQty": "50"
  },
  "traderId": "wonyotti",
  "inferredPersona": "AGGRESSIVE"
}
```

## 6. 연속 자동매매 세션 계약

### AutoSessionStartRequest

```json
{
  "rawText": "워뇨띠 스타일로 BTCUSDT를 50 USDT만큼 시장가 매수해줘"
}
```

### AutoTradingSessionResponse

```json
{
  "sessionId": "session_xxx",
  "sessionStatus": "ACTIVE",
  "stopRequested": false,
  "selectedTickIntervalSeconds": 300,
  "rawText": "워뇨띠 스타일로 BTCUSDT를 50 USDT만큼 시장가 매수해줘",
  "selectedTraderId": "wonyotti",
  "tickCount": 1,
  "startedAt": "2026-05-12T00:00:00+09:00",
  "stoppedAt": null,
  "lastTickStartedAt": "2026-05-12T00:00:00+09:00",
  "lastTickCompletedAt": "2026-05-12T00:00:10+09:00",
  "stopReason": null,
  "latestError": null,
  "latestRun": null
}
```

### sessionStatus 값

- `IDLE`
- `ACTIVE`
- `STOPPING`
- `STOPPED`

### 현재 세션 continuation 규칙

- 계속 진행: `REPORT_READY`, `NO_ORDER`, retryable `HOLD`
- 중단: non-retryable `HOLD`, `BE_REJECTED`, `FAILED`, user stop

즉 세션 의미는 단순히 "사용자가 중지할 때까지 무조건 계속" 이 아니라, BE의 deterministic 재검증과 defensive rule base 가 허용하는 동안만 계속이다.

retryable HOLD:

- `HOLD_INPUT_AMBIGUOUS`
- `HOLD_LOW_CONVICTION`
- `HOLD_RISK_AGENT_FLAGGED`

## 7. 주문 상태/취소/리포트 계약

- `OrderStatusResponse`
- `CancelOrderResponse`
- `RunReportResponse`

현재 `RunReportResponse` 는 persisted published report 기준이며, FE Reports는 `runId` 단일 조회만 구현되어 있다.

시간 단위로 누적되는 cadence/history report 응답 계약은 아직 없다.

## 8. 대표 hold reason

- `HOLD_REVIEW_REQUIRED`
- `HOLD_DATA_INSUFFICIENT`
- `HOLD_INPUT_AMBIGUOUS`
- `HOLD_LOW_CONVICTION`
- `HOLD_RISK_AGENT_FLAGGED`

## 9. AI HTTP 계약 요약

- `POST /runs/start`
- `POST /runs/agentic/start`
- `POST /runs/resume`
- `POST /runs/complete`
- `GET /runs/{run_id}/checkpoints/order`
- `GET /runs/{run_id}/checkpoints/completion`

agentic run resume 는 현재 지원되지 않는다.
