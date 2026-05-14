# NewPick

AI 기반 뉴스 큐레이션 앱. RSS 수집 → Solar LLM 요약 → 개인화 피드 + 인라인 퀴즈 + 데일리 리포트 + RAG 챗.

## 기술 스택

| 레이어 | 선택 |
|---|---|
| Frontend | Next.js 16 + TypeScript + Tailwind v4 + Zustand + TanStack Query |
| Backend | Spring Boot 3.5 + Java 17 + Gradle + Flyway + JPA + SseEmitter |
| AI | Python 3.12 + FastAPI + LangGraph + langchain-upstage + LangSmith |
| LLM / 임베딩 | Upstage Solar (`solar-pro2`, `solar-embedding-1-large`) |
| DB | PostgreSQL 16 + pgvector (Docker) |

## 빠른 시작

```bash
# 1. 저장소 클론
git clone <repo> && cd newspick

# 2. 환경변수 설정 (.env 를 루트에 생성)
cp .env.example .env
# 필요 시 편집 (DB 기본값은 newspick/newspick/newspick)

# 3. DB 기동
docker compose up -d

# 4. 각 서비스 실행
cd backend  && ./gradlew bootRun       # Spring (포트 8080)
cd ../ai    && uv run uvicorn newspick_ai.main:app --reload  # FastAPI (포트 8000)
cd ../frontend && pnpm dev             # Next.js (포트 3000)
```

## 포트

| 서비스 | 포트 |
|---|---|
| PostgreSQL | 5432 |
| Spring Boot | 8080 |
| Python AI (FastAPI) | 8000 |
| Next.js (dev) | 3000 |

## 개발 방법론

[docs/process/development-flow.md](docs/process/development-flow.md) 참조.

슬래시 커맨드:
- CLAUDE
  -  `/project-review` — 세션 시작 시 현황 파악
  - `/step-implement {ID}` — 한 step TDD 사이클 자동 실행
- CODEX
  -  `$project-review`
  - `$step-implement BE-001`
