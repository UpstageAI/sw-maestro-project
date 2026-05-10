# Coin Agent Backend 명세

## 문서 목적

이 문서는 Backend의 공개 API, Binance 연동 책임, run orchestration 처리 방식을 정의한다.

## 1. BE 역할

BE는 Binance Spot Testnet과 직접 통신하는 유일한 계층이다. 동시에 FE와 AI 사이의 orchestration coordinator이며, 최종 실행 권한자다.

## 2. 실행 권한 원칙

- BE만 Binance REST 호출을 수행한다.
- BE만 `timestamp`, `signature`, `X-MBX-APIKEY` 를 처리한다.
- BE만 deterministic 재검증 후 실제 제출 여부를 확정한다.
- AI의 `READY_FOR_BE` 는 실행 허가가 아니라 제출 후보 상태다.

## 3. 공개 API 목록

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/health` | 서버 상태 |
| GET | `/api/v1/testnet/account` | 잔고 조회 |
| GET | `/api/v1/testnet/config` | Testnet 연결 기준 URL 조회 |
| GET | `/api/v1/testnet/ticker/price` | 현재가 조회 |
| GET | `/api/v1/testnet/ticker/book` | 호가 및 depth 조회 |
| GET | `/api/v1/testnet/klines` | 캔들 조회 |
| POST | `/api/v1/testnet/orders` | 주문 run 시작 |
| POST | `/api/v1/testnet/orders/resume` | hold run 재개 |
| GET | `/api/v1/testnet/orders/status` | 주문 상태 조회 |
| GET | `/api/v1/testnet/orders/report` | run report 조회 |
| DELETE | `/api/v1/testnet/orders` | 주문 취소 |
| GET | `/api/v1/testnet/stream/status` | stream 상태 확인 |

## 4. 주문 생성 API의 canonical 의미

`POST /api/v1/testnet/orders` 는 run 중심 공개 API다. 이 엔드포인트는 Binance 원본 `POST /v3/order` payload를 그대로 public response로 사용하지 않는다.

반환 기준은 `OrderRunResponse` 이다.

가능한 대표 상태:

- `HOLD`
- `NO_ORDER`
- `BE_REJECTED`
- `REPORT_READY`

실제로 Binance 제출이 일어난 경우에만 `orderId`, `symbol`, `status`, `type`, `side` 가 채워질 수 있다.

## 5. resume API의 canonical 의미

`POST /api/v1/testnet/orders/resume` 는 public contract에 포함되는 1급 엔드포인트다.

동작 원칙:

1. `runId` 에 해당하는 checkpoint 가 있어야 한다.
2. 해당 checkpoint 상태가 `HOLD` 여야 한다.
3. checkpoint 가 만료되지 않아야 한다.
4. BE는 AI `/runs/resume` 를 호출한다.
5. 반환된 lifecycle 에 따라 다시 hold 를 유지하거나, 재검증 및 제출을 이어간다.

현재 구현에서는 BE checkpoint 만으로 resume 가 완전하게 복구되는 것은 아니다. 다만 AI 서비스가 로컬 JSON run 저장소를 유지하는 한, AI 프로세스 재기동 이후에도 non-agentic 동일 run resume 를 이어갈 수 있다.

## 5A. config 조회 API의 canonical 의미

`GET /api/v1/testnet/config` 는 현재 서버가 사용하는 Testnet REST, WebSocket Stream, WebSocket API 기준 URL을 반환한다.

- 성공 응답은 camelCase `TestnetConfigResponse` 다.
- 이 endpoint 존재와 FE Settings 화면 연결 여부는 구분해서 문서화해야 한다.

## 5B. run report 조회 API의 canonical 의미

`GET /api/v1/testnet/orders/report` 는 `runId` 기준으로 persisted published report 를 반환한다.

- report 가 없으면 404 를 반환한다.
- FE Reports 페이지의 현재 live report 조회 상태와, cadence/history 미지원 상태를 구분해서 문서화해야 한다.

## 6. 내부 orchestration 흐름

### create

1. BE가 `runId` 생성
2. `request_context` 생성
3. `policy_context` 생성
4. AI `/runs/start` 호출
5. checkpoint 저장
6. lifecycle 처리

### READY_FOR_BE 처리

1. deterministic 재검증
2. 실패 시 `BE_REJECTED`
3. 통과 시 Binance 제출
4. 실행 결과를 AI `/runs/complete` 에 주입
5. report 및 checkpoint 저장

### HOLD 처리

- `holdReason` 과 함께 public response 반환
- 이후 `POST /orders/resume` 대상이 된다.

## 7. deterministic 재검증 범위

현재 구현 기준 예시는 다음과 같다.

- 허용 심볼 확인
- `exchangeInfo` 기반 최소 수량, 최소 notion 확인
- 잔고 확인
- 잘못된 파라미터 차단

AI가 통과시켜도 BE가 위 조건을 만족하지 않으면 `BE_REJECTED` 로 종료한다.

## 8. AI 연동 계약

BE는 AI에 다음 의미의 payload를 전달한다.

- `/runs/start`: `run_id`, `request_context`, `policy_context`
- `/runs/resume`: `run_id`, `resume_reason`, `patch_fields`
- `/runs/complete`: `run_id`, `completion_payload`

중요한 구현 사실:

- BE가 `policy_context` 를 만들어 AI에 주입한다.
- 현재 AI는 정책 아티팩트를 내부에서 직접 검색해 조립하는 서비스가 아니다.
- 문서 어디에서도 AI가 정책 아티팩트를 자체 회수한다고 쓰면 안 된다.

## 9. 상태 조회와 취소

### `GET /api/v1/testnet/orders/status`

- 주문 생성 run과 분리된 조회 API
- `symbol` 과 `orderId` 또는 `origClientOrderId` 를 사용한다.

### `DELETE /api/v1/testnet/orders`

- 주문 생성 run과 분리된 취소 API
- 특정 주문 취소 결과를 반환한다.

## 10. 응답 명명 규칙

- 성공 응답은 camelCase
- 현재 오류 응답은 snake_case

오류 응답 필드:

- `error_code`
- `message`
- `detail`
- `request_id`
- `timestamp`

## 11. 현재 구현 메모

- `POST /orders` 와 `POST /orders/resume` 는 둘 다 `OrderRunResponse` 로 응답한다.
- `GET /orders/status` 와 `DELETE /orders` 는 별도 응답 모델을 유지한다.
- config 조회용 public endpoint는 현재 존재한다.
- run report 조회용 public endpoint도 현재 존재한다.
- stream 상태는 별도 `GET /stream/status` 로 확인한다.
