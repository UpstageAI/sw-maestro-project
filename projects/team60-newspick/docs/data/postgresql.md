# PostgreSQL

## 선정 이유

- 관계형 DB + 벡터 검색(pgvector 확장)을 한 DB 에서 처리.
- Spring/Python 모두 풍부한 클라이언트 라이브러리.
- 작업환경 자주 바뀌는 환경에서 Docker 이미지 한 줄로 실행 가능.

## 버전

| 항목 | 값 |
|---|---|
| PostgreSQL | 16 |
| pgvector | 0.7.x (이미지에 동봉) |
| 이미지 | `pgvector/pgvector:pg16` |

## 운영 정책

- **로컬 개발**: Docker 컨테이너로만 실행. 호스트에 직접 설치하지 않는다 ([infra/docker-compose.md](../infra/docker-compose.md)).
- **데이터 영속성**: Docker named volume (`newspick_pgdata`) 마운트. `docker compose down` 으로는 데이터 안 사라지고, `docker compose down -v` 만 데이터 삭제.
- **발표 시연**: 시연 1~2일 전 파이프라인 1회 실행 → DB 고정 ([product/demo-strategy.md](../product/demo-strategy.md)). 시연 당일 추가 수집 X.
- **백업**: MVP 단계 자동 백업 없음. 시연 직전 `pg_dump` 1회로 안전망 확보 권장:
  ```bash
  docker exec newspick-db pg_dump -U newspick newspick > demo-snapshot.sql
  ```

## 접속 정보 (dev)

| 항목 | 값 |
|---|---|
| Host | `localhost` |
| Port | `5432` |
| Database | `newspick` |
| User | `newspick` (env `DB_USER`) |
| Password | `newspick` (env `DB_PASSWORD`) — dev only, 시연 환경 변경 시 환경변수로 |

## 마이그레이션

Spring 의 Flyway 가 단독 권한자. 시작 시 `db/migration/V*__*.sql` 자동 실행.

```
backend/src/main/resources/db/migration/
├── V1__init.sql            # CREATE EXTENSION vector; articles, daily_reports 테이블
├── V2__add_quiz_jsonb.sql  # 필요 시 alter
└── ...
```

`V1__init.sql` 골격 (자세한 컬럼은 [data/pgvector.md](pgvector.md)):

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE articles (
  id           text PRIMARY KEY,
  url          text UNIQUE NOT NULL,
  title        text NOT NULL,
  source       text NOT NULL,
  category     text NOT NULL,
  published_at timestamptz NOT NULL,
  raw_text     text,
  summary      jsonb,
  keywords     jsonb,
  importance   text,
  context      text,
  importance_score smallint,
  quiz         jsonb,
  embedding    vector(4096),
  status       text NOT NULL,
  created_at   timestamptz NOT NULL DEFAULT now(),
  updated_at   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_articles_published_at ON articles (published_at DESC);
CREATE INDEX idx_articles_status ON articles (status);
CREATE INDEX idx_articles_category ON articles (category);

CREATE TABLE daily_reports (
  report_date       date PRIMARY KEY,
  report_updated_at timestamptz NOT NULL,
  briefing          text NOT NULL,
  flow              jsonb NOT NULL,
  headline          jsonb NOT NULL,
  sub_articles      jsonb NOT NULL,
  keywords          jsonb NOT NULL,
  created_at        timestamptz NOT NULL DEFAULT now()
);
```

## 주의점

- 4096차원 벡터는 row 당 약 16KB(float4 × 4096). 하루 30건이면 미미하지만 1년 누적이면 ~6GB 정도.
- `pgvector` 확장은 superuser 권한 필요. Docker 이미지는 기본 `postgres` 가 superuser 라 문제없음.
- `psql` 접근:
  ```bash
  docker exec -it newspick-db psql -U newspick -d newspick
  ```

## 레퍼런스

- pgvector/pgvector image: https://hub.docker.com/r/pgvector/pgvector
- pgvector docs: https://github.com/pgvector/pgvector
- PostgreSQL 16 release notes: https://www.postgresql.org/docs/16/release.html
