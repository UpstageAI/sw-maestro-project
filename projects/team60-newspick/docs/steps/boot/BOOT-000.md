---
id: BOOT-000
milestone: M1
requires:
  completed: []
  external:
    mockable: []
    hard: []
---

# BOOT-000 — 공용 부트스트랩

## 목표

3 트랙(BE/FE/AI)이 병렬 개발을 시작할 수 있는 **공유 인프라와 계약을 동결**한다. 이 step 완료 후 `docs/contracts/`, `docker-compose.yml`, `.env.example`, 각 트랙 디렉토리는 read-only 또는 own-track-only 로 다뤄지며 트랙 간 merge 충돌 가능성이 0 이 된다.

## 사전 조건

- Phase B 문서들이 모두 작성되어 있음 (현재 상태 ✅)
- 사용자 머신에 Docker, Java 17, Node 20+, pnpm, Python 3.12, uv 설치
- 사용자 보유: Upstage API key, LangSmith API key (있으면 좋음 — 없으면 .env 비워둠)

## 파일 대상

**루트 (공용)**:
```
docker-compose.yml                       [신규]
.env.example                             [신규]
.gitignore                               [신규]
.editorconfig                            [신규]
README.md                                [신규]
```

**계약 (이미 일부 존재 — 검증 + 채움)**:
```
docs/contracts/openapi.yaml              [존재 — 그대로 동결]
docs/contracts/python-ai.yaml            [존재 — 그대로 동결]
docs/contracts/sse-events.md             [존재 — 그대로 동결]
docs/contracts/db-init.sql               [존재 — 그대로 동결]
docs/contracts/json-schemas/*.json       [존재 — 그대로 동결]
```

**트랙 디렉토리 초기화 (각 디렉토리 안의 빈 프로젝트만)**:
```
backend/                                 [Spring Initializr 결과]
  build.gradle, settings.gradle, gradlew, src/main/java/com/newspick/NewspickApplication.java,
  src/main/resources/application.yml, src/main/resources/db/migration/V1__init.sql (= db-init.sql 사본)

frontend/                                [create-next-app 결과 + Tailwind v4]
  package.json, tsconfig.json, app/layout.tsx, app/page.tsx, app/globals.css

ai/                                      [uv init 결과 + FastAPI/LangGraph 의존성]
  pyproject.toml, src/newspick_ai/__init__.py, src/newspick_ai/main.py
```

## 테스트 명세

본 step 은 TDD 의 unit test 가 아니라 **부트스트랩 검증 테스트**:

- **테스트 1**: `docker compose up -d` 후 `docker compose ps` 결과에서 `db` 가 healthy
- **테스트 2**: `cd backend && ./gradlew build` → BUILD SUCCESSFUL (빈 프로젝트라도 컴파일·테스트 통과)
- **테스트 3**: `cd frontend && pnpm install && pnpm build` → 성공
- **테스트 4**: `cd ai && uv sync && uv run python -c "import newspick_ai"` → import 성공
- **테스트 5**: `docs/contracts/openapi.yaml` 와 `python-ai.yaml` 을 OpenAPI validator 로 검증 (예: `npx @redocly/cli lint docs/contracts/openapi.yaml`)
- **테스트 6**: `docs/contracts/db-init.sql` 을 컨테이너 DB 에서 실행해 에러 없이 통과

## 구현 힌트

### docker-compose.yml

[docs/infra/docker-compose.md](../../infra/docker-compose.md) 의 코드를 그대로 사용.

### .env.example

```
# 루트 (docker-compose 가 읽음)
DB_NAME=newspick
DB_USER=newspick
DB_PASSWORD=newspick

# Backend (backend/.env 또는 IDE 환경변수)
# DB_USER, DB_PASSWORD 위와 동일
# AI_SERVICE_URL=http://localhost:8000
# AI_SERVICE_TIMEOUT_SECONDS=120

# AI (ai/.env)
# UPSTAGE_API_KEY=...
# LANGCHAIN_TRACING_V2=true
# LANGCHAIN_API_KEY=...
# LANGCHAIN_PROJECT=newspick-mvp
# DATABASE_URL=postgresql://newspick:newspick@localhost:5432/newspick

# Frontend (frontend/.env.local)
# NEXT_PUBLIC_API_BASE=http://localhost:8080
```

### Spring Initializr (backend/)

브라우저에서 https://start.spring.io 로:
- Project: Gradle - Groovy
- Language: Java
- Spring Boot: 3.4.x
- Java: 17
- Dependencies: Web, JPA, PostgreSQL Driver, Validation, Flyway Migration, Lombok
- Group: `com.newspick`
- Artifact: `newspick`

생성 후 `backend/` 에 압축 해제. `application.yml` 작성은 [docs/backend/spring-boot.md](../../backend/spring-boot.md) 참조.

`src/main/resources/db/migration/V1__init.sql` 은 `docs/contracts/db-init.sql` 의 **사본** (서로 다른 파일이지만 내용은 1대1 동일하게 유지).

### create-next-app (frontend/)

```bash
pnpm create next-app@latest frontend \
  --typescript --tailwind --app --no-src-dir --import-alias "@/*" \
  --use-pnpm
```

이후 Tailwind v4 마이그레이션 ([docs/frontend/tailwind.md](../../frontend/tailwind.md) 의 `@theme` 셋업).

### uv init (ai/)

```bash
uv init ai --package
cd ai
uv add fastapi uvicorn langgraph langchain-upstage hdbscan numpy asyncpg pgvector feedparser
uv add --dev pytest pytest-asyncio httpx vcrpy
```

`src/newspick_ai/main.py` 에 빈 FastAPI 앱:

```python
from fastapi import FastAPI
app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "ok"}
```

### .gitignore

```
# OS
.DS_Store
Thumbs.db

# IDE
.idea/
.vscode/

# 환경
.env
.env.local
.env.*.local

# Backend
backend/build/
backend/.gradle/
backend/out/

# Frontend
frontend/node_modules/
frontend/.next/
frontend/.turbo/

# AI
ai/.venv/
ai/__pycache__/
ai/**/__pycache__/
ai/.pytest_cache/

# DB volume (안전 차원)
pgdata/
```

## 검증 방법

**자동**:
```bash
docker compose up -d
docker compose ps                                                  # db healthy
cd backend && ./gradlew build && cd ..
cd frontend && pnpm install && pnpm build && cd ..
cd ai && uv sync && uv run python -c "import newspick_ai" && cd ..
```
모두 성공 종료.

**수동**:
1. `docs/contracts/` 의 모든 파일이 존재하고 변경되지 않았는지 확인 (git diff 가 비어있음).
2. 각 트랙 디렉토리에서 빈 프로젝트 빌드 결과(JAR/Next dev/uvicorn) 1회 실행 가능.
3. 사용자가 "다음 step 부터 트랙별 병렬 개발 시작 가능" 판단.

## 완료 후

- progress.md 의 BOOT 체크박스 ✅
- 다음: BE-001 / FE-001 / AI-001 을 **병렬로** 진행 가능 (3명이 동시에 시작해도 충돌 없음)

## 결정 완료 테스트 명세

- **테스트 이름**: `bootstrap_contracts_and_workspace_are_ready`
- **fixture**: repo root의 `docs/contracts/`, `docker-compose.yml`, `.env.example`, `docs/progress/` 파일 세트.
- **action**: 계약 파일 존재 여부와 docker compose config, progress 파일 경로를 검사한다.
- **assertions**:
  - `docs/contracts/openapi.yaml`, `python-ai.yaml`, `sse-events.md`, `db-init.sql`이 존재한다.
  - `docker compose config`가 성공한다.
  - `docs/progress/boot.md`, `be.md`, `fe.md`, `ai.md`가 존재한다.
- **mock strategy**: 외부 API를 호출하지 않는다. Docker compose 설정 검증만 수행한다.
- **out of scope**: FE/BE/AI 기능 구현과 서버 실행 검증은 각 트랙 step에서 수행한다.
