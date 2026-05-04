# Coin Agent 문서 레포지토리

> 정책 기반 리스크 게이트를 통과한 경우에만 페이퍼 실행을 수행하는 보수적 코인 투자 보조 시스템의 구현 기준 문서 모음

## 문서 목적

이 레포지토리는 Coin Agent MVP를 실제로 구현하기 위한 기준 문서 세트를 관리한다. 이 프로젝트는 **로컬에서만 실행하는 개인용 Agent**이며, **실제 자동매매가 아니라 페이퍼 실행 중심 MVP**다. 사용자의 정책과 리스크 게이트를 통과하지 못하면 기본값은 **무거래 또는 판단 보류**로 한다.

## 문서 읽는 순서

1. `PROPOSAL.md` - 왜 이 프로젝트를 하는지, 어떤 문제를 해결하는지 이해한다.
2. `SPEC.md` - MVP에서 반드시 만족해야 할 제품/기능 요구사항을 확인한다.
3. `ARCHITECTURE.md` - 시스템 구조와 FE/BE/AI 책임 경계를 확인한다.
4. `DATA.md` - API 계약, 데이터 모델, ERD를 확인한다.
5. `FE.md` / `BE.md` / `AI.md` - 역할별 구현 상세를 확인한다.
6. `TEST_AND_DEMO.md` - 테스트 기준과 발표 데모 기준을 확인한다.

## 문서 역할 요약

| 문서 | 역할 | 주요 독자 |
|---|---|---|
| `README.md` | 문서 레포 진입점, 읽는 순서, 환경 변수/실행 기준 안내 | 전원 |
| `PROPOSAL.md` | 상위 기획 근거 문서, 문제 정의와 MVP 방향성 보존 | 전원 |
| `SPEC.md` | 제품/기능 명세, MVP 범위와 성공 기준 정의 | PM, FE, BE, AI |
| `ARCHITECTURE.md` | 전체 시스템 구조, 책임 경계, 예외 기본 원칙 정의 | FE, BE, AI |
| `FE.md` | Next.js 기준 화면/컴포넌트/UI 상태/디자인 시스템 정의 | FE |
| `BE.md` | FastAPI 기준 라우터, 서비스, 어댑터, 예외 포맷 정의 | BE |
| `AI.md` | LangGraph 기준 오케스트레이터, Agent, 프롬프트/가드레일 정의 | AI |
| `DATA.md` | API 계약, 데이터 객체, DB 초안, ERD 통합 정의 | FE, BE, AI |
| `TEST_AND_DEMO.md` | 테스트 전략, E2E, 발표 데모, 실패 시 백업 플랜 정의 | 전원 |

## 구현 원칙 요약

- 실제 자동매매는 MVP 범위에 포함하지 않는다.
- 모든 실행은 페이퍼 실행 기준으로 정의한다.
- 사용자 정책과 리스크 게이트를 통과하지 못하면 기본값은 무거래 또는 판단 보류로 한다.
- 수익 보장, 확정적 예측, 공격적 투자 표현은 금지한다.
- 구현 기준은 로컬 개인용 Agent와 빠른 데모 개발을 우선하는 방향으로 고정한다.

## 실행 및 환경 변수

이 레포는 문서 전용 레포지토리다. 실제 애플리케이션 실행은 별도 구현 레포 또는 이후 생성될 코드 레포를 기준으로 한다. 아래 값은 구현 시점에 필요한 공통 환경 변수 기준이다.

### 권장 서비스 구성

- FE: Next.js
- BE: FastAPI
- AI: LangGraph 실행 서비스
- DB: SQLite
- External: Upbit API

### 환경 변수 목록

| 변수명 | 설명 | 필수 여부 |
|---|---|---:|
| `OPENAI_API_KEY` | LLM 호출용 API 키 | 예 |
| `UPBIT_ACCESS_KEY` | 현재 MVP 범위에서는 사용하지 않음. 향후 확장 대비 예약 변수 | 선택 |
| `UPBIT_SECRET_KEY` | 현재 MVP 범위에서는 사용하지 않음. 향후 확장 대비 예약 변수 | 선택 |
| `UPBIT_BASE_URL` | Upbit API 기본 URL | 예 |
| `DATABASE_URL` | SQLite 연결 문자열 | 예 |
| `NEXT_PUBLIC_API_BASE_URL` | FE에서 호출할 BE 기본 URL | 예 |
| `AI_SERVICE_HTTP_URL` | BE가 호출하는 AI HTTP 엔드포인트 | 선택 |
| `APP_ENV` | `local`, `dev`, `demo` 등 실행 환경 구분 | 예 |
| `LOG_LEVEL` | 애플리케이션 로그 레벨 | 예 |

### 로컬 개발 기준

1. FE는 `.env.local`에 `NEXT_PUBLIC_API_BASE_URL`을 설정한다.
2. BE는 `.env`에 `DATABASE_URL`, `UPBIT_BASE_URL`, `OPENAI_API_KEY`를 설정한다.
3. AI 서비스는 BE와 동일 네트워크에서 HTTP 인터페이스만 제공한다.
4. 로컬 데모와 개인용 실행 환경 모두 SQLite를 기본 저장소로 사용한다.
5. 데모는 업비트 실시간 시세/캔들 API를 사용하고, 실행은 내부 페이퍼 실행으로 처리한다.

### 실행 순서 기준

1. DB 준비
2. FastAPI 실행
3. LangGraph AI 서비스 실행
4. Next.js 실행
5. 테스트 데이터 적재 후 데모 진행

## 문서 사용 방법

- 요구사항 변경이 발생하면 먼저 `PROPOSAL.md`와 `SPEC.md`를 확인한다.
- 구현 상세를 바꿀 때는 `ARCHITECTURE.md`, `FE.md`, `BE.md`, `AI.md`, `DATA.md`를 함께 갱신한다.
- 테스트 기준 변경은 반드시 `TEST_AND_DEMO.md`와 동기화한다.

## 확정 구현 기준

- 로컬 개인용 Agent 기준으로 데이터는 SQLite에 저장하고, 수동 정리 전까지 유지한다.
- 업비트 실시간 API는 자동 폴링보다 수동 새로고침을 기본으로 사용한다.
- 단일 사용자 환경에서 정책 히스토리는 최신 10개 버전까지 유지한다.
