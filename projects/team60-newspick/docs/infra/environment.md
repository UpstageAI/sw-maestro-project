# 환경 변수 / 포트 / 실행 순서

여러 작업환경에서 일관되게 셋업할 수 있도록 환경 변수와 포트를 한 곳에 정리.

## 포트 맵

| 서비스 | 포트 | 호스트/컨테이너 |
|---|---|---|
| PostgreSQL | 5432 | Docker 컨테이너 (호스트 매핑 동일) |
| Spring Boot | 8080 | 호스트 |
| Python AI (FastAPI) | 8000 | 호스트 |
| Next.js (dev) | 3000 | 호스트 |

## 환경 변수

### 프로젝트 루트 `.env`

Docker Compose 가 읽음 ([infra/docker-compose.md](docker-compose.md)).

```
DB_NAME=newspick
DB_USER=newspick
DB_PASSWORD=newspick
```

### `backend/.env` (또는 IDE 환경변수)

```
DB_USER=newspick
DB_PASSWORD=newspick
AI_SERVICE_URL=http://localhost:8000
AI_SERVICE_TIMEOUT_SECONDS=120
```

### `ai/.env`

```
UPSTAGE_API_KEY=...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=...
LANGCHAIN_PROJECT=newspick-mvp
DATABASE_URL=postgresql://newspick:newspick@localhost:5432/newspick
```

### `frontend/.env.local`

```
NEXT_PUBLIC_API_BASE=http://localhost:8080
```

> Next.js 에는 **민감 키를 절대 두지 않는다**. `NEXT_PUBLIC_` prefix 가 붙으면 빌드 타임에 클라이언트 번들로 박힘.

## .env.example

각 디렉토리(루트/backend/ai/frontend)에 `.env.example` 을 두고 git 추적. 실제 `.env` / `.env.local` 은 `.gitignore`.

## 실행 순서 (depencency 순)

```
1. PostgreSQL  (docker compose up -d)
2. Spring      (./gradlew bootRun)        # Flyway 가 V1__init.sql 적용
3. Python AI   (uv run python -m newspick_ai)
4. Next.js     (pnpm dev)
```

순서를 어기면:
- Spring 이 먼저 시작했는데 DB 가 없으면 connection refused 후 종료. compose 의 healthcheck 로 보장.
- Python 이 안 떠 있으면 Spring 의 `/api/refresh-stream` 호출이 timeout.

## 시연 직전 체크리스트

발표 30분 전:

- [ ] DB 컨테이너 healthy (`docker compose ps`)
- [ ] DB 에 기사 20~30건, 리포트 1건 존재 (`SELECT COUNT(*) FROM articles`)
- [ ] Spring 8080 응답 (`curl localhost:8080/api/feed | head`)
- [ ] Python 8000 응답 (`curl localhost:8000/health`)
- [ ] Next.js 빌드 후 prod 모드 실행 (`pnpm build && pnpm start`)
- [ ] 시연 질문 3~4개 답변 정상 ([product/demo-strategy.md](../product/demo-strategy.md))
- [ ] LangSmith trace 확인 가능 (모니터링용)

## 주의점

- `localhost` 가 아닌 다른 호스트에서 접근해야 할 때 (예: 폰 시연) Spring/Python `application.yml` 의 `server.address` 와 CORS 갱신.
- API 키 노출 사고 시 Upstage 콘솔에서 즉시 rotate.
