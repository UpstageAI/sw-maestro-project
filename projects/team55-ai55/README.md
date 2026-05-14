# PM Schedule Agent

팀 프로젝트의 Task, 팀원 근무 가능 시간, 내부 캘린더 정보를 바탕으로 우선순위, 일정 배치안, 마감 리스크를 추천하는 PM 보조 Agent입니다.

프론트엔드는 프로젝트 데이터를 브라우저 `localStorage`에 저장하고, 백엔드는 요청마다 전달받은 `ProjectSnapshot`을 분석해 추천 결과만 반환합니다. 외부 캘린더 연동이나 서버 DB 저장 없이 로컬 실행을 전제로 만든 MVP입니다.

## 주요 기능

- 프로젝트 목표 입력 후 AI 마일스톤 후보 생성 및 PM 승인
- 팀원, 근무 가능 시간, Task, 의존성, 진척률 관리
- Task별 결정적 우선순위 점수 계산
- 담당자 근무 가능 시간과 기존 캘린더 이벤트를 고려한 일정 슬롯 추천
- 마감, 선후행 관계, 담당자 과부하 리스크 탐지
- 추천 일정 승인 후 내부 캘린더 이벤트로 반영
- 프로젝트 데이터 JSON export/import
- Upstage API 키가 없을 때도 동작하는 deterministic fallback

## 실행 주소

| 구분 | 주소 |
|---|---|
| Frontend | `http://127.0.0.1:5173` |
| Backend | `http://127.0.0.1:8000` |
| Health Check | `http://127.0.0.1:8000/v1/health` |
| OpenAPI JSON | `http://127.0.0.1:8000/openapi.json` |

## 기술 스택

### Frontend

- React 18
- Vite 6
- TypeScript
- React Router
- React Hook Form
- Tailwind CSS 4
- Radix UI
- MUI Icons
- Lucide React
- Playwright

### Backend

- Python 3.11+
- FastAPI
- Pydantic v2
- Uvicorn
- LangGraph
- httpx
- structlog
- pytest

### Infra / Tooling

- npm workspaces
- Docker Compose
- OpenAPI 타입 생성
- 로컬 QA 스크립트

## 프로젝트 구조

```text
.
├── FE/                  # React/Vite 프론트엔드
│   ├── src/app/         # 라우트, 페이지, store, API client
│   ├── tests/           # FE 계약 테스트와 Playwright smoke test
│   └── package.json
├── BE/                  # FastAPI 백엔드
│   ├── app/api/         # API route
│   ├── app/agents/      # priority, schedule, risk agent
│   ├── app/services/    # LLM, cache, metrics, ID 발급 등
│   ├── tests/           # 백엔드 계약/시나리오 테스트
│   └── pyproject.toml
├── docs/specs/          # 기획/아키텍처/API 계약 문서
├── scripts/             # QA, OpenAPI 생성, smoke check 스크립트
├── demos/               # 데모 입력/출력 JSON
├── docker-compose.yml
└── package.json
```

## 사전 준비

- Node.js 18 이상 권장
- Python 3.11 이상
- Docker로 실행할 경우 Docker Desktop
- 실제 LLM 호출을 사용하려면 Upstage API key

## 환경 변수

백엔드 환경 변수 예시는 `BE/.env.example`에 있습니다.

```bash
cp BE/.env.example BE/.env
```

주요 값은 아래와 같습니다.

| 변수 | 설명 |
|---|---|
| `UPSTAGE_API_KEY` | Upstage LLM 호출용 API key |
| `UPSTAGE_BASE_URL` | Upstage API base URL |
| `UPSTAGE_MODEL` | 사용할 Upstage 모델. 기본값은 `solar-mini` |
| `LLM_DAILY_BUDGET` | 일일 LLM 호출 예산 |
| `LLM_MAX_CONCURRENCY` | LLM 동시 호출 제한 |
| `RATE_LIMIT_PER_MIN` | 백엔드 요청 rate limit |
| `FRONTEND_ORIGINS` | CORS 허용 프론트엔드 origin 목록 |

`UPSTAGE_API_KEY`가 비어 있어도 로컬 개발과 테스트는 fallback 결과로 진행할 수 있습니다.

## 실행 방법

### 1. Docker Compose로 실행

루트에 `.env` 파일을 만들고 백엔드 환경 변수를 넣습니다.

```bash
cp BE/.env.example .env
```

그다음 실행합니다.

```bash
docker compose up --build
```

브라우저에서 `http://127.0.0.1:5173`으로 접속합니다.

### 2. 로컬에서 직접 실행

의존성을 설치합니다.

```bash
npm install
cd BE
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
cd ..
```

백엔드를 실행합니다.

```bash
npm run dev:be
```

다른 터미널에서 프론트엔드를 실행합니다.

```bash
npm run dev:fe
```

브라우저에서 `http://127.0.0.1:5173`으로 접속합니다.

## 주요 npm 스크립트

| 명령 | 설명 |
|---|---|
| `npm run dev:fe` | Vite 프론트엔드 개발 서버 실행 |
| `npm run dev:be` | FastAPI 백엔드 개발 서버 실행 |
| `npm run build:fe` | 프론트엔드 프로덕션 빌드 |
| `npm run test:fe` | FE API client snapshot 테스트 |
| `npm run test:be` | 백엔드 pytest 실행 |
| `npm run test:e2e` | Playwright E2E smoke test 실행 |
| `npm run generate:openapi` | FastAPI OpenAPI 기반 FE 타입 재생성 |
| `npm run check:openapi` | 생성된 OpenAPI 타입 최신성 확인 |
| `npm run qa:local` | 로컬 품질 게이트 실행 |
| `npm run check:completion` | 최종 완료 게이트 실행 |

## 품질 검증

일반 로컬 검증은 아래 명령을 사용합니다.

```bash
npm run qa:local
```

이 명령은 OpenAPI drift, Upstage readiness, 백엔드 테스트, 프론트엔드 테스트, FE 빌드, bundle budget, Playwright 시나리오 발견, 서버 health, API smoke, audit consistency, whitespace를 확인합니다.

최종 완료 검증은 아래 명령을 사용합니다.

```bash
npm run check:completion
```

`check:completion`은 `qa:local`에 더해 live Upstage 검증과 Playwright 브라우저 E2E까지 요구합니다. 이 검증을 통과하려면 FE/BE 서버가 실행 중이어야 하고, `UPSTAGE_API_KEY`가 설정되어 있어야 합니다.

## API 흐름

주요 백엔드 endpoint는 아래와 같습니다.

| Endpoint | 역할 |
|---|---|
| `GET /v1/health` | 백엔드와 LLM 설정 상태 확인 |
| `POST /v1/projects` | 프로젝트 ID 발급 |
| `POST /v1/projects/{project_id}/milestones:suggest` | 프로젝트 목표 기반 마일스톤 후보 생성 |
| `POST /v1/projects/{project_id}/milestones:approve` | PM이 승인한 마일스톤 확정 |
| `POST /v1/projects/{project_id}/analyze` | Priority, Schedule, Risk 분석 실행 |
| `POST /v1/projects/{project_id}/schedule:approve` | 선택한 추천 슬롯을 내부 캘린더 이벤트로 승인 |
| `POST /v1/projects/{project_id}/risk:simulate` | 리스크 제안 적용 전후 변화 시뮬레이션 |

프론트엔드에서는 raw `fetch` 대신 `FE/src/app/apiClient.ts`의 wrapper를 통해 API를 호출합니다.

## 참고 문서

- `docs/specs/00-overview.md`: 프로젝트 목표와 MVP 범위
- `docs/specs/01-architecture.md`: 시스템 아키텍처와 Agent 구조
- `docs/specs/07-data-contracts.md`: API 및 데이터 계약
- `FE/README.md`: 프론트엔드 인수인계 문서
- `BE/README.md`: 백엔드 인수인계 문서
- `docs/local-verification-runbook.md`: 로컬 검증 절차
