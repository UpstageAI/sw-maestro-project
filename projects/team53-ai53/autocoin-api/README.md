# Coin Agent BE

Binance Spot Testnet 전용 FastAPI 백엔드입니다. 이 서버는 수동 주문 테스트, run 기반 AI orchestration, 자연어 자동매매 세션 제어, 주문 상태/취소, 리포트 조회를 모두 담당합니다.

> **주의**: 이 서버는 Testnet 전용입니다. `api.binance.com` 같은 Production Binance 호스트는 설정 단계에서 차단됩니다.

## 기능

- Testnet 계정 잔고 조회
- 현재가 / 호가 / 캔들 조회
- 수동 주문 run 시작 (`POST /orders`)
- hold run resume (`POST /orders/resume`)
- 자연어 auto order 실행 (`POST /orders/auto`)
- 연속 자동매매 세션 start / stop / status (`/orders/auto/session/*`)
- run report 조회 (`GET /orders/report`)
- 주문 상태 조회 / 취소
- WebSocket stream 상태 조회

## 기술 스택

| 항목 | 기술 |
|---|---|
| 프레임워크 | FastAPI 0.115 |
| 언어 | Python 3.12 |
| DB | SQLite (SQLAlchemy 2.0) |
| HTTP 클라이언트 | httpx (async) |
| WebSocket | websockets |
| 테스트 | pytest + pytest-asyncio |
| 인증 | HMAC-SHA256 |

## 설치 및 실행

```bash
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

서버 시작 시 자동으로:

1. SQLite 테이블 생성
2. `btcusdt@ticker` WebSocket stream background task 시작

## 환경 변수

| 변수명 | 기본값 | 설명 |
|---|---|---|
| `BINANCE_TESTNET_API_KEY` | - | Testnet API Key |
| `BINANCE_TESTNET_SECRET_KEY` | - | Testnet Secret Key |
| `BINANCE_TESTNET_REST_BASE_URL` | `https://testnet.binance.vision/api` | REST 기준 URL |
| `BINANCE_TESTNET_WS_STREAM_URL` | `wss://stream.testnet.binance.vision/ws` | Stream URL |
| `BINANCE_TESTNET_WS_API_URL` | `wss://ws-api.testnet.binance.vision/ws-api/v3` | WS API URL |
| `DATABASE_URL` | `sqlite:///./coin_agent.db` | SQLite 연결 문자열 |
| `AI_SERVICE_HTTP_URL` | `http://localhost:8001` | 독립 AI 서비스 URL |
| `APP_ENV` | `local` | `local` \| `demo` \| `testnet` |
| `LOG_LEVEL` | `INFO` | 로그 레벨 |
| `CORS_ORIGINS` | local 기본 병합 | 허용 오리진 목록 |

## 공개 API

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/health` | 헬스 체크 |
| GET | `/api/v1/testnet/account` | 잔고 조회 |
| GET | `/api/v1/testnet/config` | Testnet 연결 기준 URL 조회 |
| GET | `/api/v1/testnet/ticker/price` | 현재가 조회 |
| GET | `/api/v1/testnet/ticker/book` | 호가/Depth 조회 |
| GET | `/api/v1/testnet/klines` | 캔들 조회 |
| POST | `/api/v1/testnet/orders` | 수동 주문 run 시작 |
| POST | `/api/v1/testnet/orders/resume` | hold run 재개 |
| POST | `/api/v1/testnet/orders/auto` | 자연어 auto order 1회 실행 |
| POST | `/api/v1/testnet/orders/auto/session/start` | 연속 자동매매 세션 시작 |
| POST | `/api/v1/testnet/orders/auto/session/stop` | 세션 중지 요청 |
| GET | `/api/v1/testnet/orders/auto/session` | 현재 세션 상태 조회 |
| GET | `/api/v1/testnet/orders/report` | persisted run report 조회 |
| GET | `/api/v1/testnet/orders/status` | 주문 상태 조회 |
| DELETE | `/api/v1/testnet/orders` | 주문 취소 |
| GET | `/api/v1/testnet/stream/status` | stream 상태 조회 |

Swagger UI: `http://localhost:8000/docs`

## 실행 권한 경계

- AI는 Binance를 직접 호출하지 않습니다.
- AI는 주문 제출 후보와 trace를 생성할 뿐입니다.
- BE만 Binance Testnet REST 호출, 서명, deterministic 재검증, 최종 제출을 수행합니다.
- `READY_FOR_BE` 는 실행 완료가 아니라 **BE 재검증 대기 상태**입니다.

## auto-trading 세션 구현 요약

- 세션 loop 는 BE가 소유합니다.
- 각 tick 은 fresh `run_id` 로 `POST /orders/auto` 흐름을 재사용합니다.
- auto tick 시작 전 BE는 실제 잔고/현재가/호가/5분 캔들 snapshot 을 수집해 AI request에 주입합니다.
- 세션은 `REPORT_READY`, `NO_ORDER`, 일부 retryable HOLD 에서 계속될 수 있습니다.
- agentic run resume 는 현재 지원되지 않습니다.

## 테스트

```bash
pytest tests/ -v
```

대표 검증 묶음:

```bash
pytest tests/test_orders_auto.py tests/test_auto_session.py tests/test_reports.py -v
```

## 관련 문서

- `docs/api-spec.md`
- `docs/ARCHITECTURE.md`
- `docs/AI.md`
- `docs/BE.md`
- `docs/DATA.md`
- `docs/TEST_AND_DEMO.md`
