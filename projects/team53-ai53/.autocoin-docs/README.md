# Coin Agent 루트 문서 안내

> Binance Spot Testnet 전용 주문 테스트 및 자연어 자동매매 실험 시스템의 canonical 문서 세트

## 문서 목적

이 문서는 현재 구현 기준의 전체 제품 진입점이다. FE, BE, AI, DB, Binance Testnet, run/report/session 계약, 자연어 자동매매 흐름, 그리고 아직 남아 있는 제약을 한 번에 설명할 수 있어야 한다. 특히 이 제품은 사용자가 자연어로 자동매매 의도를 시작하면, FE가 아니라 BE가 세션을 소유한 채 계속 재평가하고, 사용자가 중지할 수 있지만 BE 안전 규칙이 더 먼저 멈출 수도 있다는 점을 분명히 드러내야 한다.

## 핵심 원칙

- 거래소는 Binance Spot Testnet만 사용한다.
- FE는 Binance를 직접 호출하지 않는다.
- AI는 Binance 요청을 직접 제출하거나 서명하지 않는다.
- BE만 Binance 호출, 시그니처 생성, deterministic 재검증, 최종 실행 판정을 수행한다.
- BE의 방어 규칙은 단순 보조 검사가 아니라, AI 판단 뒤에도 반드시 다시 거치는 deterministic 재검증과 defensive rule base 다.
- 수동 주문과 자연어 자동매매 모두 run 중심 계약을 사용한다.

## 현재 구현 표면 요약

### FE 라우트

- `/dashboard`
- `/auto-trading`
- `/orders`
- `/reports`
- `/settings`

### 공개 BE API

- `GET /health`
- `GET /api/v1/testnet/account`
- `GET /api/v1/testnet/config`
- `GET /api/v1/testnet/ticker/price`
- `GET /api/v1/testnet/ticker/book`
- `GET /api/v1/testnet/klines`
- `POST /api/v1/testnet/orders`
- `POST /api/v1/testnet/orders/resume`
- `POST /api/v1/testnet/orders/auto`
- `POST /api/v1/testnet/orders/auto/session/start`
- `POST /api/v1/testnet/orders/auto/session/stop`
- `GET /api/v1/testnet/orders/auto/session`
- `GET /api/v1/testnet/orders/status`
- `GET /api/v1/testnet/orders/report`
- `DELETE /api/v1/testnet/orders`
- `GET /api/v1/testnet/stream/status`

### BE가 호출하는 AI HTTP API

- `POST /runs/start`
- `POST /runs/agentic/start`
- `POST /runs/resume`
- `POST /runs/complete`
- `GET /runs/{run_id}/checkpoints/order`
- `GET /runs/{run_id}/checkpoints/completion`

## 현재 제품 성숙도 요약

- 수동 주문 테스트는 run 기반으로 동작한다.
- 자연어 auto order 1회 실행이 구현되어 있다.
- 연속 자연어 자동매매 세션 start / stop / status 가 구현되어 있다.
- 이 연속 세션은 사용자가 자연어로 시작하고, 이후 각 tick 마다 fresh `run_id` 로 다시 판단한다.
- 각 auto tick 은 fresh `run_id` 로 수행된다.
- auto tick 시작 전 BE는 live account / price / book / 5분 klines snapshot 을 AI에 주입한다.
- 자연어 입력에서는 `traderId`, `inferredPersona` 가 추론될 수 있으며, 이후 세션은 그 판단 스타일을 이어서 사용한다.
- retryable `HOLD` 에서는 세션이 다음 tick 으로 이어질 수 있다.
- 사용자는 세션 stop 을 요청할 수 있지만, 세션은 BE defensive rule base 결과에 따라 더 일찍 `STOPPED` 될 수 있다.
- Reports 페이지는 `runId` 기준 단일 live report 조회다.
- cadence/history 전용 API는 아직 없다.
- 시간 경과에 따라 리포트가 누적되는 history/cadence UX 도 아직 구현되지 않았다.
- Settings 페이지는 placeholder 중심이며, BE의 `/config` endpoint 를 아직 FE가 live 호출하지 않는다.
- agentic run resume 는 현재 지원되지 않는다.

## 문서 구성

- `SPEC.md` — 제품 범위와 현재 구현 목표
- `ARCHITECTURE.md` — FE/BE/AI/Binance/DB 책임 경계와 runtime 흐름
- `DATA.md` — 공개 계약과 상태/세션 모델
- `FE.md` — 화면, UX, 페이지 성숙도
- `BE.md` — 공개 API와 실행 권한, session loop, Binance 재검증
- `AI.md` — AI HTTP 서비스, agentic/non-agentic run, checkpoint, 제약
- `TEST_AND_DEMO.md` — 테스트와 데모 기준
- `PROPOSAL.md` — 제품의 상위 기획 배경
