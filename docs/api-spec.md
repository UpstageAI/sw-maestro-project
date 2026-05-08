# API Specification

Coin Agent BE — Binance Spot Testnet 전용 백엔드 API 명세.

- Base URL: `http://localhost:8000`
- 모든 응답은 **camelCase JSON**
- 인증: 서버가 환경 변수의 API Key / Secret으로 Binance Testnet에 서명하여 호출 (클라이언트는 별도 인증 불필요)

---

## 공통 에러 응답

HTTP 4xx / 5xx 시 아래 형식으로 반환됩니다.

```json
{
  "errorCode": "REQUEST_FAILED",
  "message": "사람이 읽을 수 있는 메시지",
  "detail": "기술적 상세 내용 (local 환경에서만 노출)",
  "requestId": "req_a1b2c3d4",
  "timestamp": "2026-01-01T00:00:00+00:00"
}
```

| errorCode | HTTP | 상황 |
|---|---|---|
| `VALIDATION_ERROR` | 422 | 요청 파라미터 오류 |
| `REQUEST_FAILED` | 4xx | 일반 요청 실패 |
| `INTERNAL_SERVER_ERROR` | 500 | 서버 내부 오류 |

---

## GET /health

헬스 체크. 서버 동작 여부 확인용.

### 응답 `200`

```json
{
  "status": "ok",
  "env": "local"
}
```

---

## GET /api/v1/testnet/account

Testnet 계정의 현재 잔고를 조회합니다. 잔액이 0인 자산은 제외합니다.

### 응답 `200`

```json
{
  "balances": [
    {
      "asset": "BTC",
      "free": "0.05000000",
      "locked": "0.00000000"
    },
    {
      "asset": "USDT",
      "free": "9900.00000000",
      "locked": "100.00000000"
    }
  ]
}
```

| 필드 | 타입 | 설명 |
|---|---|---|
| `balances` | `BalanceItem[]` | 보유 자산 목록 (잔액 > 0인 것만) |
| `balances[].asset` | `string` | 자산명 (`BTC`, `USDT`, ...) |
| `balances[].free` | `string` | 사용 가능 수량 |
| `balances[].locked` | `string` | 주문 잠금 수량 |

---

## GET /api/v1/testnet/ticker/price

특정 심볼의 현재가를 조회합니다.

### 쿼리 파라미터

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `symbol` | `string` | ✅ | 심볼 대문자 (`BTCUSDT`, `ETHUSDT`) |

### 응답 `200`

```json
{
  "symbol": "BTCUSDT",
  "price": "80000.00000000"
}
```

---

## GET /api/v1/testnet/ticker/book

특정 심볼의 최우선 호가(BBO)와 Order Book 상위 항목을 조회합니다.  
Binance `bookTicker`와 `depth` API를 병렬로 호출하여 결합합니다.

### 쿼리 파라미터

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `symbol` | `string` | ✅ | 심볼 대문자 (`BTCUSDT`) |

### 응답 `200`

```json
{
  "symbol": "BTCUSDT",
  "bidPrice": "79999.00000000",
  "bidQty": "0.50000000",
  "askPrice": "80001.00000000",
  "askQty": "0.30000000",
  "depth": {
    "lastUpdateId": 123456789,
    "bids": [
      ["79999.00000000", "0.50000000"],
      ["79998.00000000", "1.20000000"]
    ],
    "asks": [
      ["80001.00000000", "0.30000000"],
      ["80002.00000000", "0.80000000"]
    ]
  }
}
```

| 필드 | 타입 | 설명 |
|---|---|---|
| `bidPrice` | `string` | 최우선 매수 호가 |
| `bidQty` | `string` | 최우선 매수 수량 |
| `askPrice` | `string` | 최우선 매도 호가 |
| `askQty` | `string` | 최우선 매도 수량 |
| `depth.lastUpdateId` | `number` | Order Book 업데이트 ID |
| `depth.bids` | `[price, qty][]` | 매수 호가 목록 (높은 가격 순) |
| `depth.asks` | `[price, qty][]` | 매도 호가 목록 (낮은 가격 순) |

---

## GET /api/v1/testnet/klines

캔들(OHLCV) 데이터를 조회합니다.

### 쿼리 파라미터

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|---|---|---|---|---|
| `symbol` | `string` | ✅ | - | 심볼 대문자 (`BTCUSDT`) |
| `interval` | `string` | ✅ | - | 캔들 주기 (`1m`, `5m`, `15m`, `1h`, `4h`, `1d`) |
| `limit` | `integer` | ❌ | `100` | 반환할 캔들 수 (최대 1000) |

### 응답 `200`

```json
{
  "symbol": "BTCUSDT",
  "interval": "1m",
  "items": [
    {
      "openTime": 1700000000000,
      "open": "79500.00",
      "high": "80100.00",
      "low": "79400.00",
      "close": "80000.00",
      "volume": "123.45"
    }
  ]
}
```

| 필드 | 타입 | 설명 |
|---|---|---|
| `items[].openTime` | `number` | 캔들 시작 시각 (Unix ms) |
| `items[].open` | `string` | 시가 |
| `items[].high` | `string` | 고가 |
| `items[].low` | `string` | 저가 |
| `items[].close` | `string` | 종가 |
| `items[].volume` | `string` | 거래량 |

---

## POST /api/v1/testnet/orders

현물 주문을 생성합니다. Binance Testnet에 서명된 요청을 전송하고 결과를 DB에 저장합니다.

### 요청 Body

```json
{
  "symbol": "BTCUSDT",
  "side": "BUY",
  "type": "LIMIT",
  "quantity": "0.001",
  "price": "80000.00",
  "timeInForce": "GTC"
}
```

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `symbol` | `string` | ✅ | 심볼 대문자 |
| `side` | `"BUY" \| "SELL"` | ✅ | 매수/매도 |
| `type` | `"MARKET" \| "LIMIT"` | ✅ | 주문 유형 |
| `quantity` | `string` | 조건부 | 수량 (LIMIT 주문 필수, MARKET 주문 시 `quoteOrderQty`와 택1) |
| `quoteOrderQty` | `string` | 조건부 | USDT 기준 금액 (MARKET 주문 전용) |
| `price` | `string` | 조건부 | 가격 (LIMIT 주문 필수) |
| `timeInForce` | `"GTC" \| "IOC" \| "FOK"` | 조건부 | 체결 조건 (LIMIT 주문 필수) |

**유효성 규칙:**
- LIMIT: `quantity`, `price`, `timeInForce` 모두 필수
- MARKET: `quantity` 또는 `quoteOrderQty` 중 하나 필수

### 응답 `200`

```json
{
  "orderId": 123456789,
  "symbol": "BTCUSDT",
  "status": "NEW",
  "type": "LIMIT",
  "side": "BUY"
}
```

| `status` 값 | 설명 |
|---|---|
| `NEW` | 주문 접수 |
| `PARTIALLY_FILLED` | 부분 체결 |
| `FILLED` | 전량 체결 |
| `CANCELED` | 취소됨 |
| `REJECTED` | 거부됨 |
| `EXPIRED` | 만료됨 |

---

## GET /api/v1/testnet/orders/status

주문의 현재 상태를 조회합니다.

### 쿼리 파라미터

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `symbol` | `string` | ✅ | 심볼 대문자 |
| `orderId` | `integer` | 조건부 | Binance 주문 ID (`orderId` 또는 `origClientOrderId` 중 하나 필수) |
| `origClientOrderId` | `string` | 조건부 | 클라이언트 주문 ID |

### 응답 `200`

```json
{
  "orderId": 123456789,
  "symbol": "BTCUSDT",
  "status": "FILLED",
  "executedQty": "0.00100000"
}
```

| 필드 | 타입 | 설명 |
|---|---|---|
| `orderId` | `number` | Binance 주문 ID |
| `symbol` | `string` | 심볼 |
| `status` | `string` | 현재 주문 상태 |
| `executedQty` | `string` | 체결된 수량 |

---

## DELETE /api/v1/testnet/orders

주문을 취소합니다.

### 요청 Body

```json
{
  "symbol": "BTCUSDT",
  "orderId": 123456789
}
```

또는 `origClientOrderId` 사용:

```json
{
  "symbol": "BTCUSDT",
  "origClientOrderId": "my-order-001"
}
```

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `symbol` | `string` | ✅ | 심볼 대문자 |
| `orderId` | `integer` | 조건부 | Binance 주문 ID (`orderId` 또는 `origClientOrderId` 중 하나 필수) |
| `origClientOrderId` | `string` | 조건부 | 클라이언트 주문 ID |

### 응답 `200`

```json
{
  "orderId": 123456789,
  "symbol": "BTCUSDT",
  "status": "CANCELED"
}
```

---

## GET /api/v1/testnet/stream/status

서버의 WebSocket 스트림 연결 상태를 반환합니다.  
서버 시작 시 `btcusdt@ticker`를 자동 구독하며, 연결이 끊기면 5초 후 재연결을 시도합니다.

### 응답 `200`

**연결됨:**
```json
{
  "connected": true,
  "streamName": "btcusdt@ticker",
  "lastEvent": {
    "e": "24hrTicker",
    "s": "BTCUSDT",
    "c": "80000.00",
    "v": "1234.56"
  }
}
```

**연결 안 됨:**
```json
{
  "connected": false,
  "streamName": null,
  "lastEvent": null
}
```

| 필드 | 타입 | 설명 |
|---|---|---|
| `connected` | `boolean` | WebSocket 연결 여부 |
| `streamName` | `string \| null` | 구독 중인 스트림 이름 |
| `lastEvent` | `object \| null` | 가장 최근 수신한 WebSocket 이벤트 원본 |
