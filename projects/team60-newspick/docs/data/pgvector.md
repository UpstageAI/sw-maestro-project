# pgvector

## 사용 범위

NewPick 에서 pgvector 는 두 곳에서 사용된다.

1. **EmbeddingGenerator 노드**: `articles.embedding vector(4096)` 컬럼에 Solar 임베딩 저장. 정의: [architecture/pipeline-design.md](../architecture/pipeline-design.md) 의 EmbeddingGenerator.
2. **AI 챗 RAG 검색 / 리포트 클러스터링**: 코사인 유사도(`<=>`) 검색 + HDBSCAN 클러스터링 입력. 정의: [ai/rag-chat.md](../ai/rag-chat.md), [data/hdbscan.md](hdbscan.md).

벡터 작업은 **모두 Python** 이 수행한다 — Spring 은 `embedding` 컬럼을 SELECT 절에서 명시 제외 ([backend/jpa.md](../backend/jpa.md)).

## 컬럼 정의

```sql
CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE articles
  ADD COLUMN embedding vector(4096),
  ADD COLUMN importance_score smallint;
```

차원 4096은 Solar `solar-embedding-1-large-{passage,query}` 의 출력 차원이다.

## 인덱스 전략 (MVP: 인덱스 없음)

**MVP 에서는 인덱스를 만들지 않는다.** 이유:

- 하루 20~30건 수집, 시연 직전 DB 에 100건 미만으로 고정.
- 100건 미만 sequential scan 은 코사인 유사도 계산 포함해도 수 ms 이하.
- pgvector 의 HNSW 인덱스는 기본 `vector` 타입에서 **2000차원까지만 지원** — 4096차원 인덱싱하려면 `halfvec(4096)` 으로 캐스팅 필요.
- IVFFlat 도 동일한 2000차원 한계.

따라서 다음 정책:

- **기본**: 인덱스 없이 풀스캔.
- **데이터 증가 시**: `halfvec` + HNSW 로 마이그레이션 (아래 §확장 참고).

## 유사도 쿼리 (인덱스 없음)

```sql
SELECT id, title, summary, source, published_at, category
FROM articles
WHERE status = 'summarized'
  AND DATE(published_at) >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY embedding <=> $1   -- $1 = query 임베딩 (4096-dim)
LIMIT 5;
```

`<=>` 는 코사인 거리(0 = 동일, 2 = 정반대). pgvector 는 `<->` (L2), `<#>` (negative inner product) 도 제공.

## 확장: halfvec + HNSW (데이터 증가 시)

```sql
-- 기존 vector(4096) 를 보존하면서 HNSW 인덱스용 캐스트 인덱스 생성
CREATE INDEX articles_embedding_hnsw_halfvec
  ON articles USING hnsw ((embedding::halfvec(4096)) halfvec_cosine_ops);

-- 검색 시
SELECT ...
FROM articles
ORDER BY embedding::halfvec(4096) <=> $1::halfvec(4096)
LIMIT 5;
```

`halfvec` 은 16비트 부동소수점 — 정밀도가 살짝 낮아지지만 검색 품질에 미치는 영향은 거의 없고 인덱스 크기가 절반.

## DDL 위치

마이그레이션은 Spring Flyway 가 단독 관리한다 ([data/postgresql.md](postgresql.md)). Python 은 DDL 을 만들지 않고 INSERT/UPDATE 만 수행.

## 임베딩 INSERT (Python)

```python
import asyncpg

async def persist_article(conn, article):
    await conn.execute("""
        INSERT INTO articles (id, url, title, source, category, published_at,
                              summary, keywords, importance, context, importance_score,
                              quiz, embedding, status)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
        ON CONFLICT (url) DO UPDATE SET
          summary = EXCLUDED.summary,
          embedding = EXCLUDED.embedding,
          status = EXCLUDED.status,
          updated_at = now()
    """,
    article.id, article.url, article.title, article.source, article.category,
    article.published_at,
    json.dumps(article.summary), json.dumps(article.keywords),
    article.importance, article.context, article.importance_score,
    json.dumps([q.model_dump() for q in article.quiz]),
    article.embedding,    # asyncpg 가 list[float] 를 vector 로 자동 변환 (pgvector-python 등록 후)
    article.status)
```

`pgvector-python` 패키지를 등록하면 `list[float]` ↔ `vector` 자동 변환:

```python
from pgvector.asyncpg import register_vector

conn = await asyncpg.connect(...)
await register_vector(conn)
```

## 주의점

- 4096차원 벡터를 매번 직렬화해 전송하므로 INSERT 페이로드가 큼. 배치 INSERT 시 prepared statement 재사용.
- `VACUUM` 자동 실행되도록 두고, 수동 튜닝은 MVP 단계 불요.
- `embedding IS NULL` 인 row 가 검색에 끼어들지 않도록 `WHERE status = 'summarized' AND embedding IS NOT NULL`.

## 레퍼런스

- pgvector README: https://github.com/pgvector/pgvector
- pgvector-python: https://github.com/pgvector/pgvector-python
- HNSW vs IVFFlat: https://github.com/pgvector/pgvector#indexing
