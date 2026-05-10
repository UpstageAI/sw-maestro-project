# Coin Agent 데이터 및 API 계약

## 문서 목적

이 문서는 루트 문서 세트의 canonical 계약 문서다. FE, BE, AI가 공유하는 공개 요청과 응답, 상태값, 명명 규칙을 정의한다.

## 1. 명명 규칙

- 공개 성공 응답은 camelCase를 사용한다.
- 현재 공개 오류 응답은 snake_case를 사용한다.
- 내부 AI 서비스 payload는 현재 snake_case를 사용한다.

## 2. 핵심 용어

| 용어 | 의미 |
|---|---|
| `runId` | 공개 BE API에서 사용하는 run 식별자 |
| `run_id` | AI 내부 및 AI HTTP API에서 사용하는 run 식별자 |
| `lifecycleStatus` | 현재 run 상태 |
| `holdReason` | `HOLD` 의 세부 원인 |
| `reasonCodes` | 판단 또는 차단 근거 코드 목록 |
| `policyContext` | BE가 조합해 AI에 주입하는 정책 근거 |
| `executionResult` | BE가 Binance 실행 결과를 정규화해 AI에 다시 주입한 객체 |

## 3. 공개 BE API 목록

| 메서드 | 경로 | 응답 계약 |
|---|---|---|
| GET | `/health` | `HealthResponse` |
| GET | `/api/v1/testnet/account` | `BalanceResponse` |
| GET | `/api/v1/testnet/config` | `TestnetConfigResponse` |
| GET | `/api/v1/testnet/ticker/price` | `PriceResponse` |
| GET | `/api/v1/testnet/ticker/book` | `BookResponse` |
| GET | `/api/v1/testnet/klines` | `KlinesResponse` |
| POST | `/api/v1/testnet/orders` | `OrderRunResponse` |
| POST | `/api/v1/testnet/orders/resume` | `OrderRunResponse` |
| GET | `/api/v1/testnet/orders/status` | `OrderStatusResponse` |
| GET | `/api/v1/testnet/orders/report` | `RunReportResponse` |
| DELETE | `/api/v1/testnet/orders` | `CancelOrderResponse` |
| GET | `/api/v1/testnet/stream/status` | `StreamStatusResponse` |

## 4. 주문 요청 계약

### 4.1 SpotOrderRequest

```json
{
  "symbol": "BTCUSDT",
  "side": "BUY",
  "type": "MARKET",
  "quoteOrderQty": "10"
}
```

제약 요약:

- `MARKET` 매수는 보통 `quoteOrderQty` 를 사용한다.
- `MARKET` 매도는 보통 `quantity` 를 사용한다.
- `LIMIT` 는 `price`, `quantity`, `timeInForce` 가 필요하다.

## 5. 주문 생성 응답의 canonical 계약

### 5.1 OrderRunResponse

```json
{
  "runId": "run_0f3b6f",
  "lifecycleStatus": "REPORT_READY",
  "holdReason": null,
  "orderId": 123456789,
  "symbol": "BTCUSDT",
  "status": "NEW",
  "type": "LIMIT",
  "side": "BUY",
  "reasonCodes": []
}
```

필드 설명:

| 필드 | 타입 | 설명 |
|---|---|---|
| `runId` | string | run 식별자 |
| `lifecycleStatus` | string | 현재 또는 최종 run 상태 |
| `holdReason` | string \| null | `HOLD` 인 경우 세부 원인 |
| `orderId` | number \| null | Binance 제출이 실제로 일어난 경우의 주문 ID |
| `symbol` | string \| null | 제출된 심볼 |
| `status` | string \| null | 주문 상태 |
| `type` | string \| null | 주문 타입 |
| `side` | string \| null | 주문 방향 |
| `reasonCodes` | string[] | 보류, 무주문, 재검증 차단 등 이유 코드 |

### 5.2 중요한 canonical 규칙

- `POST /api/v1/testnet/orders` 의 public contract는 `OrderRunResponse` 다.
- `POST /api/v1/testnet/orders/resume` 의 public contract도 `OrderRunResponse` 다.
- 이 두 엔드포인트는 Binance 원본 주문 응답 전체를 직접 public response로 약속하지 않는다.
- Binance 원본 응답은 BE 내부 실행 결과, 로그, 보고 생성의 입력으로만 다룬다.

### 5.3 상태별 예시

#### HOLD

```json
{
  "runId": "run_hold_001",
  "lifecycleStatus": "HOLD",
  "holdReason": "HOLD_REVIEW_REQUIRED",
  "orderId": null,
  "symbol": null,
  "status": null,
  "type": null,
  "side": null,
  "reasonCodes": []
}
```

#### NO_ORDER

```json
{
  "runId": "run_no_order_001",
  "lifecycleStatus": "NO_ORDER",
  "holdReason": null,
  "orderId": null,
  "symbol": null,
  "status": null,
  "type": null,
  "side": null,
  "reasonCodes": ["RISK_THRESHOLD_EXCEEDED"]
}
```

#### BE_REJECTED

```json
{
  "runId": "run_reject_001",
  "lifecycleStatus": "BE_REJECTED",
  "holdReason": null,
  "orderId": null,
  "symbol": null,
  "status": null,
  "type": null,
  "side": null,
  "reasonCodes": ["MIN_NOTIONAL_NOT_MET"]
}
```

## 6. resume 요청 계약

### 6.1 ResumeCommandPayload

```json
{
  "runId": "run_hold_001",
  "resumeReason": "USER_APPROVED_ORDER",
  "patchFields": {
    "approval": {
      "approved": true
    }
  }
}
```

### 6.2 canonical 의미

- `runId` 는 기존 hold run 을 가리킨다.
- `resumeReason` 은 왜 재개하는지 설명한다.
- `patchFields` 는 승인 정보, 보완 입력, 재조회 데이터 같은 추가 정보를 담는다.

## 7. 주문 상태 및 취소 계약

### 7.1 OrderStatusResponse

```json
{
  "orderId": 123456789,
  "symbol": "BTCUSDT",
  "status": "FILLED",
  "executedQty": "0.001"
}
```

### 7.2 CancelOrderResponse

```json
{
  "orderId": 123456789,
  "symbol": "BTCUSDT",
  "status": "CANCELED"
}
```

상태 조회와 취소는 run 중심 생성 API와 구분되는 별도 public contract다.

## 8. market 조회 계약

### 8.0 TestnetConfigResponse

```json
{
  "restBaseUrl": "https://testnet.binance.vision/api",
  "wsStreamUrl": "wss://stream.testnet.binance.vision/ws",
  "wsApiUrl": "wss://ws-api.testnet.binance.vision/ws-api/v3"
}
```

### 8.1 BalanceResponse

```json
{
  "balances": [
    {
      "asset": "USDT",
      "free": "10000.00000000",
      "locked": "0.00000000"
    }
  ]
}
```

### 8.2 PriceResponse

```json
{
  "symbol": "BTCUSDT",
  "price": "65000.12"
}
```

### 8.3 BookResponse

```json
{
  "symbol": "BTCUSDT",
  "bidPrice": "64999.99",
  "bidQty": "0.12",
  "askPrice": "65000.13",
  "askQty": "0.45",
  "depth": {
    "lastUpdateId": 123456,
    "bids": [["64999.99", "0.12"]],
    "asks": [["65000.13", "0.45"]]
  }
}
```

### 8.4 KlinesResponse

```json
{
  "symbol": "BTCUSDT",
  "interval": "1m",
  "items": [
    {
      "openTime": 1715000000000,
      "open": "64950.00",
      "high": "65100.00",
      "low": "64880.00",
      "close": "65000.12",
      "volume": "12.34"
    }
  ]
}
```

## 8.5 run report 조회 계약

```json
{
  "runId": "run_report_001",
  "report": {
    "status": "success",
    "message": "done"
  }
}
```

`GET /api/v1/testnet/orders/report?runId=...` 는 checkpoint 에 저장된 run report를 반환한다.

## 9. stream 상태 계약

```json
{
  "connected": true,
  "streamName": "btcusdt@ticker",
  "lastEvent": {
    "e": "24hrTicker",
    "s": "BTCUSDT",
    "c": "65000.12"
  }
}
```

## 10. 오류 응답 계약

```json
{
  "error_code": "REQUEST_FAILED",
  "message": "runId not found: run_missing_001",
  "detail": null,
  "request_id": "req_0abc1234",
  "timestamp": "2026-05-09T10:00:00+00:00"
}
```

오류 payload는 현재 snake_case를 사용한다.

## 11. AI HTTP 계약

### 11.1 `/runs/start`

요청 예시:

```json
{
  "run_id": "run_0f3b6f",
  "request_context": {
    "request_id": "run_0f3b6f",
    "request_type": "PLACE_ORDER_TEST",
    "user_input": {
      "symbol": "BTCUSDT",
      "side": "BUY",
      "type": "MARKET",
      "quoteOrderQty": "10"
    }
  },
  "policy_context": {
    "policy_refs": ["policy.symbol_allowlist", "policy.spot_testnet_only"]
  }
}
```

### 11.2 `/runs/resume`

```json
{
  "run_id": "run_hold_001",
  "resume_reason": "USER_APPROVED_ORDER",
  "patch_fields": {
    "approval": {
      "approved": true
    }
  }
}
```

### 11.3 `/runs/complete`

```json
{
  "run_id": "run_0f3b6f",
  "completion_payload": {
    "execution_result": {
      "status": "NEW",
      "orderId": 123456789,
      "clientOrderId": "test-order"
    }
  }
}
```

## 12. 현재 구현 메모

- FE 타입 일부는 아직 raw order response 성격의 이름을 유지하고 있다.
- 그러나 canonical public contract는 `OrderRunResponse` 다.
- Reports 페이지는 현재 `runId` 기준 단일 live report 조회가 연결되어 있다.
- Settings 화면은 현재 placeholder 단계지만, `GET /api/v1/testnet/config` public endpoint 자체는 이미 존재한다.
