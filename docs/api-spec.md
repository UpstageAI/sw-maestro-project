# API Specification

Coin Agent BE — Binance Spot Testnet 전용 백엔드 API 명세.

- Base URL: `http://localhost:8000`
- 성공 응답은 **camelCase JSON**
- 인증: 서버가 환경 변수의 API Key / Secret으로 Binance Testnet에 서명하여 호출 (클라이언트는 별도 인증 불필요)

---

## 구현 상태

| 엔드포인트 | 상태 |
|---|---|
| `GET /health` | ✅ 구현 완료 |
| `GET /api/v1/testnet/account` | ✅ 구현 완료 |
| `GET /api/v1/testnet/ticker/price` | ✅ 구현 완료 |
| `GET /api/v1/testnet/ticker/book` | ✅ 구현 완료 |
| `GET /api/v1/testnet/klines` | ✅ 구현 완료 |
| `POST /api/v1/testnet/orders` | ✅ 구현 완료 (AI Gateway 연동) |
| `POST /api/v1/testnet/orders/resume` | ✅ 구현 완료 (HOLD run resume) |
| `GET /api/v1/testnet/orders/report` | ✅ 구현 완료 (persisted published report 조회) |
| `GET /api/v1/testnet/orders/status` | ✅ 구현 완료 |
| `DELETE /api/v1/testnet/orders` | ✅ 구현 완료 |
| `GET /api/v1/testnet/stream/status` | ✅ 구현 완료 |

---

## 공통 에러 응답

HTTP 4xx / 5xx 시 아래 형식으로 반환됩니다.

```json
{
  "error_code": "REQUEST_FAILED",
  "message": "사람이 읽을 수 있는 메시지",
  "detail": "기술적 상세 내용 (local 환경에서만 노출)",
  "request_id": "req_a1b2c3d4",
  "timestamp": "2026-01-01T00:00:00+00:00"
}
```

| error_code | HTTP | 상황 |
|---|---|---|
| `VALIDATION_ERROR` | 422 | 요청 파라미터 오류 |
| `REQUEST_FAILED` | 4xx | 일반 요청 실패 (Binance 에러 포함) |
| `INTERNAL_SERVER_ERROR` | 500 | 서버 내부 오류 |

---

## 허용 값 참조

### 심볼 (`symbol`)

REST 파라미터는 **대문자**로 전달합니다.

권장 심볼: `BTCUSDT`, `ETHUSDT`

### 캔들 주기 (`interval`)

`1m`, `3m`, `5m`, `15m`, `30m`, `1h`, `2h`, `4h`, `6h`, `8h`, `12h`, `1d`, `3d`, `1w`, `1M`

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

| 필드 | 타입 | 값 |
|---|---|---|
| `status` | `string` | 항상 `"ok"` |
| `env` | `string` | `"local"` \| `"demo"` \| `"testnet"` |

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

### 에러 응답

| HTTP | errorCode | 상황 |
|---|---|---|
| 500 | `INTERNAL_SERVER_ERROR` | Binance Testnet 연결 실패 |

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

### 에러 응답

| HTTP | errorCode | 상황 |
|---|---|---|
| 422 | `VALIDATION_ERROR` | `symbol` 파라미터 누락 |
| 500 | `INTERNAL_SERVER_ERROR` | Binance Testnet 연결 실패 또는 유효하지 않은 심볼 |

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

### 에러 응답

| HTTP | errorCode | 상황 |
|---|---|---|
| 422 | `VALIDATION_ERROR` | `symbol` 파라미터 누락 |
| 500 | `INTERNAL_SERVER_ERROR` | Binance Testnet 연결 실패 또는 유효하지 않은 심볼 |

---

## GET /api/v1/testnet/klines

캔들(OHLCV) 데이터를 조회합니다.

### 쿼리 파라미터

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|---|---|---|---|---|
| `symbol` | `string` | ✅ | - | 심볼 대문자 (`BTCUSDT`) |
| `interval` | `string` | ✅ | - | 캔들 주기 (허용 값 참조) |
| `limit` | `integer` | ❌ | `100` | 반환할 캔들 수 (최대 `1000`) |

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

### 에러 응답

| HTTP | errorCode | 상황 |
|---|---|---|
| 422 | `VALIDATION_ERROR` | `symbol` 또는 `interval` 파라미터 누락 |
| 500 | `INTERNAL_SERVER_ERROR` | Binance Testnet 연결 실패 또는 유효하지 않은 심볼/주기 |

---

## POST /api/v1/testnet/orders

현물 주문을 생성합니다. AI의 policy/risk 판단을 거친 뒤 BE가 Binance Testnet에 최종 제출합니다.

**내부 흐름:**
1. BE가 `run_id`를 생성하고 AI에 run을 시작
2. AI가 policy → risk → evaluator 단계를 거쳐 결과 반환
3. `READY_FOR_BE`: BE가 exchangeInfo/잔고 재검증 후 Binance에 주문 제출
4. `HOLD`: FE에 보류 상태 반환 → `POST /orders/resume`로 재개
5. `NO_ORDER` / `BE_REJECTED`: 차단 사유와 함께 반환

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
| `symbol` | `string` | ✅ | 심볼 대문자 (`BTCUSDT`, `ETHUSDT`) |
| `side` | `"BUY" \| "SELL"` | ✅ | 매수/매도 |
| `type` | `"MARKET" \| "LIMIT"` | ✅ | 주문 유형 |
| `quantity` | `string` | 조건부 | 수량 (LIMIT 필수, MARKET은 `quoteOrderQty`와 택1) |
| `quoteOrderQty` | `string` | 조건부 | USDT 기준 금액 (MARKET 전용) |
| `price` | `string` | 조건부 | 가격 (LIMIT 필수) |
| `timeInForce` | `"GTC" \| "IOC" \| "FOK"` | 조건부 | 체결 조건 (LIMIT 필수) |

**유효성 규칙:**
- LIMIT: `quantity`, `price`, `timeInForce` 모두 필수
- MARKET: `quantity` 또는 `quoteOrderQty` 중 하나 필수

### 응답 `200`

`lifecycleStatus`에 따라 포함 필드가 다릅니다.

**주문 제출 성공 (`REPORT_READY`):**
```json
{
  "runId": "run_abc123",
  "lifecycleStatus": "REPORT_READY",
  "orderId": 123456789,
  "symbol": "BTCUSDT",
  "status": "NEW",
  "type": "LIMIT",
  "side": "BUY",
  "holdReason": null,
  "reasonCodes": []
}
```

**AI 보류 (`HOLD`):**
```json
{
  "runId": "run_abc123",
  "lifecycleStatus": "HOLD",
  "holdReason": "HOLD_REVIEW_REQUIRED",
  "orderId": null,
  "reasonCodes": []
}
```

**주문 차단 (`NO_ORDER` 또는 `BE_REJECTED`):**
```json
{
  "runId": "run_abc123",
  "lifecycleStatus": "NO_ORDER",
  "reasonCodes": ["RISK_THRESHOLD_EXCEEDED"],
  "orderId": null
}
```

| 필드 | 타입 | 설명 |
|---|---|---|
| `runId` | `string` | AI run 식별자. `HOLD` 시 resume에 사용 |
| `lifecycleStatus` | `string` | `REPORT_READY` \| `HOLD` \| `NO_ORDER` \| `BE_REJECTED` |
| `holdReason` | `string \| null` | `HOLD_REVIEW_REQUIRED` \| `HOLD_DATA_INSUFFICIENT` |
| `orderId` | `number \| null` | Binance 주문 ID (`REPORT_READY` 시에만 존재) |
| `symbol` | `string \| null` | 심볼 |
| `status` | `string \| null` | Binance 주문 상태 |
| `type` | `string \| null` | 주문 유형 |
| `side` | `string \| null` | 매수/매도 |
| `reasonCodes` | `string[]` | 차단/보류 사유 코드 |

| `lifecycleStatus` | 의미 | FE 처리 |
|---|---|---|
| `REPORT_READY` | 주문 제출 완료 | `orderId`로 상태 조회 가능 |
| `HOLD` | AI 보류 — 사람 검토 또는 데이터 보완 필요 | `runId` 보관 후 `POST /orders/resume` 호출 |
| `NO_ORDER` | AI가 주문 불가 판단 | `reasonCodes` 표시 후 종료 |
| `BE_REJECTED` | AI 통과 후 BE 재검증에서 차단 | `reasonCodes` 표시 후 종료 |

### 에러 응답

| HTTP | errorCode | 상황 |
|---|---|---|
| 422 | `VALIDATION_ERROR` | 요청 파라미터 오류 (LIMIT에 `price` 누락 등) |
| 500 | `INTERNAL_SERVER_ERROR` | AI 서비스 연결 실패 |
| 502 | `REQUEST_FAILED` | Binance Testnet 제출 실패 |

---

## POST /api/v1/testnet/orders/resume

`HOLD` 상태의 주문 run을 재개합니다.
FE가 사용자 승인 또는 보완 데이터를 받은 후 호출합니다.

### 요청 Body

**사용자 승인 (`HOLD_REVIEW_REQUIRED` 해소):**
```json
{
  "runId": "run_abc123",
  "resumeReason": "USER_APPROVED_ORDER",
  "patchFields": {
    "approval": { "approved": true }
  }
}
```

**데이터 보완 (`HOLD_DATA_INSUFFICIENT` 해소):**
```json
{
  "runId": "run_abc123",
  "resumeReason": "USER_PROVIDED_DATA",
  "patchFields": {
    "supplementalUserInput": { "additionalInfo": "..." }
  }
}
```

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `runId` | `string` | ✅ | `POST /orders` 응답에서 받은 run 식별자 |
| `resumeReason` | `string` | ✅ | 재개 사유 (`USER_APPROVED_ORDER`, `USER_PROVIDED_DATA` 등) |
| `patchFields` | `object` | ✅ | AI에 전달할 보완 데이터 |

### 응답 `200`

`POST /orders`와 동일한 응답 형식.

### 에러 응답

| HTTP | errorCode | 상황 |
|---|---|---|
| 404 | `REQUEST_FAILED` | `runId`를 찾을 수 없음 |
| 400 | `REQUEST_FAILED` | HOLD 상태가 아닌 run에 resume 시도 |
| 410 | `REQUEST_FAILED` | Checkpoint 만료 (기본 60분) |
| 500 | `INTERNAL_SERVER_ERROR` | AI 서비스 연결 실패 |

---

## GET /api/v1/testnet/orders/report

`runId` 기준으로 저장된 최종 리포트를 조회합니다.

- 이 엔드포인트는 raw checkpoint 전체를 반환하지 않고, 저장된 published report만 반환합니다.
- `clientOrderId` 는 공개 응답에 포함하지 않습니다.
- `HOLD` 와 `NO_ORDER` 는 `report.userSummary` 가 비어 있으면 evaluator 요약으로 fallback 할 수 있습니다.

### 쿼리 파라미터

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `runId` | `string` | ✅ | `POST /orders` 또는 `POST /orders/resume` 결과에서 받은 run 식별자 |

### 응답 `200`

```json
{
  "runId": "run_abc123",
  "report": {
    "lifecycleStatus": "NO_ORDER",
    "holdReason": null,
    "reasonCodes": ["SYMBOL_NOT_ALLOWED"],
    "userSummary": "BUY DOGEUSDT 1 USDT 평가 완료. 결과: NO_ORDER",
    "decisionTrace": {
      "policy": {
        "reasonCodes": ["ORDER_INTENT_NORMALIZED", "POLICY_GROUNDED"],
        "evidenceRefs": ["policy_context.policy_refs[0]", "trader_principles"],
        "finalAction": "PASS",
        "notes": null
      },
      "risk": {
        "reasonCodes": ["SYMBOL_NOT_ALLOWED"],
        "evidenceRefs": ["verification_checks[-1]"],
        "finalAction": "NO_ORDER",
        "notes": null
      },
      "evaluator": {
        "reasonCodes": ["EVALUATOR_LLM_FALLBACK"],
        "evidenceRefs": ["evaluator_review"],
        "finalAction": "NO_ORDER",
        "notes": null
      },
      "execution": {
        "reasonCodes": [],
        "evidenceRefs": [],
        "finalAction": "",
        "notes": null
      },
      "runSummary": {
        "reasonCodes": ["RUN_COMPLETE"],
        "evidenceRefs": ["evaluator_review", "decision_trace"],
        "finalAction": "NO_ORDER",
        "notes": null
      }
    },
    "order": null
  }
}
```

### 필드 설명

| 필드 | 타입 | 설명 |
|---|---|---|
| `runId` | `string` | run 식별자 |
| `report.lifecycleStatus` | `string` | `HOLD` \| `NO_ORDER` \| `BE_REJECTED` \| `REPORT_READY` \| `FAILED` |
| `report.holdReason` | `string \| null` | `HOLD` 인 경우 상세 사유 |
| `report.reasonCodes` | `string[]` | 최종 상태 요약 코드 |
| `report.userSummary` | `string \| null` | 사용자용 요약 문장 |
| `report.decisionTrace` | `object \| null` | 단계별 trace 요약 |
| `report.order` | `object \| null` | 주문이 실제 제출된 경우의 공개 주문 결과 |
| `report.order.orderId` | `number \| null` | Binance 주문 ID |
| `report.order.symbol` | `string \| null` | 심볼 |
| `report.order.status` | `string \| null` | Binance 주문 상태 |
| `report.order.type` | `string \| null` | 주문 유형 |
| `report.order.side` | `string \| null` | 매수/매도 |

### 에러 응답

| HTTP | errorCode | 상황 |
|---|---|---|
| 404 | `REQUEST_FAILED` | `runId` 자체를 찾을 수 없음 |
| 404 | `REQUEST_FAILED` | checkpoint는 있으나 persisted report 가 없음 |

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

### 에러 응답

| HTTP | errorCode | 상황 |
|---|---|---|
| 422 | `VALIDATION_ERROR` | `orderId`와 `origClientOrderId` 모두 누락 |
| 500 | `INTERNAL_SERVER_ERROR` | Binance Testnet 연결 실패 또는 존재하지 않는 주문 |

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

### 에러 응답

| HTTP | errorCode | 상황 |
|---|---|---|
| 422 | `VALIDATION_ERROR` | `orderId`와 `origClientOrderId` 모두 누락 |
| 500 | `INTERNAL_SERVER_ERROR` | Binance Testnet 연결 실패, 이미 체결/취소된 주문, 존재하지 않는 주문 |

---

## GET /api/v1/testnet/stream/status

서버의 WebSocket 스트림 연결 상태를 반환합니다.  
서버 시작 시 `btcusdt@ticker`를 자동 구독하며, 연결이 끊기면 5초 후 재연결을 시도합니다.

> FE는 이 엔드포인트를 폴링하여 실시간 시세 수신 여부를 확인할 수 있습니다.  
> `lastEvent`의 `c` 필드가 현재가입니다.

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
    "o": "79000.00",
    "h": "81000.00",
    "l": "78500.00",
    "v": "1234.56",
    "q": "98765432.00"
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
| `streamName` | `string \| null` | 구독 중인 스트림 이름 (소문자) |
| `lastEvent` | `object \| null` | 가장 최근 수신한 WebSocket 이벤트 원본 |
| `lastEvent.c` | `string` | 현재가 (close price) |
| `lastEvent.o` | `string` | 24시간 시가 |
| `lastEvent.h` | `string` | 24시간 고가 |
| `lastEvent.l` | `string` | 24시간 저가 |
| `lastEvent.v` | `string` | 24시간 거래량 (base asset) |
| `lastEvent.q` | `string` | 24시간 거래대금 (quote asset) |
