# Coin Agent 시스템 아키텍처

## 문서 목적

이 문서는 Coin Agent의 canonical 구조와 현재 구현 경계를 설명한다. 기준은 Binance Spot Testnet 전용, FE 입력과 시각화, BE 실행 권한, AI 판단 보조의 분리다.

## 1. 시스템 구성

1. React Frontend
2. FastAPI Backend
3. Standalone HTTP AI Service
4. SQLite 저장소
5. Binance Spot Testnet REST / WebSocket

## 2. 권한 경계

| 계층 | 책임 | 금지 사항 |
|---|---|---|
| FE | 입력 수집, 결과 표시, 상태 분기 UI | Binance 직접 호출, 시그니처 생성 |
| BE | 공개 API, Binance 호출, 시그니처 생성, deterministic 재검증, checkpoint 저장 | AI 판단만 믿고 무검증 제출 |
| AI | 주문 의도 정규화, 리스크 판단, trace 생성, completion 보고 | Binance 직접 제출, Binance 서명, 정책 임의 완화 |
| DB | checkpoint, 주문 로그, 상태 로그, 리포트 저장 | 거래소 권한 판단 |
| Binance | 시장 데이터와 Testnet 주문 처리 | 내부 정책 해석 |

핵심 경계는 단순하다. FE는 Binance를 호출하지 않는다. AI는 Binance 요청을 제출하거나 서명하지 않는다. BE만 실행 권한을 가진다.

## 3. 공개 인터페이스 구조

### FE → BE

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

### BE → AI

- `POST /runs/start`
- `POST /runs/resume`
- `POST /runs/complete`

### BE → Binance

- `GET /v3/account`
- `GET /v3/ticker/price`
- `GET /v3/ticker/bookTicker`
- `GET /v3/depth`
- `GET /v3/klines`
- `GET /v3/exchangeInfo`
- `POST /v3/order`
- `GET /v3/order`
- `DELETE /v3/order`

## 4. 주문 생성의 canonical 흐름

1. FE가 `POST /api/v1/testnet/orders` 를 호출한다.
2. BE가 `runId` 를 생성하고 `request_context`, `policy_context` 를 만든다.
3. BE가 AI `/runs/start` 를 호출한다.
4. AI가 `HOLD`, `NO_ORDER`, `READY_FOR_BE` 중 하나를 반환한다.
5. `READY_FOR_BE` 인 경우에만 BE가 deterministic 재검증을 수행한다.
6. 재검증을 통과하면 BE가 Binance 주문을 제출한다.
7. 제출 결과 또는 차단 근거를 BE가 AI `/runs/complete` 로 주입한다.
8. BE가 최종 run 결과를 저장하고 FE에 run 중심 응답을 반환한다.

중요한 점은 `POST /api/v1/testnet/orders` 의 public contract가 run 결과라는 것이다. Binance 원본 주문 응답은 내부 실행 결과와 로그의 일부일 뿐이다.

## 5. resume의 canonical 흐름

1. AI 또는 BE가 `HOLD` 상태를 만든다.
2. BE는 checkpoint 를 `runId` 기준으로 저장한다.
3. FE 또는 외부 클라이언트가 `POST /api/v1/testnet/orders/resume` 를 호출한다.
4. BE는 checkpoint 존재 여부, 만료 여부, 현재 상태가 `HOLD` 인지 확인한다.
5. BE는 AI `/runs/resume` 로 `resumeReason`, `patchFields` 를 전달한다.
6. AI가 같은 `runId` 아래에서 새 상태를 계산한다.
7. 결과가 `READY_FOR_BE` 면 BE가 재검증과 실행을 이어간다.
8. 결과가 여전히 `HOLD` 또는 `NO_ORDER` 면 해당 run 상태를 그대로 반환한다.

`POST /api/v1/testnet/orders/resume` 는 보조 기능이 아니라 public API의 1급 엔드포인트다. 현재 구현에서는 BE checkpoint 와 AI 로컬 JSON run 저장소를 함께 사용하므로, 같은 저장소 파일이 유지되는 한 AI 프로세스 재시작 이후에도 non-agentic run resume 를 이어갈 수 있다. 다만 저장소 파일이 유실되거나 교체되면 BE checkpoint 만으로 동일 run 복구가 완전하게 보장되지는 않는다.

## 6. AI 서비스의 현재 구현 특성

- AI는 BE 내부 모듈이 아니라 별도 HTTP 서비스다.
- 현재 기본 run 저장소는 로컬 JSON 파일 기반이다.
- `start()` 는 run 상태를 메모리에 저장한다.
- `resume()` 는 기존 run을 읽어 이력을 추가한 뒤 다시 graph를 실행한다.
- `complete()` 는 `READY_FOR_BE` run에 completion payload를 주입한다.
- 현재 구현에는 `/runs/agentic/start` 도 존재하지만, 공통 FE→BE→AI 주문 흐름의 canonical 경로는 여전히 `/runs/start` 다.

현재 resume 의미는 다음과 같다.

- 이전 `request_context` 와 `policy_context` 는 유지된다.
- `resume_history` 는 누적된다.
- `decision_trace_history` 는 재개 직전 trace 스냅샷을 보존한다.
- 새 resume 실행 후 현재 `decision_trace` 와 현재 `verification_checks` 는 재계산되어 overwrite될 수 있다.

즉, 이력은 보존되지만 현재 stage 결과는 append-only가 아니다.

## 7. 저장 경계

### BE 저장

- checkpoint
- 주문 로그
- 주문 상태 조회 로그
- 주문 취소 로그
- run report

### AI 저장

- 현재 구현에서는 로컬 JSON 파일에 run 상태를 저장

이 차이 때문에 AI 보존성은 순수 in-memory 수준은 아니지만, BE SQLite checkpoint와 완전히 같은 durability 계층도 아니다.

## 8. 현재 FE 성숙도 위치

- Orders 플로우는 run 중심 응답을 받아야 하는 구조로 가고 있다.
- Reports 페이지는 현재 mock 기반이다. 다만 BE의 `GET /api/v1/testnet/orders/report` 는 이미 존재한다.
- Settings 페이지는 현재 placeholder를 표시한다. 다만 BE의 `GET /api/v1/testnet/config` 는 이미 존재한다.
- resume API는 canonical 구조에 포함되지만, 현재 FE 연결은 완전하지 않다.

## 9. 응답 명명 정책

- 성공 응답은 camelCase
- 현재 오류 응답은 snake_case

이 정책은 FE, BE, AI 설명 문서 전반에서 동일하게 유지한다.
