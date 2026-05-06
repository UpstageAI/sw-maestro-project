# Coin Agent BE — Gemini 리뷰 가이드

이 문서는 `autocoin-api` (FastAPI 기반 Binance Spot Testnet 전용 백엔드)의 Gemini 코드 리뷰 기준을 정의한다.

---

## Review Comment Style & Language

- 모든 리뷰 코멘트는 **한국어로 작성한다.**
- **무엇이 어긋났는지**, **왜 문제인지**, **어떻게 맞추면 되는지**를 함께 제시한다.
- 사소한 제안에는 `[nit]` 접두어를 붙인다.
- 리뷰 우선순위: **보안** → **정확성** → **구조** → **가독성**

---

## 1. 프로젝트 전제

| 항목 | 기준 |
|---|---|
| 언어 | Python 3.12 |
| 프레임워크 | FastAPI |
| DB | SQLite + SQLAlchemy 2.x |
| 설정 관리 | pydantic-settings (`Settings` 클래스) |
| 거래소 | **Binance Spot Testnet 전용** |
| AI 연동 | LangGraph (별도 HTTP 서비스, `http://localhost:8001`) |

**핵심 제약**: 실거래 엔드포인트(`api.binance.com`, `stream.binance.com`, `ws-api.binance.com`)는 코드, 설정, 문서 어디에도 나타나면 안 된다.

---

## 2. 보안 체크포인트 (CRITICAL)

다음 항목은 발견 즉시 CRITICAL로 지적한다.

| 검사 항목 | 규칙 |
|---|---|
| 실거래 URL | `api.binance.com`, `stream.binance.com`, `ws-api.binance.com` 사용 금지 |
| API Key/Secret 하드코딩 | 코드에 직접 작성 금지. 반드시 환경 변수(`settings`) 경유 |
| `.env` 파일 커밋 | `.env` 파일은 커밋하지 않는다. `.env.example`만 허용 |
| 시그니처 노출 | HMAC 서명 결과나 Secret Key를 로그에 출력 금지 |
| Production key 감지 우회 | `config.py`의 `_validate_no_production_urls()` 로직을 삭제하거나 우회하는 코드 금지 |

---

## 3. 프로젝트 구조 규칙

```
app/
├── main.py          # FastAPI 앱 진입점, 라우터 등록
├── config.py        # pydantic-settings 기반 Settings
├── database.py      # SQLAlchemy 엔진, 세션 팩토리
├── db/
│   ├── models.py    # SQLAlchemy ORM 모델
│   └── crud.py      # DB CRUD 함수
├── models/          # Pydantic 요청/응답 스키마
├── routers/         # FastAPI 라우터 (엔드포인트)
└── services/        # 비즈니스 로직 / Binance 연동
tests/               # pytest 테스트
```

### 리뷰 체크포인트

- 비즈니스 로직은 `services/`에 두고, `routers/`에서는 요청/응답 처리만 한다.
- Binance API 직접 호출은 `services/`에서만 이루어져야 한다.
- `routers/`에서 `httpx` 또는 `requests`를 직접 호출하면 구조 위반이다.
- DB 접근은 `db/crud.py`를 경유해야 한다. 라우터나 서비스에서 직접 쿼리 작성 금지.

---

## 4. FastAPI / Python 코드 품질

### 4.1 라우터

- 모든 엔드포인트에 **응답 스키마**(`response_model`)를 명시해야 한다.
- 라우터 prefix는 `/api/v1/testnet`으로 고정한다.
- HTTP 상태 코드는 명시적으로 지정한다.

### 4.2 Pydantic 모델

- 요청/응답 스키마는 `app/models/`에 정의한다.
- `dict` 반환보다 Pydantic 모델 반환을 우선한다.
- 필드에 `Optional`을 쓸 때 기본값(`None`)을 명시한다.

### 4.3 설정

- 환경 변수는 반드시 `app.config.settings`를 통해 접근한다.
- `os.environ` 직접 접근은 `config.py` 외부에서 금지한다.
- Testnet URL 3종은 `settings`에 정의된 값을 사용한다.
  - `settings.binance_testnet_rest_base_url`
  - `settings.binance_testnet_ws_stream_url`
  - `settings.binance_testnet_ws_api_url`

### 4.4 타입 힌트

- 모든 함수 인자와 반환값에 타입 힌트를 작성한다.
- `Any` 사용은 정당한 이유 없이 금지한다.

### 4.5 에러 처리

- Binance API 호출 실패 시 `HTTPException`으로 변환하고, 원인을 로그에 남긴다.
- 빈 `except:` 또는 `except Exception: pass` 패턴은 금지한다.
- 에러 응답에 Binance Secret Key, 서명값, 내부 스택 트레이스를 포함하면 안 된다.

---

## 5. Binance Testnet 연동 규칙

### 5.1 REST 엔드포인트

| 기능 | Binance 엔드포인트 |
|---|---|
| 계정 잔고 | `GET /api/v3/account` |
| 현재가 | `GET /api/v3/ticker/price` |
| 최우선 호가 | `GET /api/v3/ticker/bookTicker` |
| 오더북 | `GET /api/v3/depth` |
| 캔들 | `GET /api/v3/klines` |
| 주문 생성 | `POST /api/v3/order` |
| 주문 조회 | `GET /api/v3/order` |
| 주문 취소 | `DELETE /api/v3/order` |
| 심볼 정보 | `GET /api/v3/exchangeInfo` |

### 5.2 WebSocket

- stream URL: `wss://stream.testnet.binance.vision/ws`
- stream 이름의 심볼은 **소문자**를 사용한다. (`btcusdt@ticker`, `btcusdt@kline_1m`)
- REST 요청의 심볼은 **대문자**를 사용한다. (`BTCUSDT`)

### 5.3 시그니처

- HMAC SHA256 서명은 `binance_auth_service`에서만 처리한다.
- `timestamp`는 밀리초 단위 Unix 시간이다.
- `signature`는 URL query string 마지막에 위치해야 한다.

### 5.4 주문 파라미터 검증

- `quantity`는 `minQty`, `stepSize`를 만족해야 한다.
- `price`는 `tickSize`를 만족해야 한다.
- 검증은 `GET /api/v3/exchangeInfo` 기준으로 수행한다.

---

## 6. 응답 포맷 규칙

- `/api/v1/testnet/*` 응답은 Binance 원본 payload를 그대로 반환하지 않고, **필요한 필드만 정규화**하여 반환한다.
- 주문 상태 값(`status`)은 Binance 원본 enum을 유지한다. (`NEW`, `FILLED`, `CANCELED` 등)
- 에러 응답은 아래 `ErrorResponse` 스키마를 따른다. (`docs/DATA.md §2.8` 기준)

```json
{
  "error_code": "BINANCE_TESTNET_REQUEST_FAILED",
  "message": "사람이 읽을 수 있는 메시지",
  "detail": "기술적 상세 내용 (로컬 환경에서만 노출)",
  "request_id": "req_xxx",
  "timestamp": "ISO8601"
}
```

---

## 7. 테스트 규칙

- 신규 기능에는 반드시 `tests/` 하위에 테스트를 추가한다.
- Binance API 호출은 테스트에서 mock 처리한다.
- 테스트 파일명은 `test_{모듈명}.py` 형식을 따른다.
- `pytest`와 `pytest-asyncio`를 사용한다.

---

## 8. Git / Issue / PR 규칙

### 브랜치

- 기본 브랜치는 `main`이다. `develop` 브랜치는 사용하지 않는다.
- 브랜치명: `{type}/{issue-number}-{description}` (예: `feat/3-order-service`)
- 브랜치명에 `#`을 포함하지 않는다.

### 커밋

- 형식: `{type}: 작업 내용 (#{issue-number})` (예: `feat: 주문 서비스 구현 (#3)`)
- 한 커밋에 한 가지 목적만 담는다.

### PR

- 제목: `[#issue-number] 총 작업 내용` (예: `[#3] 주문 서비스 구현`)
- 본문에 `Closes #...` 포함 필수
- Merge 대상은 항상 `main`

---

## 9. 리뷰에서 특히 중요한 실패 유형

1. **실거래 URL 혼입** — `api.binance.com` 등 production 호스트가 코드 또는 문서에 등장하는 경우
2. **API Key/Secret 노출** — 환경 변수 없이 값이 하드코딩된 경우
3. **서비스 계층 우회** — 라우터에서 Binance를 직접 호출하는 경우
4. **응답 스키마 누락** — `response_model` 없이 `dict`를 반환하는 경우
5. **타입 힌트 누락** — 함수 인자나 반환값에 타입이 없는 경우

---

## 확정 구현 기준

리뷰는 다음 조건을 모두 만족할 때 통과로 본다.

- 실거래 Binance URL이 코드, 설정, 문서 어디에도 없다.
- API Key/Secret이 코드에 직접 작성되어 있지 않다.
- 비즈니스 로직이 `services/`에 위치한다.
- 모든 엔드포인트에 `response_model`이 명시되어 있다.
- 신규 기능에 테스트가 존재한다.
- 브랜치/커밋/PR 규칙이 `git_convention.md`와 일치한다.
