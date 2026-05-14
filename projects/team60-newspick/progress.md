# NewPick 개발 진행 상황 (마스터 대시보드)

> 이 파일은 프로젝트 전체 상태의 첫 진입점이다. `/project-review`는 이 파일을 먼저 읽고, `/step-implement`는 단계 완료 후 트랙별 progress와 함께 이 파일을 최신화한다.

## 현재 단계

**Phase C — 실제 코드 구현**

방법론: [docs/process/development-flow.md](docs/process/development-flow.md)

## 트랙 진행 요약

| 트랙 | 진행률 | 현재 상태 | 다음 단계 | 상세 |
|---|---:|---|---|---|
| **BOOT** | 1/1 | M1 완료 | - | [docs/progress/boot.md](docs/progress/boot.md) |
| **BE** | 23/23 | M6 BE 완료 | - | [docs/progress/be.md](docs/progress/be.md) |
| **FE** | 35/37 | M3 live gate 완료 / M6 live gate 완료 | FE-022/030 | [docs/progress/fe.md](docs/progress/fe.md) |
| **AI** | 29/29 | M6 챗 RAG 완료 | - | [docs/progress/ai.md](docs/progress/ai.md) |

> 진행률은 `docs/progress/{track}.md`의 체크박스와 동기화한다. 이 표가 오래된 상태라면 `/step-implement` 완료 처리에서 함께 갱신한다.

## 마일스톤

- [x] **M1**: BOOT-000 완료 — 모든 트랙이 병렬 개발 가능 상태
- [x] **M2**: 각 트랙 초기 시드 단계 완료 — 걸어다니는 뼈대 (BOOT/BE/FE/AI 시드 완료)
- [x] **M3**: 첫 기사 1건이 RSS → 요약 → 홈 카드 → 상세까지 흐름 (E2E 정상 흐름)
- [ ] **M4**: 인라인 퀴즈 동작
- [ ] **M5**: 데일리 리포트 생성·표시
- [x] **M6**: AI 챗 RAG 동작
- [ ] **M7**: 시연 데이터 고정 ([product/demo-strategy.md](docs/product/demo-strategy.md)) + 발표 리허설

## 의존성 대시보드

### 바로 진행 가능
- **FE-022**: M4 실제 퀴즈 연동 확인 (BE-014, AI-017 완료 — live gate 해제)
- **FE-030**: M5 실제 리포트 연동 확인 (BE-017, AI-023 완료 — live gate 해제)

### 모킹 선행으로 진행 가능

- 없음 — FE M6 mock-first 단계는 완료되었고, 다음 FE 단계는 live gate다.

### 예정된 필수 의존 게이트

- 없음 — BE/AI hard dependency는 모두 해제되었고, 남은 FE 단계는 live gate다.

## M3~M6 스텝 그래프

| 마일스톤 | FE | BE | AI | 실제 연동 확인 |
|---|---|---|---|---|
| M3 기사 해피 패스 | FE-009~FE-016 | BE-009~BE-012 | AI-009~AI-014 | FE-016 필수: BE-012, AI-014 |
| M4 인라인 퀴즈 | FE-017~FE-022 | BE-013~BE-014 | AI-015~AI-017 | FE-022 필수: BE-014, AI-017 |
| M5 데일리 리포트 | FE-023~FE-030 | BE-015~BE-017 | AI-018~AI-023 | FE-030 필수: BE-017, AI-023 |
| M6 AI 챗 RAG | FE-031~FE-037 | BE-018~BE-023 | AI-024~AI-029 | FE-037 필수: BE-023, AI-029 |

## 운영 규칙

### Step 문서 완성도 기준

- M2~M6의 progress 항목은 모두 `docs/steps/{track}/{STEP_ID}.md` 파일을 가진다.
- step 문서는 YAML metadata, fixture, action, assertions, mock strategy, out of scope를 포함한다.
- 결정되지 않은 테스트 문구가 남아 있는 step은 구현 전에 문서 결함으로 처리한다.
- live integration gate는 `RUN_LIVE_CONTRACT=true`에서만 실제 서버를 호출한다.
- 루트 `progress.md`는 마일스톤/트랙/의존성 상태의 마스터 대시보드다.
- `docs/progress/{track}.md`는 단계 단위 체크리스트다.
- `docs/steps/{track}/{STEP_ID}.md`는 상세 명세와 의존성 메타데이터의 단일 진실원천이다.
- `mockable` 의존성은 MSW/WireMock/가짜 그래프로 대체해 진행할 수 있다.
- FE mock-first step은 이전 live integration gate 미완료 상태에서도 진행할 수 있다. 예: FE-016이 미완료여도 FE-017~FE-021은 fixture/MSW 기준으로 구현·검증한다.
- `hard` 의존성이 미완료인 단계는 구현 전에 중단하고 필요한 단계 ID를 사용자에게 알린다.

## 슬래시 커맨드

- `/project-review` — `progress.md`를 먼저 읽고 전체 마일스톤/트랙/의존성 상태를 요약한다. ([.claude/commands/project-review.md](.claude/commands/project-review.md))
- `/step-implement {ID}` — 단계 TDD 사이클을 수행하고 트랙 progress와 루트 `progress.md`를 함께 최신화한다. ([.claude/commands/step-implement.md](.claude/commands/step-implement.md))

## 기술 스택 요약

| 레이어 | 선택 |
|---|---|
| Frontend | Next.js 15 + TypeScript + Tailwind v4 + Zustand + TanStack Query (pnpm) |
| Backend | Spring Boot 3.4 + Java 17 + Gradle + Flyway + JPA + SseEmitter |
| AI | Python 3.12 + FastAPI + LangGraph + langchain-upstage + LangSmith |
| LLM | Upstage Solar (`solar-pro2`) |
| 임베딩 | Solar (`solar-embedding-1-large-{passage,query}`, 4096-dim) |
| DB | PostgreSQL 16 + pgvector (Docker `pgvector/pgvector:pg16`) |
| 인증 | 없음 (MVP) |

상세: [docs/README.md](docs/README.md)
