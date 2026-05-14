# Docker Compose (DB 전용)

작업환경(노트북·데스크톱)이 자주 바뀌므로 **PostgreSQL+pgvector 만 컨테이너화** 한다. Spring·Python·Next 는 호스트에서 직접 실행 (IDE 디버깅 용이).

## 파일 위치

프로젝트 루트의 `docker-compose.yml`.

## docker-compose.yml

```yaml
services:
  db:
    image: pgvector/pgvector:pg16
    container_name: newspick-db
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${DB_NAME:-newspick}
      POSTGRES_USER: ${DB_USER:-newspick}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-newspick}
    ports:
      - "5432:5432"
    volumes:
      - newspick_pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-newspick} -d ${DB_NAME:-newspick}"]
      interval: 5s
      timeout: 3s
      retries: 10

volumes:
  newspick_pgdata:
```

## 환경 변수 (.env)

루트의 `.env` (gitignore):

```
DB_NAME=newspick
DB_USER=newspick
DB_PASSWORD=newspick
```

> dev 환경 비밀번호. 시연용 외부 노출 시 변경.

## 실행 / 정지

```bash
# 시작 (백그라운드)
docker compose up -d

# 로그 보기
docker compose logs -f db

# 정지 (데이터 보존)
docker compose down

# 정지 + 데이터 삭제 (주의!)
docker compose down -v
```

## 새 작업 환경 셋업 절차

새 노트북에서:

```bash
# 1. Docker Desktop 설치 (또는 colima/orbstack)
# 2. 저장소 클론
git clone <repo>
cd newspick
# 3. .env 작성 (.env.example 복사)
cp .env.example .env
# 4. DB 기동
docker compose up -d
# 5. Spring 실행 → Flyway 가 자동으로 V1__init.sql 적용
cd backend && ./gradlew bootRun
# 6. Python AI 서비스 기동
cd ../ai && uv run python -m newspick_ai
# 7. Next.js 실행
cd ../frontend && pnpm install && pnpm dev
```

## 데이터 이전 (환경 간)

작업환경 옮길 때 DB 스냅샷을 옮기고 싶다면:

```bash
# 기존 환경
docker exec newspick-db pg_dump -U newspick newspick > newspick.sql

# 새 환경 (DB 띄운 뒤)
cat newspick.sql | docker exec -i newspick-db psql -U newspick -d newspick
```

## 시연 환경 운영

[product/demo-strategy.md](../product/demo-strategy.md) 의 데이터 고정 정책에 따라:

1. 발표 1~2일 전 파이프라인 1회 실행 → 기사 20~30건 + 리포트 1건 + 임베딩 모두 채움.
2. `pg_dump` 로 스냅샷 저장.
3. 발표 직전 호스트에서 컨테이너 재기동 후 스냅샷 import — 새벽 기사 자동 수집 같은 변수 차단.

## 향후 확장 (Phase B 이후)

본 MVP 에는 포함하지 않지만 필요해지면:

- **Python AI 서비스 컨테이너화**: 새 작업환경에서 Python 의존성(`hdbscan` 빌드 등)이 까다로우면 추가 검토. 현재는 호스트 venv/uv 로 충분.
- **Spring 컨테이너화**: 시연 환경 표준화에 필요해지면. 현재는 IDE 실행이 편의성 우선.
- **외부 노출**: 발표 시 외부 IP 노출 시 reverse proxy(nginx/caddy) 추가.

## 주의점

- 이미지 `pgvector/pgvector:pg16` 는 Apple Silicon(arm64) 지원. M1/M2/M3 노트북에서도 그대로 동작.
- 5432 포트가 호스트에서 이미 사용 중이면 호스트 측 매핑만 변경: `"5433:5432"`.
- volume 이름 `newspick_pgdata` 는 docker context(=설치된 docker daemon) 단위로 보존된다. context 가 바뀌면(예: Docker Desktop ↔ colima 전환) 데이터가 안 보일 수 있음 — 그 경우 위 데이터 이전 절차를 사용.

## 레퍼런스

- pgvector image: https://hub.docker.com/r/pgvector/pgvector
- Docker Compose v2 spec: https://docs.docker.com/compose/compose-file/
