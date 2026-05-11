# API Specification

Coin Agent BE의 현재 구현 기준 공개 API 명세.

- Base URL: `http://localhost:8000`
- 성공 응답: **camelCase JSON**
- 오류 응답: 현재 **snake_case JSON**
- FE는 이 API만 호출하며 Binance를 직접 호출하지 않는다.

## 구현 상태

| 엔드포인트 | 상태 |
|---|---|
| `GET /health` | ✅ |
| `GET /api/v1/testnet/account` | ✅ |
| `GET /api/v1/testnet/config` | ✅ |
| `GET /api/v1/testnet/ticker/price` | ✅ |
| `GET /api/v1/testnet/ticker/book` | ✅ |
| `GET /api/v1/testnet/klines` | ✅ |
| `POST /api/v1/testnet/orders` | ✅ |
| `POST /api/v1/testnet/orders/resume` | ✅ |
| `POST /api/v1/testnet/orders/auto` | ✅ |
| `POST /api/v1/testnet/orders/auto/session/start` | ✅ |
| `POST /api/v1/testnet/orders/auto/session/stop` | ✅ |
| `GET /api/v1/testnet/orders/auto/session` | ✅ |
| `GET /api/v1/testnet/orders/report` | ✅ |
| `GET /api/v1/testnet/orders/status` | ✅ |
| `DELETE /api/v1/testnet/orders` | ✅ |
| `GET /api/v1/testnet/stream/status` | ✅ |

## 공통 오류 응답

```json
{
  "error_code": "REQUEST_FAILED",
  "message": "사람이 읽을 수 있는 메시지",
  "detail": "기술적 상세 내용",
  "request_id": "req_xxx",
  "timestamp": "2026-01-01T00:00:00+00:00"
}
```

## GET /health

```json
{
  "status": "ok",
  "env": "local"
}
```

## GET /api/v1/testnet/account

잔고 조회. 0이 아닌 자산만 반환.

```json
{
  "balances": [
    { "asset": "USDT", "free": "10000.00000000", "locked": "0.00000000" }
  ]
}
```

## GET /api/v1/testnet/config

현재 서버가 사용하는 Testnet REST / WS 기준 URL을 반환.

```json
{
  "restBaseUrl": "https://testnet.binance.vision/api",
  "wsStreamUrl": "wss://stream.testnet.binance.vision/ws",
  "wsApiUrl": "wss://ws-api.testnet.binance.vision/ws-api/v3"
}
```

## GET /api/v1/testnet/ticker/price

```json
{
  "symbol": "BTCUSDT",
  "price": "68000.00"
}
```

## GET /api/v1/testnet/ticker/book

현재 구현은 `bookTicker + depth(5)` 조합 응답을 반환.

```json
{
  "symbol": "BTCUSDT",
  "bidPrice": "67990.00",
  "bidQty": "0.10",
  "askPrice": "68010.00",
  "askQty": "0.20",
  "depth": {
    "lastUpdateId": 1,
    "bids": [["67990.00", "0.10"]],
    "asks": [["68010.00", "0.20"]]
  }
}
```

## GET /api/v1/testnet/klines

```json
{
  "symbol": "BTCUSDT",
  "interval": "5m",
  "items": [
    {
      "openTime": 1,
      "open": "67000",
      "high": "68100",
      "low": "66900",
      "close": "68000",
      "volume": "12"
    }
  ]
}
```

## POST /api/v1/testnet/orders

수동 구조화 주문 run 시작.

요청 예시:

```json
{
  "symbol": "BTCUSDT",
  "side": "BUY",
  "type": "MARKET",
  "quoteOrderQty": "10"
}
```

응답은 run 중심:

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

가능한 주요 `lifecycleStatus`:

- `HOLD`
- `NO_ORDER`
- `BE_REJECTED`
- `REPORT_READY`

## POST /api/v1/testnet/orders/resume

hold run 재개.

```json
{
  "runId": "run_hold_001",
  "resumeReason": "USER_APPROVED_ORDER",
  "patchFields": {
    "approval": { "approved": true }
  }
}
```

현재 구현 제약:

- checkpoint 존재 필요
- checkpoint 상태가 `HOLD` 여야 함
- checkpoint TTL 이 살아 있어야 함
- agentic run resume 는 현재 지원되지 않음

## POST /api/v1/testnet/orders/auto

자연어 auto order 1회 실행.

```json
{
  "rawText": "BTCUSDT를 50 USDT만큼 시장가 매수해줘"
}
```

응답:

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

중요한 현재 구현 사실:

- AI는 `/runs/agentic/start` 로 호출된다.
- BE는 live account/price/book/klines snapshot 을 요청 payload에 주입한다.
- 실제 제출 여부는 여전히 BE 재검증과 Binance submit 경로가 결정한다.

## POST /api/v1/testnet/orders/auto/session/start

연속 자동매매 세션 시작.

```json
{
  "rawText": "워뇨띠 스타일로 BTCUSDT를 50 USDT만큼 시장가 매수해줘"
}
```

응답:

```json
{
  "sessionId": "session_xxx",
  "sessionStatus": "ACTIVE",
  "stopRequested": false,
  "selectedTickIntervalSeconds": 300,
  "rawText": "워뇨띠 스타일로 BTCUSDT를 50 USDT만큼 시장가 매수해줘",
  "selectedTraderId": null,
  "tickCount": 0,
  "startedAt": "2026-05-12T00:00:00+09:00",
  "stoppedAt": null,
  "lastTickStartedAt": null,
  "lastTickCompletedAt": null,
  "stopReason": null,
  "latestError": null,
  "latestRun": null
}
```

세션 동작 규칙:

- FE가 아니라 BE가 loop 를 소유함
- 각 tick 은 fresh `run_id`
- fast keyword → 180초
- slow keyword → 600초
- default → 300초
- overlap start 는 409
- `REPORT_READY`, `NO_ORDER`, 일부 retryable HOLD 에서는 다음 tick 지속

## POST /api/v1/testnet/orders/auto/session/stop

세션 중지 요청.

```json
{
  "sessionId": "session_xxx",
  "sessionStatus": "STOPPING",
  "stopRequested": true
}
```

## GET /api/v1/testnet/orders/auto/session

현재 세션 상태 조회. `latestRun` 과 `stopReason`, `latestError` 를 함께 반환할 수 있음.

## GET /api/v1/testnet/orders/report

`runId` 기준 persisted published report 조회.

## GET /api/v1/testnet/orders/status

특정 Binance 주문 상태 조회.

## DELETE /api/v1/testnet/orders

특정 Binance 주문 취소.

## GET /api/v1/testnet/stream/status

백엔드 stream 상태 조회.

```json
{
  "connected": true,
  "streamName": "btcusdt@ticker",
  "lastEvent": { "s": "BTCUSDT", "c": "68000.00" }
}
```
