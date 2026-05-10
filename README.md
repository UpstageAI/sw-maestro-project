# Coin Agent 루트 문서 안내

> Binance Spot Testnet 전용 주문 테스트 시스템의 canonical 문서 세트

## 문서 목적

이 문서는 루트 문서 세트의 진입점이다. 제품 범위, 권한 경계, API 계약, 현재 구현 성숙도를 한 번에 파악할 수 있게 돕는다.

## 문서 구성

- `SPEC.md`: 제품 범위와 요구사항
- `ARCHITECTURE.md`: FE, BE, AI, DB, Binance 간 책임 경계와 런타임 흐름
- `DATA.md`: 공용 API 계약과 데이터 모델
- `FE.md`: 화면, 사용자 흐름, 현재 UI 성숙도
- `BE.md`: 공개 API, Binance 연동, deterministic 재검증 원칙
- `AI.md`: 독립 HTTP AI 서비스, run 상태, resume 의미
- `TEST_AND_DEMO.md`: 테스트 기준과 데모 시나리오
- `PROPOSAL.md`: 기획 배경

## 핵심 원칙

- 거래소는 Binance Spot Testnet만 사용한다.
- FE는 Binance를 직접 호출하지 않는다.
- AI는 Binance 요청을 직접 제출하거나 서명하지 않는다.
- BE만 Binance 호출, 시그니처 생성, 최종 실행 판정을 수행한다.
- 주문 생성 API의 canonical 응답은 Binance 원본 주문 응답이 아니라 run 중심 응답이다.
- 주문 상태 조회와 주문 취소는 생성 API와 분리된 별도 공개 API로 유지한다.

## canonical 런타임 요약

### 공개 BE API

- `GET /health`
- `GET /api/v1/testnet/account`
- `GET /api/v1/testnet/config`
- `GET /api/v1/testnet/ticker/price`
- `GET /api/v1/testnet/ticker/book`
- `GET /api/v1/testnet/klines`
- `POST /api/v1/testnet/orders`
- `POST /api/v1/testnet/orders/resume`
- `GET /api/v1/testnet/orders/status`
- `GET /api/v1/testnet/orders/report`
- `DELETE /api/v1/testnet/orders`
- `GET /api/v1/testnet/stream/status`

### BE가 호출하는 AI HTTP API

- `POST /runs/start`
- `POST /runs/resume`
- `POST /runs/complete`

AI 서비스는 독립 HTTP 서비스이며, 현재 구현은 로컬 JSON 파일 기반 run 저장소를 사용한다.

## 주문 생성 계약의 canonical 기준

`POST /api/v1/testnet/orders` 는 Binance 원본 `POST /api/v3/order` payload를 그대로 반환하지 않는다. 이 엔드포인트는 run 단위 오케스트레이션 결과를 반환한다.

핵심 성공 응답 필드 예시는 다음과 같다.

```json
{
  "runId": "run_123",
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

같은 엔드포인트는 다음과 같은 run 상태도 반환할 수 있다.

- `HOLD`
- `NO_ORDER`
- `BE_REJECTED`
- `REPORT_READY`

## 현재 구현 성숙도 요약

- FE 주문 생성은 이미 run 중심 payload를 기대하는 방향으로 설계되어 있다.
- FE 주문 상태 조회와 주문 취소는 별도 API 흐름으로 분리되어 있다.
- FE Reports 페이지는 현재 `runId` 기준 단일 live report 조회가 연결되어 있다. cadence/history 전용 API는 아직 없어 placeholder를 표시한다.
- FE Settings 페이지는 현재 placeholder 상태다. 다만 BE에는 `GET /api/v1/testnet/config` 공개 API가 이미 존재한다.
- FE에서 `POST /api/v1/testnet/orders/resume` 연동은 canonical 계약에는 포함되지만, 현재 UI는 아직 완전하게 연결되지 않았다.
- AI resume는 이전 이력과 이전 trace 스냅샷을 보존하지만, 재개 후 현재 stage trace와 현재 verification 결과는 새로 계산되어 overwrite된다.
- AI run 상태는 로컬 JSON 파일에 저장되므로 같은 저장소 파일을 유지하는 한 프로세스 재시작 이후에도 non-agentic run resume를 이어갈 수 있다.

## 응답 명명 규칙

- 성공 payload는 camelCase를 사용한다.
- 현재 오류 payload 필드는 snake_case를 사용한다.

오류 응답 예시:

```json
{
  "error_code": "VALIDATION_ERROR",
  "message": "요청 파라미터가 올바르지 않습니다.",
  "detail": "body -> symbol: Field required",
  "request_id": "req_ab12cd34",
  "timestamp": "2026-05-09T10:00:00+00:00"
}
```

## 문서 사용법

설계 판단이 필요하면 `ARCHITECTURE.md` 를 먼저 본다. 응답 필드와 상태값을 확인할 때는 `DATA.md` 를 기준으로 본다. 화면 성숙도와 API 연동 범위를 판단할 때는 `FE.md`, 실행 권한과 Binance 연동 책임은 `BE.md`, run 상태와 resume 의미는 `AI.md` 를 기준으로 본다.
