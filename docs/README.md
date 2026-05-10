# Coin Agent 문서 레포지토리

> Binance Spot Testnet 전용 가상 자금 현물 주문·체결 테스트 기반 개인용 투자 보조 Agent 구현 문서 모음

## 문서 목적

이 레포지토리는 Coin Agent를 **Binance Spot Testnet 전용**으로 구현하기 위한 기준 문서 세트를 관리한다. 이 프로젝트는 **실거래 기능을 다루지 않으며**, 오직 **가상 자금 기반 현물 모의투자**만 다룬다. 모든 문서는 `https://testnet.binance.vision/api` 및 Binance Spot Testnet WebSocket 환경만 기준으로 작성한다.

## 절대 금지 사항

- 실거래 URL 사용 금지
- 실거래 API Key / Secret 사용 금지
- Binance Production REST/WebSocket Host 사용 금지
- 선물, 마진, 출금, 레버리지 관련 기능 문서화 금지

## 모의투자 전용 엔드포인트

| 구분 | 엔드포인트 |
|---|---|
| REST Base URL | `https://testnet.binance.vision/api` |
| WebSocket Streams | `wss://stream.testnet.binance.vision/ws` |
| WebSocket API | `wss://ws-api.testnet.binance.vision/ws-api/v3` |

## 문서 읽는 순서

1. `PROPOSAL.md` - 프로젝트 목적과 Binance Spot Testnet 전환된 기획 배경을 이해한다.
2. `SPEC.md` - 무엇을 구현해야 하는지 확인한다.
3. `ARCHITECTURE.md` - Agent, BE, FE, Binance Spot Testnet 관계를 확인한다.
4. `DATA.md` - REST 계약, 주문 파라미터, 응답 예시, DB 초안을 확인한다.
5. `FE.md`, `BE.md`, `AI.md` - 역할별 구현 기준을 확인한다.
6. `TEST_AND_DEMO.md` - 테스트와 발표 데모 흐름을 확인한다.

## 문서 역할 요약

| 문서 | 역할 | 주요 독자 |
|---|---|---|
| `README.md` | 문서 진입점, 환경 변수, 안전 수칙, 읽는 순서 | 전원 |
| `PROPOSAL.md` | 상위 기획 근거 문서 | 전원 |
| `SPEC.md` | 제품/기능 명세 | PM, FE, BE, AI |
| `ARCHITECTURE.md` | 전체 구조와 흐름 설명 | FE, BE, AI |
| `FE.md` | Next.js 기준 화면/상태/UI 명세 | FE |
| `BE.md` | FastAPI 기준 Binance Testnet 연동/주문 흐름 명세 | BE |
| `AI.md` | LangGraph Agent 및 리스크 게이트 명세 | AI |
| `DATA.md` | API 계약, 데이터 모델, ERD | FE, BE, AI |
| `TEST_AND_DEMO.md` | 테스트 체크리스트와 데모 시나리오 | 전원 |

## 구현 원칙 요약

- 거래소는 Binance Spot Testnet만 사용한다.
- 모든 주문은 가상 자금 기반 현물 주문 테스트만 다룬다.
- 실거래 URL, 실거래 API Key, 실거래 주문 기능은 문서 범위에서 제외한다.
- 사용자의 정책과 리스크 게이트를 통과하지 못하면 기본값은 무주문 또는 판단 보류다.
- 브라우저는 Binance API를 직접 호출하지 않고, 모든 호출은 BE를 통해 수행한다.

## API Key 생성 절차

1. `https://testnet.binance.vision/` 에 접속한다.
2. Binance Spot Testnet 계정으로 로그인한다.
3. API Management에서 Testnet용 API Key / Secret을 생성한다.
4. 생성된 키는 로컬 환경 변수에만 저장한다.
5. 실거래 Binance 계정 키와 혼용하지 않는다.

## 실행 및 환경 변수

### 권장 서비스 구성

- FE: Vite + React
- BE: FastAPI
- AI: LangGraph 실행 서비스
- DB: SQLite
- External: Binance Spot Testnet REST / WebSocket

### 환경 변수 목록

| 변수명 | 설명 | 필수 여부 |
|---|---|---:|
| `BINANCE_TESTNET_API_KEY` | Binance Spot Testnet API Key | 예 |
| `BINANCE_TESTNET_SECRET_KEY` | Binance Spot Testnet Secret Key | 예 |
| `BINANCE_TESTNET_REST_BASE_URL` | 기본값 `https://testnet.binance.vision/api` | 예 |
| `BINANCE_TESTNET_WS_STREAM_URL` | 기본값 `wss://stream.testnet.binance.vision/ws` | 예 |
| `BINANCE_TESTNET_WS_API_URL` | 기본값 `wss://ws-api.testnet.binance.vision/ws-api/v3` | 예 |
| `DATABASE_URL` | SQLite 연결 문자열 | 예 |
| `VITE_API_BASE_URL` | FE에서 호출할 BE 기본 URL | 예 |
| `AI_SERVICE_HTTP_URL` | BE가 호출하는 AI HTTP 엔드포인트 | 예 |
| `APP_ENV` | `local`, `demo`, `testnet` 중 하나 | 예 |
| `LOG_LEVEL` | 애플리케이션 로그 레벨 | 예 |

### 로컬 개발 기준

1. FE는 `.env` 또는 `.env.local`에 `VITE_API_BASE_URL`을 설정한다.
2. BE는 `.env`에 Binance Testnet Key, Secret, REST/WS base URL, `DATABASE_URL`을 설정한다.
3. AI 서비스는 BE와 동일 네트워크에서 HTTP 인터페이스만 제공한다.
4. DB는 SQLite를 사용한다.
5. 시세/호가/캔들 자동 갱신은 기본적으로 수동 새로고침 또는 사용자 액션 기반으로 처리한다.

### 실행 순서 기준

1. SQLite DB 준비
2. FastAPI 실행
3. LangGraph AI 서비스 실행
4. Vite 프론트엔드 실행
5. Binance Spot Testnet API Key 설정 확인
6. 잔고 조회 → 시세 조회 → 모의 주문 → 주문 상태 조회 → 취소 흐름 테스트 진행

## 빠른 시작 흐름

1. Spot Testnet API Key 생성
2. 환경 변수 설정
3. 계좌 잔고 조회
4. `BTCUSDT` 현재가/호가/캔들 조회
5. 소량의 현물 매수 모의 주문
6. 주문 상태 조회
7. 필요 시 주문 취소
8. WebSocket으로 시세 수신 확인

## 실수 방지 주의사항

### 반드시 지켜야 할 규칙

- REST 호출은 반드시 `https://testnet.binance.vision/api` 만 사용한다.
- 시세 스트림은 반드시 `wss://stream.testnet.binance.vision/ws` 만 사용한다.
- WebSocket API는 반드시 `wss://ws-api.testnet.binance.vision/ws-api/v3` 만 사용한다.
- 환경 변수 이름에 `TESTNET`이 들어간 값만 사용한다.
- API Key를 붙여넣기 전 문자열에 실거래 키가 아닌지 다시 확인한다.

### 사용 금지 예시

- `https://api.binance.com`
- `wss://stream.binance.com`
- `wss://ws-api.binance.com`
- 실거래 Binance API Key / Secret

## 확정 구현 기준

- 프로젝트 문서는 Binance Spot Testnet 전용으로 유지한다.
- 거래 심볼 표기는 REST에서 `BTCUSDT`, `ETHUSDT`처럼 대문자 심볼을 사용한다.
- WebSocket stream 이름은 `btcusdt@ticker`처럼 소문자 stream symbol을 사용한다.
- 기본 주문 예시는 Spot 시장가 매수/매도와 주문 상태 조회/취소까지로 제한한다.
- 실거래 기능, 출금, 선물, 마진은 문서에 포함하지 않는다.
