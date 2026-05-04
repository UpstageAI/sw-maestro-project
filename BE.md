# Coin Agent Backend 개발 명세

## 문서 목적

이 문서는 FastAPI 기반 Backend의 Binance Spot Testnet REST / WebSocket 연동, 인증/시그니처, 주문 테스트, 주문 상태 조회, 주문 취소, Python 예제 기준을 정의한다.

## 관련 문서

- 제품 요구사항: `SPEC.md`
- 아키텍처: `ARCHITECTURE.md`
- 데이터 계약: `DATA.md`

## 1. BE 역할

BE는 Binance Spot Testnet과 직접 통신하는 유일한 계층이다. 잔고 조회, 현재가/호가/캔들 조회, 주문 생성, 주문 상태 조회, 주문 취소, WebSocket 시세 수신을 담당한다.

## 2. REST / WebSocket 기준 엔드포인트

| 구분 | 값 |
|---|---|
| REST Base URL | `https://testnet.binance.vision/api` |
| WebSocket Streams | `wss://stream.testnet.binance.vision/ws` |
| WebSocket API | `wss://ws-api.testnet.binance.vision/ws-api/v3` |

## 3. 라우터 구조

| 라우터 | 역할 |
|---|---|
| `/api/v1/testnet/account` | Testnet 계정 잔고 조회 |
| `/api/v1/testnet/ticker/price` | 현재가 조회 |
| `/api/v1/testnet/ticker/book` | 호가 조회 |
| `/api/v1/testnet/klines` | 캔들 조회 |
| `/api/v1/testnet/orders` | 주문 생성 / 취소 |
| `/api/v1/testnet/orders/status` | 주문 상태 조회 |
| `/api/v1/testnet/stream/status` | WebSocket 연결 상태 확인 |

## 4. 서비스 모듈 구조

| 모듈 | 책임 |
|---|---|
| `binance_auth_service` | `timestamp`, `signature`, `X-MBX-APIKEY` 처리 |
| `account_service` | `GET /api/v3/account` 호출 |
| `market_service` | `ticker/price`, `bookTicker`, `depth`, `klines`, `exchangeInfo` 호출 |
| `order_service` | `POST /api/v3/order`, `GET /api/v3/order`, `DELETE /api/v3/order` 호출 |
| `stream_service` | WebSocket stream 구독 및 최근 이벤트 저장 |
| `report_service` | 주문/조회 결과를 설명 가능한 결과로 변환 |

## 5. 인증 방식

### 5.1 REST 인증

Binance Testnet의 signed endpoint 호출 시 다음 요소가 필요하다.

- `X-MBX-APIKEY` header
- `timestamp`
- `signature`
- 선택적으로 `recvWindow`

서명 방식은 HMAC SHA256 기준으로 구현한다.

### 5.2 WebSocket API 인증

이 문서 범위에서는 WebSocket API는 base URL만 정의하고, 실제 핵심 구현은 market data stream 수신에 집중한다. 주문 테스트는 REST 기준으로 수행한다.

## 6. 계정 잔고 조회

- 엔드포인트: `GET /api/v3/account`
- 주요 응답 필드: `balances[].asset`, `balances[].free`, `balances[].locked`
- signed endpoint이므로 header/signature/timestamp 필요

## 7. 현재가 / 호가 / 캔들 조회

### 현재가

- `GET /api/v3/ticker/price`
- 주요 파라미터: `symbol=BTCUSDT`

### 최우선 호가

- `GET /api/v3/ticker/bookTicker`
- 주요 응답: `bidPrice`, `bidQty`, `askPrice`, `askQty`

### 오더북

- `GET /api/v3/depth`
- 주요 파라미터: `symbol`, `limit`
- FE에서 말하는 orderbook은 이 `depth` snapshot을 의미한다.

### 캔들

- `GET /api/v3/klines`
- 주요 파라미터: `symbol`, `interval`, `limit`

## 8. 현물 매수/매도 주문 테스트

### 시장가 매수 예시

- 엔드포인트: `POST /api/v3/order`
- 필드: `symbol`, `side=BUY`, `type=MARKET`, `quoteOrderQty`, `timestamp`, `signature`

### 시장가 매도 예시

- 엔드포인트: `POST /api/v3/order`
- 필드: `symbol`, `side=SELL`, `type=MARKET`, `quantity`, `timestamp`, `signature`

### 지정가 주문 예시

- 엔드포인트: `POST /api/v3/order`
- 필드: `symbol`, `side`, `type=LIMIT`, `timeInForce=GTC`, `price`, `quantity`, `timestamp`, `signature`

### 주문 파라미터 검증 원칙

- `GET /api/v3/exchangeInfo`를 기준으로 `PRICE_FILTER`, `LOT_SIZE`, `MIN_NOTIONAL`을 검증한다.
- `quantity`는 `minQty`와 `stepSize`를 만족해야 한다.
- `price`는 `tickSize`를 만족해야 한다.
- `quoteOrderQty` 기반 주문도 최소 notion 조건을 만족해야 한다.

## 9. 주문 상태 조회

- 엔드포인트: `GET /api/v3/order`
- 필수 파라미터: `symbol`, `timestamp`, 그리고 `orderId` 또는 `origClientOrderId`
- 주요 응답 필드: `status`, `origQty`, `executedQty`, `price`, `type`, `side`

## 10. 주문 취소

- 엔드포인트: `DELETE /api/v3/order`
- 필수 파라미터: `symbol`, `timestamp`, 그리고 `orderId` 또는 `origClientOrderId`
- 취소 제한이 필요하면 `cancelRestrictions` 사용 가능

## 11. WebSocket 시세 수신

### Streams Endpoint

- `wss://stream.testnet.binance.vision/ws`

### 대표 stream 예시

- `btcusdt@ticker`
- `btcusdt@bookTicker`
- `btcusdt@kline_1m`

stream 이름의 심볼은 반드시 소문자를 사용한다.

## 12. Python 예제 코드

### 12.1 HMAC 시그니처 유틸

```python
import hmac
import hashlib
import time
from urllib.parse import urlencode


def sign_params(secret_key: str, params: dict) -> str:
    query_string = urlencode(params)
    return hmac.new(
        secret_key.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def make_timestamp() -> int:
    return int(time.time() * 1000)
```

### 12.2 잔고 조회

```python
import os
import requests

BASE_URL = os.environ["BINANCE_TESTNET_REST_BASE_URL"]
API_KEY = os.environ["BINANCE_TESTNET_API_KEY"]
SECRET_KEY = os.environ["BINANCE_TESTNET_SECRET_KEY"]

params = {"timestamp": make_timestamp()}
params["signature"] = sign_params(SECRET_KEY, params)

resp = requests.get(
    f"{BASE_URL}/v3/account",
    headers={"X-MBX-APIKEY": API_KEY},
    params=params,
    timeout=10,
)
print(resp.json())
```

### 12.3 현재가 조회

```python
resp = requests.get(
    f"{BASE_URL}/v3/ticker/price",
    params={"symbol": "BTCUSDT"},
    timeout=10,
)
print(resp.json())
```

### 12.4 시장가 매수 주문

```python
params = {
    "symbol": "BTCUSDT",
    "side": "BUY",
    "type": "MARKET",
    "quoteOrderQty": "50",
    "timestamp": make_timestamp(),
}
params["signature"] = sign_params(SECRET_KEY, params)

resp = requests.post(
    f"{BASE_URL}/v3/order",
    headers={"X-MBX-APIKEY": API_KEY},
    params=params,
    timeout=10,
)
print(resp.json())
```

### 12.5 주문 상태 조회

```python
params = {
    "symbol": "BTCUSDT",
    "orderId": 123456,
    "timestamp": make_timestamp(),
}
params["signature"] = sign_params(SECRET_KEY, params)

resp = requests.get(
    f"{BASE_URL}/v3/order",
    headers={"X-MBX-APIKEY": API_KEY},
    params=params,
    timeout=10,
)
print(resp.json())
```

### 12.6 주문 취소

```python
params = {
    "symbol": "BTCUSDT",
    "orderId": 123456,
    "timestamp": make_timestamp(),
}
params["signature"] = sign_params(SECRET_KEY, params)

resp = requests.delete(
    f"{BASE_URL}/v3/order",
    headers={"X-MBX-APIKEY": API_KEY},
    params=params,
    timeout=10,
)
print(resp.json())
```

### 12.7 WebSocket ticker 수신

```python
import json
from websocket import create_connection

ws = create_connection("wss://stream.testnet.binance.vision/ws/btcusdt@ticker")
message = ws.recv()
print(json.loads(message))
ws.close()
```

## 13. 실수 방지 주의사항

- `https://api.binance.com` 사용 금지
- `wss://stream.binance.com` 사용 금지
- 실거래 API Key 사용 금지
- Testnet 심볼 예시와 stream 소문자 규칙을 혼동하지 않기
- `quoteOrderQty`와 `quantity` 사용 위치를 혼동하지 않기

## 14. 확정 구현 기준

- 로컬 개인용 Agent에서만 실행한다.
- 주문 테스트는 Binance Spot Testnet REST 기준으로만 수행한다.
- 시세 stream 수신은 WebSocket Streams endpoint 기준으로 수행한다.
- 실거래 기능은 문서와 구현 모두에서 제외한다.

## 15. 응답 포맷 기준

- `/api/v1/testnet/*` 응답은 FE 친화적인 정규화 포맷으로 반환한다.
- Binance 원본 전체 payload는 로그/SQLite에 보관할 수 있지만, 기본 API 응답은 필요한 필드만 노출한다.
- 주문 상태 값은 Binance 원본 enum을 유지한다.
