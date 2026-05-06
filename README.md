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
| `FE.md` | React 기준 화면/상태/UI 명세 | FE |
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

## 왜 이 구조가 agentic 인가

- 이 시스템은 단순히 프롬프트를 순서대로 호출하는 체인이 아니라, 하나의 `run_id` 아래에서 상태를 이어 가는 Agent run이다.
- 각 Agent는 자기 단계의 입력을 읽고, 허용된 필드만 쓰며, `decision_trace`와 `verification_checks`를 남긴다.
- LLM은 컨텍스트를 검색하고 후보 action path를 제안할 수 있지만, 실제 실행 여부는 deterministic rule 기반 Risk Engine과 BE 재검증이 결정한다.
- 따라서 `PASS`는 실행 완료가 아니라 `READY_FOR_BE` 성격의 제안이다.

## 최신 문서 계약 요약

- `HOLD`는 상위 상태이며, 실제 원인은 `HOLD_REVIEW_REQUIRED` 또는 `HOLD_DATA_INSUFFICIENT`로 구분한다.
- 모든 주문 테스트 run은 `run_id`로 추적하며, resume는 동일 `run_id` 기준으로 진행한다.
- AI는 Binance를 직접 호출하지 않고, 정규화 도구와 구조화 schema 계약 위에서만 동작한다.
- `BE_REJECTED`는 AI `PASS` 이후 BE 재검증에서만 생성된다.
- 검증 기준과 상태별 기대 결과는 `TEST_AND_DEMO.md`를 기준으로 본다.

## Agent와 실행 권한 분리 요약

| 주체 | 할 수 있는 일 | 할 수 없는 일 |
|---|---|---|
| Policy/Planning Agent | 정책 검색, 입력 정규화, 후보 action path 제안 | 주문 제출 확정 |
| Market/Risk Agent | 정책/시장/잔고 근거 평가, `HOLD` 또는 `PASS` 제안 | Binance 서명, 제출 |
| Execution/Report Agent | 실행 결과 해석, 보고서 작성 | 조건 변경 후 재주문 |
| BE + rule engine | deterministic 검증, 서명, 제출, 재검증 | LLM 추론에 실행 권한 위임 |

## 리포트 단위와 cadence 요약

- 기본 보고 단위는 **1 `run_id` = 1 주문 테스트 run** 이다.
- 중간 보고 단위는 Agent 단계별 `decision_trace.policy`, `decision_trace.risk`, `decision_trace.execution` 이다.
- canonical 보고 cadence는 request accepted, policy retrieval complete, policy complete, risk gate complete, evaluator complete, BE revalidation complete, final report ready 순서를 따른다.
- 사용자 화면이나 요약 리포트는 이 canonical cadence의 일부만 간단히 보여줄 수 있다.
- 휴먼 QA는 각 cadence에서 `hold_reason`, `BE_REJECTED`, `verification_checks`가 설명 가능하게 보이는지 확인한다.

## API Key 생성 절차

1. `https://testnet.binance.vision/` 에 접속한다.
2. Binance Spot Testnet 계정으로 로그인한다.
3. API Management에서 Testnet용 API Key / Secret을 생성한다.
4. 생성된 키는 로컬 환경 변수에만 저장한다.
5. 실거래 Binance 계정 키와 혼용하지 않는다.

## 실행 및 환경 변수

### 권장 서비스 구성

- FE: React
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
| `FRONTEND_API_BASE_URL` | FE에서 호출할 BE 기본 URL | 예 |
| `AI_SERVICE_HTTP_URL` | BE가 호출하는 AI HTTP 엔드포인트 | 예 |
| `APP_ENV` | `local`, `demo`, `testnet` 중 하나 | 예 |
| `LOG_LEVEL` | 애플리케이션 로그 레벨 | 예 |

### 로컬 개발 기준

1. FE는 React 개발 환경에서 사용하는 env 파일에 `FRONTEND_API_BASE_URL`을 설정한다.
2. BE는 `.env`에 Binance Testnet Key, Secret, REST/WS base URL, `DATABASE_URL`을 설정한다.
3. AI 서비스는 BE와 동일 네트워크에서 HTTP 인터페이스만 제공한다.
4. DB는 SQLite를 사용한다.
5. 시세/호가/캔들 자동 갱신은 기본적으로 수동 새로고침 또는 사용자 액션 기반으로 처리한다.

### 실행 순서 기준

1. SQLite DB 준비
2. FastAPI 실행
3. LangGraph AI 서비스 실행
4. React FE 실행
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
- `run_id`, `hold_reason`, `decision_trace` 같은 핵심 계약 용어는 문서 간 동일하게 유지한다.
