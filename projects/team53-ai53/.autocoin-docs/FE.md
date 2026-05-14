# Coin Agent Frontend 명세

## 문서 목적

이 문서는 현재 구현 기준의 Frontend 역할, 페이지 구성, 현재 성숙도, BE API 의존성을 설명한다. 특히 초보 사용자도 이 제품이 무엇을 하는지 오해하지 않도록, FE 문구가 실행 권한 경계와 현재 한계를 쉬운 말로 드러내야 한다.

## 1. FE 역할

- 입력 수집
- 상태 polling
- 결과/리포트 표시
- 수동 주문과 연속 자연어 자동매매의 UX 분리
- 초보 사용자도 이해할 수 있는 설명 문구 유지

FE는 Binance를 직접 호출하지 않는다.

## 2. 현재 페이지 구성

| 페이지 | 경로 | 현재 상태 |
|---|---|---|
| Dashboard | `/dashboard` | live 조회 구현 |
| Auto Trading | `/auto-trading` | 연속 자동매매 세션 제어 구현 |
| Orders | `/orders` | 수동 주문 run + 상태/취소 구현 |
| Reports | `/reports` | `runId` 기준 단일 live report 조회 구현 |
| Settings | `/settings` | placeholder 중심, `/config` 미연동 |

## 3. FE가 호출하는 주요 API

- `GET /api/v1/testnet/account`
- `GET /api/v1/testnet/config` (현재 FE 미연동)
- `GET /api/v1/testnet/ticker/price`
- `GET /api/v1/testnet/ticker/book`
- `GET /api/v1/testnet/klines`
- `POST /api/v1/testnet/orders`
- `POST /api/v1/testnet/orders/resume`
- `POST /api/v1/testnet/orders/auto`
- `POST /api/v1/testnet/orders/auto/session/start`
- `POST /api/v1/testnet/orders/auto/session/stop`
- `GET /api/v1/testnet/orders/auto/session`
- `GET /api/v1/testnet/orders/report`
- `GET /api/v1/testnet/orders/status`
- `DELETE /api/v1/testnet/orders`
- `GET /api/v1/testnet/stream/status`

## 4. 수동 주문 UX

- `POST /orders` 는 raw Binance 응답이 아니라 run 중심 응답을 받는다.
- 현재 주요 상태 분기:
  - `HOLD`
  - `NO_ORDER`
  - `BE_REJECTED`
  - `REPORT_READY`
- `HOLD_REVIEW_REQUIRED`, `HOLD_DATA_INSUFFICIENT` 는 resume CTA 를 제공한다.

## 5. 자연어 자동매매 UX

`/auto-trading` 는 단건 요청 화면이 아니라 **backend-owned session control UI** 다.

현재 표시 항목:

- session status (`IDLE`, `ACTIVE`, `STOPPING`, `STOPPED`)
- tick interval
- tick count
- selected trader
- inferred persona 결과
- current raw text
- session timestamps
- latest run
- latest report
- stop reason / latest error
- ambiguity guidance

중요 제약:

- FE가 로컬 타이머로 거래 loop를 돌리지 않는다.
- FE는 session status만 polling 한다.
- 세션이 계속되는지/멈추는지는 BE가 결정한다.
- 사용자는 stop 을 누를 수 있지만, 실제 중단 사유는 user stop 이거나 BE safety stop 일 수 있다.

## 6. Reports 현재 상태

- `runId` query param 기준 단일 live report 조회
- cadence/history 전용 API 없음
- placeholder 영역은 그대로 노출
- 시간별 누적 리포트, 주기별 report accumulation, 과거 run history 축적 화면은 아직 구현되지 않았다.

## 7. Settings 현재 상태

- API base URL, 설명성 placeholder 중심
- BE `/config` endpoint 는 존재하지만 FE가 아직 이를 live 호출하지 않는다.

## 8. UI 문구 원칙

- Binance Spot Testnet 문구를 유지한다.
- AI가 실행권자인 것처럼 보이면 안 된다.
- `READY_FOR_BE` 는 실행 완료가 아니라 BE 재검증 대기 의미다.
- auto-trading session status와 latest run status를 혼동하지 않게 표시한다.
- 초보 사용자가 이해하기 어려운 내부 용어보다, "자동매매 시작", "백엔드가 계속 확인 중", "안전 규칙으로 중단될 수 있음" 같은 쉬운 한국어를 우선한다.
- persona 는 전용 선택기처럼 설명하지 말고, 자연어 입력에서 trader/style 이 추론된 결과로 설명한다.
- Reports는 하나의 run 결과를 보는 화면이지, 시간 흐름에 따라 누적 분석을 쌓아 보는 화면처럼 설명하면 안 된다.
