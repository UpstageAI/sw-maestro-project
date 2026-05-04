# Coin Agent 테스트 및 데모 시나리오

## 문서 목적

이 문서는 Binance Spot Testnet 전용 Coin Agent의 테스트 전략, Python 예제 검증, 주문 테스트 체크리스트, 발표 데모 흐름을 정의한다.

## 관련 문서

- 요구사항: `SPEC.md`
- 데이터 계약: `DATA.md`
- 구현 기준: `FE.md`, `BE.md`, `AI.md`

## 1. 테스트 원칙

- 모든 테스트는 Binance Spot Testnet에서만 수행한다.
- 실거래 URL과 실거래 API Key는 테스트 환경에 포함하지 않는다.
- 주문 생성, 상태 조회, 주문 취소는 반드시 가상 자금 환경에서만 검증한다.
- 실거래 기능은 테스트 대상이 아니다.

## 2. 핵심 기능 테스트

| 테스트 ID | 대상 | 검증 내용 | 관련 요구사항 |
|---|---|---|---|
| T-01 | API Key 설정 | Testnet Key 환경 변수 인식 | FR-01 |
| T-02 | 잔고 조회 | `GET /api/v3/account` 응답 확인 | FR-02 |
| T-03 | 현재가 조회 | `ticker/price` 응답 확인 | FR-03 |
| T-04 | 호가 조회 | `bookTicker` / `depth` 응답 확인 | FR-04 |
| T-05 | 캔들 조회 | `klines` 응답 확인 | FR-05 |
| T-06 | 현물 주문 테스트 | Spot 매수/매도 주문 성공 | FR-06, FR-07 |
| T-07 | 주문 상태 조회 | `orderId` 기준 상태 응답 확인 | FR-08 |
| T-08 | 주문 취소 | 취소 응답 확인 | FR-09 |
| T-09 | WebSocket 시세 수신 | ticker 또는 kline 이벤트 수신 | FR-10 |
| T-10 | Python 예제 | 예제 코드가 Testnet URL만 사용하는지 확인 | FR-11, FR-12 |

## 3. 테스트 체크리스트

### 환경 체크

- `BINANCE_TESTNET_REST_BASE_URL`이 `https://testnet.binance.vision/api`인지 확인
- `BINANCE_TESTNET_WS_STREAM_URL`이 `wss://stream.testnet.binance.vision/ws`인지 확인
- `BINANCE_TESTNET_WS_API_URL`이 `wss://ws-api.testnet.binance.vision/ws-api/v3`인지 확인
- API Key가 Testnet 발급 키인지 확인

### 기능 체크

- 잔고 조회 성공
- 현재가 조회 성공
- 호가 조회 성공
- 캔들 조회 성공
- 시장가 매수 주문 성공
- 시장가 매도 주문 성공
- 지정가 주문 생성 성공
- 주문 상태 조회 성공
- 주문 취소 성공
- WebSocket 이벤트 수신 성공

### 안전 체크

- 실거래 URL 문자열 미포함
- 실거래 API Key 사용 흔적 없음
- WebSocket stream 심볼 소문자 사용 확인
- REST 심볼 대문자 사용 확인

## 4. Python 예제 테스트

- 잔고 조회 예제 실행
- 현재가 조회 예제 실행
- 시장가 매수 예제 실행
- 주문 상태 조회 예제 실행
- 주문 취소 예제 실행
- WebSocket ticker 수신 예제 실행

## 5. Binance Spot Testnet 실패 테스트

- 잘못된 API Key 사용 시 인증 실패 확인
- 잘못된 `timestamp` 사용 시 요청 실패 확인
- 서명 누락 시 실패 확인
- 잘못된 `symbol` 사용 시 실패 확인
- 부족한 잔고에서 주문 시 실패 확인
- WebSocket 연결 실패 시 수동 조회 fallback 안내 확인

## 6. E2E 테스트

### E2E-01 Testnet 설정부터 잔고 조회까지

1. Testnet API Key 설정
2. `/account` 조회
3. 잔고 카드 표시 확인

### E2E-02 시세 조회부터 시장가 매수까지

1. `BTCUSDT` 현재가 조회
2. 호가 조회
3. 시장가 매수 주문 전송
4. 주문 결과 표시 확인

### E2E-03 주문 상태 조회와 취소

1. 지정가 주문 생성
2. `orderId` 기준 주문 상태 조회
3. 취소 요청
4. `CANCELED` 상태 확인

### E2E-03A 대체 식별자 기준 조회

1. 주문 생성
2. `origClientOrderId` 기준 주문 상태 조회
3. 동일 식별자로 취소 요청 가능 여부 확인

### E2E-04 WebSocket 시세 수신

1. `btcusdt@ticker` stream 연결
2. 이벤트 수신
3. FE에 최신 이벤트 표시 확인

## 7. 발표 데모 시나리오

### 데모 1. Spot Testnet 환경 확인

- Testnet 전용 URL과 API Key 경고 배너 설명
- 환경 설정 화면 확인

### 데모 2. 잔고와 시세 조회

- `BTCUSDT` 현재가, orderbook depth, 캔들 조회
- Testnet 잔고 확인

### 데모 3. 현물 매수 주문 테스트

- 시장가 매수 주문 수행
- 주문 응답 확인
- 주문 상태 조회

### 데모 4. 주문 취소

- 지정가 주문 생성
- 취소 요청
- 취소 결과 확인

### 데모 5. WebSocket 시세 수신

- `btcusdt@ticker` 이벤트 실시간 수신 시연

## 8. 데모용 초기 데이터

- 기본 심볼: `BTCUSDT`, `ETHUSDT`
- 기본 interval: `1m`
- 테스트용 quote 금액: `50`
- 테스트용 수량 예시: `0.001`

## 9. 백업 플랜

- REST 호출 실패 시 직전 정상 응답 JSON을 데모용 백업으로 사용
- WebSocket 실패 시 동일 심볼의 REST 조회로 대체
- 주문 취소 실패 시 상태 조회 결과로 미체결 상태를 설명

## 10. 확정 구현 기준

- 발표 데모는 반드시 Spot Testnet 환경에서만 수행한다.
- 예제 코드는 모두 Testnet URL만 사용한다.
- 실거래 기능은 문서와 시연 모두에서 배제한다.
