# Coin Agent Frontend 개발 명세

## 문서 목적

이 문서는 React 기반 Frontend의 페이지, 컴포넌트, UI 상태, Binance Spot Testnet 전용 시각화 요구사항을 정의한다.

## 관련 문서

- 요구사항: `SPEC.md`
- 아키텍처: `ARCHITECTURE.md`
- API 계약: `DATA.md`

## 1. FE 역할

FE는 사용자가 Binance Spot Testnet 설정, 잔고 조회, 시세 조회, 현물 주문 테스트, 주문 상태 조회, 주문 취소, WebSocket 시세 확인을 쉽게 수행할 수 있도록 돕는다. 모든 외부 API 호출은 반드시 BE를 통해 수행한다.

## 2. 페이지 목록

| 페이지 | 경로 예시 | 목적 |
|---|---|---|
| 환경 설정 | `/settings` | Testnet 환경 변수 설정 상태 확인, base URL 표시 |
| 대시보드 | `/dashboard` | 잔고, 현재가, orderbook, 캔들, stream 상태 표시 |
| 주문 테스트 | `/orders` | 현물 매수/매도 주문 생성, 주문 상태 조회, 취소 |
| 리포트/로그 | `/reports` | 주문 결과, 에러, 테스트 기록 확인 |

## 3. 화면 흐름

```mermaid
flowchart LR
    A[환경 설정] --> B[대시보드]
    B --> C[주문 테스트]
    C --> D[주문 상태 조회]
    D --> E[주문 취소]
    E --> F[리포트/로그]
```

## 4. 주요 컴포넌트

| 컴포넌트 | 목적 | 표시 내용 |
|---|---|---|
| `EnvironmentCard` | Testnet 환경 상태 확인 | REST/WS base URL, 서버 환경 변수 설정 상태 |
| `BalanceCard` | 계좌 잔고 확인 | `asset`, `free`, `locked` |
| `PriceCard` | 현재가 표시 | `symbol`, `price` |
| `OrderBookCard` | orderbook 표시 | bids / asks depth snapshot |
| `KlineChart` | 캔들 시각화 | OHLCV |
| `OrderForm` | Spot 주문 테스트 | `symbol`, `side`, `type`, `quantity`, `quoteOrderQty`, `price` |
| `OrderStatusPanel` | 주문 상태 조회 | `orderId` 또는 `origClientOrderId`, `status`, `executedQty` |
| `CancelOrderPanel` | 주문 취소 | `symbol`, `orderId` 또는 `origClientOrderId` |
| `StreamStatusCard` | WebSocket 연결 상태 | stream name, latest event |

## 5. 화면별 사용자 흐름

### 5.1 환경 설정 화면

1. 사용자가 Testnet Key의 서버 설정 상태를 확인한다.
2. 시스템은 현재 Testnet base URL을 읽기 전용으로 보여준다.
3. FE는 API Key 원문을 입력받거나 표시하지 않는다.
4. 실거래 URL이 아님을 경고 배너로 항상 노출한다.

### 5.2 대시보드 화면

1. 사용자가 `BTCUSDT` 또는 `ETHUSDT`를 선택한다.
2. 시스템은 잔고, 현재가, orderbook depth, 캔들 요약을 표시한다.
3. WebSocket 연결 상태를 별도 카드로 보여준다.

### 5.3 주문 테스트 화면

1. 사용자가 주문 타입을 선택한다.
2. 시장가 매수 시 `quoteOrderQty`, 시장가 매도 시 `quantity`를 입력한다.
3. 지정가 주문 시 `price`, `quantity`, `timeInForce`를 입력한다.
4. 주문 결과는 즉시 로그 영역에 표시한다.

### 5.4 리포트/로그 화면

1. 최근 주문 테스트 이력을 시간순으로 보여준다.
2. 실패 원인과 Binance 에러 코드를 함께 표시한다.

## 6. UI 상태 정의

| 상태 | 정의 | UI 처리 원칙 |
|---|---|---|
| 로딩 | BE 응답 대기 중 | 스켈레톤 또는 spinner |
| 빈 상태 | 아직 조회/주문 이력 없음 | 시작 가이드 표시 |
| 성공 | 응답 정상 수신 | 카드/차트/표 표시 |
| 부분 오류 | 일부 API 실패 | 오류 배너 + 마지막 정상 데이터 |
| 전체 오류 | 핵심 API 실패 | 실거래 금지 경고와 함께 재시도 안내 |

## 7. UI/UX 원칙

- 항상 “Binance Spot Testnet” 문구를 상단에 표시한다.
- 실거래가 아님을 배너로 명확히 표시한다.
- 주문 버튼은 필수 파라미터가 모두 채워져야 활성화한다.
- stream 이름은 소문자, REST 심볼은 대문자로 설명한다.
- 수익 보장이나 공격적 투자 표현은 사용하지 않는다.

## 8. 디자인 시스템 요약

- 위험/실수 방지 배너는 빨간색 또는 주황색 경고 톤 사용
- 정상 상태 카드는 중립/청색 계열 사용
- 주문 결과는 상태별 배지 사용: `NEW`, `FILLED`, `CANCELED`, `REJECTED`
- 숫자는 문자열 응답을 화면에서 정규화해 표시하되, 원본 값도 확인 가능하도록 한다.

## 9. FE에서 호출하는 API 요약

| API | 목적 |
|---|---|
| `GET /api/v1/testnet/account` | 잔고 조회 |
| `GET /api/v1/testnet/ticker/price` | 현재가 조회 |
| `GET /api/v1/testnet/ticker/book` | orderbook depth 조회 |
| `GET /api/v1/testnet/klines` | 캔들 조회 |
| `POST /api/v1/testnet/orders` | Spot 주문 테스트 |
| `GET /api/v1/testnet/orders/status` | 주문 상태 조회 |
| `DELETE /api/v1/testnet/orders` | 주문 취소 |
| `GET /api/v1/testnet/stream/status` | WebSocket 연결 상태 확인 |

## 10. 확정 구현 기준

- 기본 심볼 예시는 `BTCUSDT`와 `ETHUSDT`를 사용한다.
- 시세 자동 갱신은 기본적으로 수동 조회 버튼 기반으로 처리한다.
- 실시간 데이터는 보조 기능으로 WebSocket 카드에서만 표시한다.
- FE는 Binance API Key/Secret 원문을 입력받거나 재표시하지 않는다.
