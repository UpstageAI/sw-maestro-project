# Coin Agent BE

Binance Spot Testnet 전용 FastAPI 백엔드. 가상 자금 기반 현물 주문 테스트를 위한 API 서버.

> **주의**: 이 서버는 Testnet 전용입니다. 실거래 Binance API(`api.binance.com`)는 절대 호출하지 않습니다.

## 기능

- Testnet 계정 잔고 조회
- 현재가 / 호가(Order Book) 조회
- 캔들(OHLCV) 데이터 조회
- 현물 주문 생성 / 상태 조회 / 취소
- WebSocket 스트림 연결 상태 조회 (`btcusdt@ticker` 자동 구독)
- 모든 거래 이력 SQLite 로컬 저장

## 기술 스택

| 항목 | 기술 |
|---|---|
| 프레임워크 | FastAPI 0.115 |
| 언어 | Python 3.12 |
| DB | SQLite (SQLAlchemy 2.0) |
| HTTP 클라이언트 | httpx (async) |
| WebSocket | websockets |
| 테스트 | pytest + pytest-asyncio |
| 인증 | HMAC-SHA256 (Binance signed endpoint) |

## 요구사항

- Python 3.12+
- Binance Spot Testnet API Key / Secret ([발급](https://testnet.binance.vision/))

## 설치 및 실행

```bash
# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
# .env 파일에 BINANCE_TESTNET_API_KEY, BINANCE_TESTNET_SECRET_KEY 입력

# 서버 실행
uvicorn app.main:app --reload --port 8000
```

서버 시작 시 자동으로:
1. SQLite 테이블 생성
2. `btcusdt@ticker` WebSocket 스트림 구독 시작 (자동 재연결 포함)

## 환경 변수

| 변수명 | 기본값 | 설명 |
|---|---|---|
| `BINANCE_TESTNET_API_KEY` | - | Testnet API Key (필수) |
| `BINANCE_TESTNET_SECRET_KEY` | - | Testnet Secret Key (필수) |
| `BINANCE_TESTNET_REST_BASE_URL` | `https://testnet.binance.vision/api` | REST 기준 URL |
| `BINANCE_TESTNET_WS_STREAM_URL` | `wss://stream.testnet.binance.vision/ws` | WebSocket 스트림 URL |
| `BINANCE_TESTNET_WS_API_URL` | `wss://ws-api.testnet.binance.vision/ws-api/v3` | WebSocket API URL |
| `DATABASE_URL` | `sqlite:///./coin_agent.db` | DB 연결 문자열 |
| `AI_SERVICE_HTTP_URL` | `http://localhost:8001` | AI 서비스 URL |
| `APP_ENV` | `local` | `local` \| `demo` \| `testnet` |
| `LOG_LEVEL` | `INFO` | 로그 레벨 |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | 추가 허용 오리진 목록. `APP_ENV=local`이면 `http://localhost:5173`, `http://127.0.0.1:5173` 가 자동 병합됨 |

## API 엔드포인트

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/health` | 헬스 체크 |
| GET | `/api/v1/testnet/account` | 계정 잔고 조회 |
| GET | `/api/v1/testnet/ticker/price` | 현재가 조회 |
| GET | `/api/v1/testnet/ticker/book` | 호가/Order Book 조회 |
| GET | `/api/v1/testnet/klines` | 캔들 데이터 조회 |
| POST | `/api/v1/testnet/orders` | 주문 생성 (AI Gateway 연동) |
| POST | `/api/v1/testnet/orders/resume` | HOLD run 재개 |
| GET | `/api/v1/testnet/orders/report` | runId 기준 최종 리포트 조회 |
| GET | `/api/v1/testnet/orders/status` | 주문 상태 조회 |
| DELETE | `/api/v1/testnet/orders` | 주문 취소 |
| GET | `/api/v1/testnet/stream/status` | WebSocket 스트림 상태 |

전체 명세: [`docs/api-spec.md`](docs/api-spec.md)  
Swagger UI: `http://localhost:8000/docs`

## 테스트

```bash
pytest tests/ -v
```

커버리지 확인:

```bash
pytest tests/ --cov=app --cov-report=term-missing
```

## 프로젝트 구조

```
BE/
├── app/
│   ├── main.py              # FastAPI 앱 진입점, 미들웨어, 예외 핸들러
│   ├── config.py            # 환경 변수 로드 및 검증
│   ├── database.py          # SQLite 연결 및 세션
│   ├── routers/             # API 라우터 (요청 수신 → 서비스 호출)
│   ├── services/            # 비즈니스 로직 (Binance 호출, DB 저장)
│   ├── models/              # Pydantic 요청/응답 스키마
│   └── db/                  # SQLAlchemy ORM 모델, CRUD
├── tests/                   # pytest 테스트
├── docs/                    # 설계 문서
├── .env.example
├── requirements.txt
└── CLAUDE.md
```

## 응답 포맷

성공 응답은 camelCase JSON으로 반환됩니다.

에러 응답:
```json
{
  "error_code": "REQUEST_FAILED",
  "message": "사람이 읽을 수 있는 메시지",
  "detail": "기술적 상세 내용",
  "request_id": "req_a1b2c3d4",
  "timestamp": "2026-01-01T00:00:00+00:00"
}
```

## 관련 문서

- [`docs/SPEC.md`](docs/SPEC.md) — 제품 요구사항
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — 전체 시스템 구조
- [`docs/BE.md`](docs/BE.md) — BE 구현 상세 기준
- [`docs/DATA.md`](docs/DATA.md) — API 계약, 데이터 모델, DB ERD
- [`docs/api-spec.md`](docs/api-spec.md) — 구현된 API 전체 명세
- [`docs/AI.md`](docs/AI.md) — AI 오케스트레이터 연동 기준
