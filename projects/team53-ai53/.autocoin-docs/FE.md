# Coin Agent Frontend 명세

## 문서 목적

이 문서는 Frontend의 canonical 역할과 현재 구현 성숙도를 함께 설명한다. 기준은 화면이 실행 권한을 오해시키지 않는 것이다.

## 1. FE 역할

FE는 입력, 조회, 시각화, 상태 분기 UX를 담당한다. FE는 Binance를 직접 호출하지 않으며, 모든 데이터는 BE 공개 API를 통해 받는다.

## 2. 페이지 구성

| 페이지 | 목적 | 현재 상태 |
|---|---|---|
| Settings | Testnet 환경과 서버 연결 상태 표시 | BE config endpoint는 존재하지만, 현재 FE는 placeholder 중심 read-only 표시 |
| Dashboard | 잔고, 현재가, 호가, 캔들, stream 상태 표시 | live 연동 대상 |
| Orders | 주문 생성, 상태 조회, 취소 | 주문 생성은 run 계약 대상, 상태/취소는 separate API |
| Reports | run 리포트와 cadence 표시 | `runId` 기준 단일 live report 조회 연결, cadence/history는 placeholder |

## 3. FE가 호출해야 하는 API

| API | 목적 |
|---|---|
| `GET /api/v1/testnet/account` | 잔고 조회 |
| `GET /api/v1/testnet/ticker/price` | 현재가 조회 |
| `GET /api/v1/testnet/ticker/book` | 호가 및 depth 조회 |
| `GET /api/v1/testnet/klines` | 캔들 조회 |
| `POST /api/v1/testnet/orders` | 주문 run 시작 |
| `POST /api/v1/testnet/orders/resume` | hold run 재개 |
| `GET /api/v1/testnet/orders/status` | 주문 상태 조회 |
| `DELETE /api/v1/testnet/orders` | 주문 취소 |
| `GET /api/v1/testnet/stream/status` | stream 상태 조회 |

## 4. 주문 생성 UX의 canonical 기준

FE는 `POST /api/v1/testnet/orders` 를 호출한 뒤 아래 중 하나를 처리해야 한다.

- `HOLD`
- `NO_ORDER`
- `BE_REJECTED`
- `REPORT_READY`

즉, 주문 생성 성공 UX는 raw Binance order success만 의미하지 않는다. FE는 run 상태를 중심으로 분기해야 한다.

### 권장 표시 항목

- `runId`
- `lifecycleStatus`
- `holdReason`
- `reasonCodes`
- 필요 시 `orderId`, `symbol`, `status`, `type`, `side`

## 5. 상태 조회와 취소 UX의 canonical 기준

- 주문 상태 조회는 생성 API와 별개다.
- 주문 취소도 생성 API와 별개다.
- 상태 조회와 취소는 특정 주문 식별자 중심 UX다.
- 생성 API의 run 상태와 조회/취소 API의 주문 상태를 혼동하면 안 된다.

## 6. hold와 resume UX 기준

### `HOLD_REVIEW_REQUIRED`

- 사용자 승인 또는 거절 CTA를 보여준다.
- 승인 후 `POST /api/v1/testnet/orders/resume` 로 같은 `runId` 를 재개한다.

### `HOLD_DATA_INSUFFICIENT`

- 재조회 또는 보완 입력 CTA를 보여준다.
- 필요한 값을 모은 뒤 `POST /api/v1/testnet/orders/resume` 로 재개한다.

현재 FE 구현은 이 canonical resume 흐름을 문서상 기준으로 삼되, 실제 UI 연결은 아직 완성되지 않았다.

## 7. 현재 구현 기준 메모

### Orders

- 현재 FE 코드는 `placeOrder()` 에서 여전히 raw order response 타입 이름을 일부 사용한다.
- 하지만 BE 실제 응답과 제품 계약은 run 중심 payload다.
- 따라서 문서 기준은 구현 의도와 BE 계약을 따라 run 중심으로 고정한다.
- 현재 FE는 `HOLD` 상태에 대해서만 dedicated resume CTA를 제공한다.
- `NO_ORDER`, `BE_REJECTED`, `REPORT_READY` 는 현재 주로 session order log를 통해 확인한다.

### Reports

- Reports 페이지는 현재 `runId` 기준 단일 live report 조회를 사용한다.
- cadence/history 전용 API는 아직 없으므로 해당 영역은 placeholder로 남아 있다.

### Settings

- Settings 페이지는 현재 Backend API base URL 과 설명성 placeholder만 보여준다.
- BE의 `GET /api/v1/testnet/config` 는 존재하지만, FE는 현재 그 endpoint를 호출해 실제 값을 렌더링하지 않는다.

## 8. UI 문구 원칙

- 항상 Binance Spot Testnet 문구를 보여준다.
- AI가 실행권자인 것처럼 보이게 하면 안 된다.
- `READY_FOR_BE` 는 실행 완료가 아니라 BE 재검증 대기라는 뜻으로 표시한다.
- `BE_REJECTED` 는 일반 실패와 구분해서 보여준다.

## 9. 응답 명명 처리 원칙

- 성공 응답은 camelCase로 소비한다.
- 오류 응답은 현재 snake_case를 그대로 처리한다.

예시:

- 성공: `runId`, `lifecycleStatus`, `holdReason`, `reasonCodes`
- 오류: `error_code`, `request_id`

## 10. FE가 지켜야 할 경계

- Binance URL을 코드에 직접 들고 있지 않는다.
- API Key, Secret 원문을 입력받거나 저장하지 않는다.
- Binance 서명이나 timestamp 생성 로직을 FE에 두지 않는다.
- Reports의 현재 상태가 단일 live report 조회 + cadence/history placeholder 임을 숨기지 않는다.
