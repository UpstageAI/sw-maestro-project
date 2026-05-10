# CLAUDE.md — Coin Agent BE

## 프로젝트 개요

Binance Spot Testnet 전용 FastAPI 백엔드. 가상 자금 기반 현물 주문 테스트만 다룬다.
실거래 기능은 문서와 구현 모두에서 제외한다.

## 절대 금지

- `https://api.binance.com` 사용 금지
- `wss://stream.binance.com` 사용 금지
- 실거래 API Key / Secret 코드에 하드코딩 금지
- 선물, 마진, 출금, 레버리지 관련 기능 구현 금지

## 기준 엔드포인트

| 구분 | 값 |
|---|---|
| REST Base URL | `https://testnet.binance.vision/api` |
| WebSocket Streams | `wss://stream.testnet.binance.vision/ws` |
| WebSocket API | `wss://ws-api.testnet.binance.vision/ws-api/v3` |

## 프로젝트 구조

```
BE/
├── app/
│   ├── main.py              # FastAPI 앱 진입점
│   ├── config.py            # 환경 변수 로드 및 검증
│   ├── database.py          # SQLite 연결
│   ├── routers/             # API 라우터
│   │   ├── account.py       # GET /api/v1/testnet/account
│   │   ├── ticker.py        # GET /api/v1/testnet/ticker/*
│   │   ├── klines.py        # GET /api/v1/testnet/klines
│   │   ├── orders.py        # POST/GET/DELETE /api/v1/testnet/orders
│   │   └── stream.py        # GET /api/v1/testnet/stream/status
│   ├── services/            # 비즈니스 로직
│   │   ├── binance_auth_service.py  # HMAC SHA256 서명
│   │   ├── account_service.py       # 계정 잔고 조회
│   │   ├── market_service.py        # 시세/호가/캔들
│   │   ├── order_service.py         # 주문 생성/조회/취소
│   │   ├── stream_service.py        # WebSocket 스트림
│   │   └── report_service.py        # 결과 설명 변환
│   ├── models/
│   │   ├── requests.py      # Pydantic request 스키마
│   │   └── responses.py     # Pydantic response 스키마
│   └── db/
│       ├── models.py        # SQLAlchemy ORM
│       └── crud.py          # DB CRUD 함수
├── tests/                   # pytest 테스트
├── .env.example
├── requirements.txt
└── CLAUDE.md
```

## API 라우터 목록

| 라우터 | 메서드 | 역할 |
|---|---|---|
| `/api/v1/testnet/account` | GET | Testnet 계정 잔고 조회 |
| `/api/v1/testnet/ticker/price` | GET | 현재가 조회 |
| `/api/v1/testnet/ticker/book` | GET | 호가/orderbook 조회 |
| `/api/v1/testnet/klines` | GET | 캔들 조회 |
| `/api/v1/testnet/orders` | POST | 주문 생성 |
| `/api/v1/testnet/orders/status` | GET | 주문 상태 조회 |
| `/api/v1/testnet/orders` | DELETE | 주문 취소 |
| `/api/v1/testnet/stream/status` | GET | WebSocket 연결 상태 |

## 환경 변수

`.env` 파일에 설정. `.env.example` 참조.

| 변수명 | 설명 |
|---|---|
| `BINANCE_TESTNET_API_KEY` | Testnet API Key |
| `BINANCE_TESTNET_SECRET_KEY` | Testnet Secret Key |
| `BINANCE_TESTNET_REST_BASE_URL` | `https://testnet.binance.vision/api` |
| `BINANCE_TESTNET_WS_STREAM_URL` | `wss://stream.testnet.binance.vision/ws` |
| `BINANCE_TESTNET_WS_API_URL` | `wss://ws-api.testnet.binance.vision/ws-api/v3` |
| `DATABASE_URL` | `sqlite:///./coin_agent.db` |
| `AI_SERVICE_HTTP_URL` | AI 서비스 HTTP URL |
| `APP_ENV` | `local` \| `demo` \| `testnet` |
| `LOG_LEVEL` | `INFO` |

## DB 테이블

| 테이블 | 역할 |
|---|---|
| `testnet_configs` | Testnet 설정 저장 |
| `balance_snapshots` | 잔고 스냅샷 |
| `price_snapshots` | 시세 스냅샷 |
| `spot_orders` | 주문 요청/응답 로그 |
| `order_status_logs` | 주문 상태 조회 이력 |
| `cancel_logs` | 취소 이력 |
| `stream_events` | WebSocket 이벤트 로그 |
| `reports` | 결과 설명 리포트 |

## 인증 방식

모든 signed endpoint에 HMAC SHA256 서명 적용.

```
X-MBX-APIKEY: {API_KEY}
timestamp: {ms}
signature: HMAC_SHA256(SECRET_KEY, query_string)
```

## 심볼 표기 규칙

- REST 파라미터: 대문자 (`BTCUSDT`, `ETHUSDT`)
- WebSocket stream 이름: 소문자 (`btcusdt@ticker`, `btcusdt@kline_1m`)

## 응답 포맷

모든 `/api/v1/testnet/*` 응답은 FE 친화적 정규화 포맷으로 반환.
Binance 원본 payload 전체는 SQLite 로그에만 보관.

에러 응답:
```json
{
  "error_code": "BINANCE_TESTNET_REQUEST_FAILED",
  "message": "사람이 읽을 수 있는 메시지",
  "detail": "기술적 상세 내용",
  "request_id": "req_xxx",
  "timestamp": "ISO8601"
}
```

## Git 컨벤션

- 브랜치: `feat/{issue-number}-{description}` / `fix/{issue-number}-{description}`
- 커밋: `feat: 작업 내용 (#issue-number)`
- PR 제목: `[#issue-number] 총 작업 내용`
- PR 본문: `Closes #issue-number`
- `develop` 브랜치 사용하지 않음, 항상 `main`에서 분기

## 개발 규칙

- 모든 Binance 호출은 `services/` 레이어에서만 수행
- 라우터는 서비스를 호출하고 응답을 정규화하는 역할만
- 실거래 URL 감지 시 즉시 실행 차단 (config 검증 단계에서)
- 주문 생성 전 반드시 리스크 게이트 통과 확인
- Testnet REST 실패 시 신규 주문 중단

## 테스트

```bash
pytest tests/ -v
```

- 단위 테스트: `tests/test_auth.py`, `test_account.py`, `test_market.py`, `test_orders.py`, `test_stream.py`
- Testnet 직접 호출 테스트는 `.env` 설정 후 실행
- 커버리지 80% 이상 목표

## 실행

```bash
pip install -r requirements.txt
cp .env.example .env  # 환경 변수 설정
uvicorn app.main:app --reload --port 8000
```

## 관련 문서

- `docs/SPEC.md` — 제품 요구사항
- `docs/ARCHITECTURE.md` — 전체 시스템 구조
- `docs/BE.md` — BE 구현 상세 기준
- `docs/DATA.md` — API 계약, 데이터 모델, DB ERD
- `docs/AI.md` — AI 오케스트레이터 연동 기준
- `docs/TEST_AND_DEMO.md` — 테스트 체크리스트, 데모 시나리오
