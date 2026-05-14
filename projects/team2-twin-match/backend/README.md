# llm-blind-date — Multi-Agent Dating Platform

LLM 페르소나 복제 + Multi-Agent System 기반 AI 소개팅 시뮬레이션 플랫폼.

명세는 [`docs/backend-specs/`](docs/backend-specs/) 참고.

## Stack
- **FastAPI** (Python 3.11+) / **SQLAlchemy 2.0 async** / **SQLite (aiosqlite)**
- **Upstage Solar LLM** (OpenAI-compatible API; `solar-pro2`)
- 비동기 대화 시뮬레이션은 **FastAPI BackgroundTasks** 로 실행

## Project Layout
```
app/
├── main.py                  # FastAPI factory
├── core/                    # config, db session, lifespan, errors, Solar client
│   ├── config.py
│   ├── lifespan.py          # init_db + Matchmaker Agent seed
│   ├── solar_client.py      # Upstage Solar LLM async wrapper
│   ├── db/session.py
│   └── errors/{error,handler}.py
├── routers/                 # /, /health, /api/agents, /api/conversations, /api/jobs
│   ├── dependencies.py      # FastAPI Depends 그래프 (repo → service)
│   ├── agents.py
│   ├── conversations.py
│   ├── jobs.py
│   └── health.py
├── services/                # 비즈니스 로직 (담당자 TODO)
├── repositories/            # SQLAlchemy 데이터 접근 (담당자 TODO)
├── models/
│   ├── db/                  # SQLAlchemy ORM (스펙 §3 매핑)
│   ├── dtos/                # 계층간 dataclass DTO
│   └── schemas/              # Pydantic Request/Response
├── prompts/                 # Agent / Matchmaker / Chemistry 프롬프트
└── utils/text_utils.py
```

## Setup

```bash
# 1) 환경 변수
cp .env.example .env
# .env 의 UPSTAGE_API_KEY 채우기

# 2) Poetry 설치
pip install poetry
poetry install --no-root
poetry run pre-commit install

# 3) 서버 실행 (./data/app.db 자동 생성 + Matchmaker Agent 시드)
./start.sh
```

서버: http://localhost:8000  ·  Swagger: http://localhost:8000/docs

## 4-Person Workstream

| 담당 | 모듈 | 우선순위 |
|------|------|----------|
| A | `services/agent_service.py` + `repositories/agent_repository.py` (FR-001/002) | P0 |
| B | `services/conversation_service.py` + `conversation/message` repos (FR-003/004) | P0 |
| C | `services/chemistry_service.py` + `chemistry_repository.py` (FR-005) | P1 |
| D | `services/job_service.py` + `job_repository.py` + 통합/문서/QA (FR-006/007) | P1 |

각 서비스의 메서드는 시그니처와 도메인 예외만 잡혀 있고 본문은 `NotImplementedError`. 자세한 TODO 는 각 파일 docstring 참고.

## Test

```bash
./test.sh
```

헬스체크/루트 라우터는 동작하므로 `tests/app/router/test_health.py` 가 그린이면 골격 OK.
