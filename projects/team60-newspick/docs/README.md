# NewPick 문서

NewPick 프로젝트의 모든 설계·기술·디자인 문서. 레이어별로 분리되어 있고, 한 기술당 한 파일이 원칙이다. 상세 구조 결정 배경은 `~/.claude/plans/playful-jumping-comet.md` 참고.

## 빠른 이동

- **무엇을 만드는지** → [product/overview.md](product/overview.md)
- **3주짜리 MVP, 어디까지 만드는지** → [product/scope-and-priority.md](product/scope-and-priority.md)
- **AI 파이프라인 어떻게 도는지** → [architecture/pipeline-design.md](architecture/pipeline-design.md)
- **UI/UX 어떻게 생겼는지** → [design.md](design.md)
- **새 환경 셋업 / 환경변수 / 포트** → [infra/docker-compose.md](infra/docker-compose.md), [infra/environment.md](infra/environment.md)
- **발표 시연 운영** → [product/demo-strategy.md](product/demo-strategy.md)

## 기술 스택 (확정)

| 레이어 | 선택 |
|---|---|
| 프론트엔드 | Next.js 15 + TypeScript, Tailwind v4, Zustand + TanStack Query, pnpm |
| 백엔드 | Spring Boot 3.4 + Java 17 + Gradle Groovy, Flyway, SseEmitter, RestClient/WebClient |
| AI | Python 3.12 + FastAPI + LangGraph + langchain-upstage SDK, LangSmith 트레이싱 |
| LLM | Upstage Solar (`solar-pro2`) |
| 임베딩 | Upstage Solar (`solar-embedding-1-large-{passage,query}`, 4096-dim) |
| DB | PostgreSQL 16 + pgvector 0.7 (Docker, `pgvector/pgvector:pg16`) |
| 인증 | 없음 (MVP) |

## 인덱스

### product/ — 제품 / UX / 시연

| 파일 | 한 줄 |
|---|---|
| [product/overview.md](product/overview.md) | 프로젝트 성격(3주 발표용 AI 데모)과 앱 기획 요약 |
| [product/scope-and-priority.md](product/scope-and-priority.md) | MVP 범위·다음 작업 우선순위·현재 판단 |
| [product/ux-decisions.md](product/ux-decisions.md) | 현재 UI/UX 반영 상태와 유지/수정 결정 |
| [product/demo-strategy.md](product/demo-strategy.md) | 발표 시연 전략과 챗봇 데이터 고정 운영 |

### architecture/ — 시스템 횡단 설계

| 파일 | 한 줄 |
|---|---|
| [architecture/system-overview.md](architecture/system-overview.md) | 목표 + 전체 처리 흐름 + RSS 피드 구성 |
| [architecture/pipeline-design.md](architecture/pipeline-design.md) | LangGraph 노드 설계, State, 조건부 라우팅, 리포트 파이프라인 |
| [architecture/data-schema.md](architecture/data-schema.md) | Article / Quiz / UserActivity 스키마 |
| [architecture/realtime-ui-states.md](architecture/realtime-ui-states.md) | UI 상태 매핑과 SSE 진행률 스키마/연동 |
| [architecture/implementation-priority.md](architecture/implementation-priority.md) | MVP 적용 범위와 10단계 구현 우선순위 |

### ai/ — AI 파이프라인 기술 (1기술=1파일)

| 파일 | 한 줄 |
|---|---|
| [ai/agents.md](ai/agents.md) | 5개 AI 에이전트(수집/요약/검증/퀴즈/리포트) 역할·입출력 |
| [ai/langgraph.md](ai/langgraph.md) | LangGraph 도입 이유와 LangSmith 와의 역할 분담 |
| [ai/langsmith.md](ai/langsmith.md) | LangSmith 5개 활용처(트레이싱·디버깅·비용·실험·운영) |
| [ai/solar.md](ai/solar.md) | Upstage Solar 사용 모델(`solar-pro2`, `solar-embedding-1-large-{passage,query}`) 및 환경 변수 |
| [ai/prompts.md](ai/prompts.md) | 요약/검증/퀴즈 프롬프트 템플릿 + 주의점 |
| [ai/rag-chat.md](ai/rag-chat.md) | RAG 기반 챗 에이전트 (질의 임베딩 → pgvector 검색 → SSE) |

### backend/ — Spring Boot 측

| 파일 | 한 줄 |
|---|---|
| [backend/spring-boot.md](backend/spring-boot.md) | Spring Boot 3.4 + Java 17 + Gradle, 모듈 구조·의존성·application.yml |
| [backend/jpa.md](backend/jpa.md) | JPA 엔티티 매핑(읽기 위주), jsonb·pgvector 처리 정책 |
| [backend/rest-api.md](backend/rest-api.md) | REST 엔드포인트 6종 + 응답 스키마 |
| [backend/sse.md](backend/sse.md) | SseEmitter + WebClient 로 Python SSE 프록시 |
| [backend/auth.md](backend/auth.md) | MVP는 인증 없음, Spring Security 도입 X |

### frontend/ — Next.js 측

| 파일 | 한 줄 |
|---|---|
| [frontend/nextjs.md](frontend/nextjs.md) | Next 15 + TS, App Router, 페이지별 RSC/Client 분리 전략 |
| [frontend/tailwind.md](frontend/tailwind.md) | Tailwind v4 `@theme`, 프로토타입 토큰 → 유틸리티 매핑 |
| [frontend/state-management.md](frontend/state-management.md) | Zustand(클라이언트) + TanStack Query(서버 상태) |
| [frontend/sse-client.md](frontend/sse-client.md) | EventSource 헬퍼, 홈 진행률·챗 스트리밍 |

### data/ — 데이터 계층

| 파일 | 한 줄 |
|---|---|
| [data/postgresql.md](data/postgresql.md) | PostgreSQL 16 + pgvector 운영 정책, 초기 DDL |
| [data/pgvector.md](data/pgvector.md) | `vector(4096)` 컬럼, MVP는 인덱스 없음 — 향후 halfvec+HNSW |
| [data/hdbscan.md](data/hdbscan.md) | min_cluster_size=2, euclidean(L2 정규화) |

### infra/ — 로컬 개발·시연 환경

| 파일 | 한 줄 |
|---|---|
| [infra/docker-compose.md](infra/docker-compose.md) | DB 전용 docker compose, 새 환경 셋업 절차 |
| [infra/environment.md](infra/environment.md) | 포트 맵, 환경변수 4종 분리, 시연 직전 체크리스트 |

### process/ — 개발 방법론 (Phase C)

| 파일 | 한 줄 |
|---|---|
| [process/development-flow.md](process/development-flow.md) | 3 트랙 비충돌 병렬 개발 + TDD 사이클 + 브랜치/PR 자동화 + 슬래시 커맨드 흐름 |

### contracts/ — 트랙 간 계약 (BOOT-000 에서 동결, read-only)

| 파일 | 한 줄 |
|---|---|
| [contracts/README.md](contracts/README.md) | 계약 변경 절차 |
| [contracts/openapi.yaml](contracts/openapi.yaml) | Spring REST API 스펙 (FE-BE 계약) |
| [contracts/python-ai.yaml](contracts/python-ai.yaml) | Python FastAPI 스펙 (BE-AI 계약) |
| [contracts/sse-events.md](contracts/sse-events.md) | SSE 이벤트 스키마 6종 |
| [contracts/db-init.sql](contracts/db-init.sql) | Flyway V1 초기 DDL |
| [contracts/json-schemas/](contracts/json-schemas/) | Article / ArticleSummary / ArticleCardSummary / DailyReport JSON Schema |

### progress/ — 트랙별 체크리스트 (3명 동시 체크 시 충돌 0)

| 파일 | 한 줄 |
|---|---|
| [../progress.md](../progress.md) | 루트 마스터 대시보드 + 마일스톤 + 의존성 대시보드 |
| [progress/boot.md](progress/boot.md) | BOOT-000 1단계 (공용 셋업) |
| [progress/be.md](progress/be.md) | Spring M2~M6 23단계 |
| [progress/fe.md](progress/fe.md) | Next.js M2~M6 37단계 |
| [progress/ai.md](progress/ai.md) | Python LangGraph M2~M6 29단계 |

### steps/ — 단계 명세서

| 경로 | 내용 |
|---|---|
| [steps/TEMPLATE.md](steps/TEMPLATE.md) | 6 섹션 단계 템플릿 |
| [steps/boot/BOOT-000.md](steps/boot/BOOT-000.md) | 공용 부트스트랩 단계 명세 |
| [steps/be/BE-001.md](steps/be/BE-001.md) | Flyway V1 마이그레이션 단계 명세 (시드 예시) |
| [steps/fe/FE-001.md](steps/fe/FE-001.md) | Tailwind v4 토큰 셋업 단계 명세 (시드 예시) |
| [steps/ai/AI-001.md](steps/ai/AI-001.md) | FastAPI 스켈레톤 + /health 단계 명세 (시드 예시) |
| [steps/{be,fe,ai}/](steps/) | M3~M6 의존성 인식 단계 명세 선작성 완료 |
| (M7 이후) | `/step-implement`가 progress의 한 줄 명세를 기반으로 필요할 때 자동 작성 |

### 단일 진실원천

| 파일 | 한 줄 |
|---|---|
| [design.md](design.md) | UI/UX 단일 진실원천 — `prototype/`의 토큰·화면·컴포넌트·인터랙션 정규화 |

### \_archive/

| 파일 | 한 줄 |
|---|---|
| `_archive/ai-implementation-plan.md` | 분해 전 원본 (보존용 — 절대 수정 금지) |
| `_archive/planning-notes.md` | 분해 전 원본 (보존용 — 절대 수정 금지) |

---

## Phase 진행 현황

- **Phase A (완료)**: 디렉토리 골격 + 기존 두 MD 분해 이전 + `design.md` 작성.
- **Phase B (완료)**: 기술 스택 확정(Solar API, Spring 3.4, Next 15, Tailwind v4, Zustand+TanStack Query, Python LangGraph 분리), backend/ frontend/ data/ infra/ 본문 작성, OpenAI → Solar 일괄 갱신.
- **Phase C (진행 중)**: 3 트랙(FE/BE/AI) 비충돌 병렬 개발 인프라 구축 완료 — `docs/contracts/` 동결, `docs/progress/` 체크리스트, `docs/steps/` 명세서 시드, 슬래시 커맨드 2종. 실제 코드 작성은 `/step-implement BOOT-000` 부터 시작.

## Phase C 시작 방법

```
/project-review              # 현재 상태 파악
/step-implement BOOT-000     # 공용 부트스트랩 — 다른 트랙 시작 전 필수
```

BOOT-000 완료 후 3명이 동시에 `/step-implement BE-001`, `FE-001`, `AI-001` 진행 가능 (충돌 0 보장). 자세한 흐름은 [process/development-flow.md](process/development-flow.md).
