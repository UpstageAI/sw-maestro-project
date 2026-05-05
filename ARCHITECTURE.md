# Coin Agent 시스템 아키텍처

## 문서 목적

이 문서는 Coin Agent MVP의 전체 시스템 구조와 FE/BE/AI/DB/Binance Spot Testnet의 책임 경계를 설명한다. 이 프로젝트는 **Binance Spot Testnet 전용 가상 자금 현물 주문 테스트** 구조를 가진다.

## 관련 문서

- 요구사항: `SPEC.md`
- 데이터 계약: `DATA.md`
- FE 구현 기준: `FE.md`
- BE 구현 기준: `BE.md`
- AI 구현 기준: `AI.md`

## 1. 아키텍처 개요

Coin Agent는 다음 다섯 계층으로 구성된다.

1. React 기반 Frontend
2. FastAPI 기반 Backend API
3. LangGraph 기반 AI Orchestrator
4. SQLite 저장소
5. Binance Spot Testnet REST / WebSocket

핵심 원칙은 다음과 같다.

- FE는 입력과 시각화에 집중한다.
- BE는 Binance Spot Testnet REST/WebSocket 연동과 시그니처 처리, 주문 테스트 흐름을 담당한다.
- AI는 상태 기반 요청 해석, 리스크 게이트, 결과 설명을 담당한다.
- 실거래는 다루지 않는다.
- API 호출은 모두 Testnet 환경에서만 수행한다.
- API Key/Secret은 서버 환경 변수에만 저장한다.
- AI의 `PASS` 판단은 실행 허가가 아니라 BE 재검증 전 단계 결과다.
- 주문 테스트 흐름은 하나의 AI run 상태를 resume하며 진행하고, 독립된 두 번의 프롬프트 호출 체인으로 구현하지 않는다.

## 2. 시스템 관계도

```mermaid
flowchart LR
    USER[사용자] --> FE[React FE]
    FE --> BE[FastAPI BE]
    BE --> DB[(SQLite)]
    BE --> AI[LangGraph AI]
    BE --> REST[Binance Spot Testnet REST]
    BE --> WS[Binance Spot Testnet WebSocket]
```

## 3. 상세 아키텍처

```mermaid
flowchart TB
    USER[User] --> UI[React UI]
    UI --> API[FastAPI REST API]
    API --> CONFIG[Testnet Config Service]
    API --> ACCOUNT[Balance / Account Service]
    API --> MARKET[Price / Order Book / Kline Service]
    API --> ORDER[Spot Order Service]
    API --> STREAM[WebSocket Stream Service]
    API --> LOG[Log / Report Service]
    API --> AIGW[AI Gateway]
    AIGW --> ORCH[LangGraph Orchestrator]
    ORCH --> P[Policy/Planning Agent]
    ORCH --> R[Market/Risk Agent]
    R --> G{Risk Gate}
    G -->|Pass| ORDER
    G -->|Reject/Hold| E[Execution/Report Agent]
    ORDER --> E[Execution/Report Agent]
    E --> LOG
    ACCOUNT --> BREST[Binance Testnet REST]
    MARKET --> BREST
    ORDER --> BREST
    STREAM --> BWS[Binance Testnet WS]
    ORDER --> DB
    LOG --> DB
    E --> DB
```

## 4. 책임 경계

| 계층 | 책임 | 하지 않는 일 |
|---|---|---|
| FE | 환경 변수 설정 상태 확인, 잔고/시세/주문 화면, 상태 시각화 | Binance 직접 호출, 시그니처 생성, API Key 원문 처리 |
| BE | REST/WebSocket 연동, 시그니처 생성, 주문 요청, 상태 조회, 취소, AI 통과 요청 재검증 | 브라우저 렌더링, 실거래 전송 |
| AI | 요청 해석, 상태 전이 관리, 리스크 게이트, 결과 설명 | Binance 직접 서명 요청, 실거래 전략 운용, BE 검증 우회 |
| DB | 환경 설정, 요청 로그, 주문 로그, 리포트 저장 | 시장 데이터의 영구 원본 저장 |
| Binance Spot Testnet | 가상 자금 기반 현물 API/WS 제공 | 내부 정책 판단 |

## 5. 핵심 흐름

### 5.1 설정 상태 확인 → 잔고 조회 → 시세 조회 → 주문 테스트 → 상태 확인 → 취소

```mermaid
sequenceDiagram
    participant U as User
    participant F as FE
    participant B as BE
    participant A as AI
    participant T as Binance Testnet
    participant D as DB

    U->>F: Testnet 설정 상태 확인
    F->>B: 설정 상태 조회
    B->>D: 마지막 설정 상태 읽기
    U->>F: 잔고/시세 조회 요청
    F->>B: REST 요청
    B->>T: account / ticker / depth / klines 조회
    T-->>B: 응답 반환
    B->>A: 결과 요약 요청
    A-->>B: 설명 생성
    B-->>F: 상태 카드 반환
    U->>F: 주문 테스트 요청
    F->>B: order 요청
    B->>A: AI run 시작 (run_id) + 정책/시장/잔고 전달
    A-->>B: 동일 run의 gate 결과 + execution_request 또는 hold/no-order 사유
    B->>B: deterministic 재검증 / signature 생성
    B->>T: Testnet spot order 요청
    T-->>B: 주문 응답
    B->>A: 동일 run resume + execution_result 주입
    A-->>B: 설명 가능한 결과 + per-agent trace + run summary
    B->>D: 주문 로그 / report 저장
    B-->>F: 주문 결과 반환
```

### 5.2 WebSocket 시세 수신 흐름

```mermaid
flowchart LR
    FE[React] --> BE[FastAPI]
    BE --> WS[wss://stream.testnet.binance.vision/ws]
    WS --> BE
    BE --> FE
```

### 5.3 AI run checkpoint / resume 흐름

```mermaid
sequenceDiagram
    participant F as FE
    participant B as BE
    participant A as AI
    participant D as SQLite

    F->>B: 주문 테스트 요청
    B->>A: run 시작 + request/policy/market/account 주입
    A-->>B: HOLD 또는 READY_FOR_BE + trace
    B->>D: checkpoint 저장
    alt HOLD_REVIEW_REQUIRED 또는 HOLD_DATA_INSUFFICIENT
        B-->>F: hold_reason + resume 필요 정보 반환
        F->>B: 재개 요청(resume payload)
        B->>D: checkpoint 조회
        B->>A: 동일 run_id resume
    else READY_FOR_BE
        B->>B: deterministic 재검증
        B->>A: execution_result resume
    end
```

### 5.4 Runtime contract 요약

- 모든 주문 테스트 run은 `run_id`로 식별한다.
- `HOLD`는 lifecycle 상태이며, 실제 원인은 `hold_reason`으로 구분한다.
- `hold_reason`의 최소 집합은 `HOLD_REVIEW_REQUIRED`, `HOLD_DATA_INSUFFICIENT`다.
- resume는 같은 `run_id`에 대해서만 허용한다.
- BE는 checkpoint 복원 후 immutable 필드를 유지한 채 resume payload만 병합한다.

## 6. 장애 및 예외 기본 원칙

- Testnet REST 실패 시 신규 주문 테스트를 중단한다.
- 잔고 조회 실패 시 주문 화면에서 주문 요청을 차단한다.
- 시그니처 생성 실패 시 즉시 에러를 반환한다.
- WebSocket 연결 실패 시 수동 조회 fallback을 사용한다.
- 실거래 URL 또는 잘못된 API Key 사용이 감지되면 즉시 실행을 차단한다.
- AI가 `PASS`를 반환해도 BE 재검증 실패 시 `BE_REJECTED`로 종료한다.
- AI schema 검증 실패 시 BE는 주문 제출로 진행하지 않고 `FAILED` 또는 `HOLD` + `hold_reason=HOLD_DATA_INSUFFICIENT`로 종료한다.

## 7. run 저장소와 resume 경계

| 항목 | 기준 |
|---|---|
| 저장소 | SQLite checkpoint 레코드 |
| 식별자 | `run_id` |
| 복원 단위 | `AgentRunState` 전체 + latest trace + latest verification checks |
| immutable 필드 | `request_context`, `policy_context`, 최초 `normalized_order_intent`, 이전 단계 trace |
| resume 허용 필드 | 사용자 승인 결과, 재조회 시장 데이터, BE execution_result, 보완 입력 |
| 만료 기준 | 데모/로컬 환경 기준 TTL을 두되, 만료 시 `FAILED` 또는 재시작 안내 |
| 감사 보존 | 최종 상태 도달 후에도 `run_summary`와 `errors`를 로그에 남김 |

## 8. 신뢰 경계 및 보안 관점

- 브라우저는 Binance Testnet REST/WS를 직접 호출하지 않는다.
- API Key/Secret은 서버 측 환경 변수로만 보관한다.
- BE만 `timestamp`, `signature`, `X-MBX-APIKEY`를 처리한다.
- AI에는 API Key, Secret, signature 원문을 전달하지 않는다.
- 실거래 host 문자열은 설정값과 문서에서 금지한다.
- FE는 API Key/Secret 원문을 입력받거나 저장하지 않는다.
- AI가 사용할 수 있는 도구는 Binance 직접 호출 도구가 아니라 BE 또는 내부 서비스가 제공하는 정규화 도구로 제한한다.

## 9. 확정 구현 기준

- REST Base URL은 `https://testnet.binance.vision/api`로 고정한다.
- WebSocket Streams URL은 `wss://stream.testnet.binance.vision/ws`로 고정한다.
- WebSocket API URL은 `wss://ws-api.testnet.binance.vision/ws-api/v3`로 고정한다.
- AI는 BE 내부 프로세스가 아니라 별도 HTTP 서비스로 두되, 로컬 동일 머신에서만 실행한다.
- 주문 예시는 Spot 현물 시장가/지정가만 다룬다.
- orderbook은 `depth` snapshot 기준으로 정의한다.
- `HOLD`와 `hold_reason`를 분리해 설계하고, FE/BE/AI가 동일 값 집합을 사용한다.
- resume는 checkpoint 복원 후 명시된 필드만 병합하는 방식으로 동작한다.
