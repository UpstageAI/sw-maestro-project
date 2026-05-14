# 파이프라인 설계

기획서에서 말하는 AI 구현은 단순히 LLM을 한 번 호출해 요약을 만드는 방식이 아니다. RSS 기사 하나가 들어오면 여러 단계의 AI/비AI 처리를 순서대로 실행하고, 실패하면 재시도하거나 제외하는 흐름이 필요하다.

이때 역할을 정확히 나누면 다음과 같다.

- LangGraph: AI 파이프라인의 오케스트레이션 담당
- LangSmith: 실행 과정 관측, 디버깅, 품질 추적 담당

즉, `LangSmith 오케스트레이션`이라기보다는 `LangGraph 오케스트레이션 + LangSmith 관측/트레이싱`으로 이해하는 것이 정확하다.

> LangGraph 자체의 도입 이유는 [ai/langgraph.md](../ai/langgraph.md), LangSmith 활용은 [ai/langsmith.md](../ai/langsmith.md) 참조.

## LangGraph 노드 설계

기사 하나를 처리하는 기본 그래프는 다음처럼 설계할 수 있다.

```text
Collector
-> Deduplicator
-> ArticleExtractor
-> Summarizer
-> SummaryValidator
-> QuizGenerator
-> Persistor
```

검증 실패가 있는 경우:

```text
SummaryValidator
-> retry 가능: Summarizer로 재진입
-> retry 초과: Skip 또는 ReviewRequired
```

## 노드별 역할

### 1. Collector

RSS 피드에서 기사 후보를 가져온다.

역할:

- RSS URL 호출
- 신규 entry 추출
- 제목, 링크, 발행일, 출처, 카테고리 정리

출력:

```json
{
  "url": "https://example.com/news/1",
  "title": "기사 제목",
  "source": "ZDNet Korea",
  "publishedAt": "2026-05-10T09:20:00+09:00",
  "category": "테크"
}
```

### 2. Deduplicator

이미 처리한 기사인지 확인한다.

중복 판단 기준:

- URL 동일
- 제목 동일
- 제목이 거의 동일하고 출처가 같은 경우

결과:

- 신규 기사면 다음 단계 진행
- 중복이면 종료

### 3. ArticleExtractor

RSS description 또는 원문 페이지에서 본문 텍스트를 추출한다.

주의:

- robots.txt 또는 접근 제한이 있는 페이지는 무리하게 크롤링하지 않는다.
- 본문 파싱이 실패하면 `rawTextStatus: "description_only"`로 표시한다.
- 본문이 너무 짧으면 요약 품질이 낮아질 수 있으므로 검증 단계에서 다룬다.

### 4. Summarizer

LLM을 호출해 기사 요약을 만든다.

출력:

- 3~5문장 요약
- 핵심 키워드
- 왜 중요한지 한 줄 설명 (`importance`)
- 조금 더 알아야 할 배경 2~3문장 (`context`): 기사 본문에서 독자가 알면 좋을 추가 맥락. 원문에 근거하며 추측을 포함하지 않는다.
- UI 표시용 짧은 요약
- `importanceScore`: 기사의 사회적 중요도 1~10 정수 (10 = 사회 전반에 즉각적 영향, 1 = 단순 단신)

프롬프트 끝에 다음을 추가한다.

```text
마지막으로 이 기사의 사회적 중요도를 1~10으로 평가하고
importance_score 필드에 정수로 출력하시오.
기준: 10 = 사회 전반에 즉각적 영향, 1 = 단순 단신
```

### 4-1. EmbeddingGenerator

Summarizer 직후 실행되며, 요약 텍스트를 벡터로 변환한다.

역할:

- 요약 문장(3~5개)을 이어붙인 텍스트를 입력으로 사용
- Upstage `solar-embedding-1-large-passage` 모델 호출 (출력 차원: **4096**)
- 생성된 벡터를 DB의 `embedding` 컬럼에 저장

DB 요구사항:

- PostgreSQL + pgvector 확장
- `articles` 테이블에 `embedding vector(4096)`, `importance_score smallint` 컬럼 추가
- 인덱스 정책은 [data/pgvector.md](../data/pgvector.md) 참조 (MVP 는 인덱스 없이 seq scan, 데이터 늘면 halfvec+HNSW)

```python
from langchain_upstage import UpstageEmbeddings

embeddings_passage = UpstageEmbeddings(
    model="solar-embedding-1-large-passage",
)

async def embedding_generator(state: ArticleState) -> ArticleState:
    text = " ".join(state["summary"])
    vector = await embeddings_passage.aembed_query(text)
    state["embedding"] = vector  # 4096-dim
    return state
```

> 챗에서는 `solar-embedding-1-large-query` 를 짝으로 사용한다. passage/query 는 Solar 임베딩 모델의 비대칭 페어 — 검색 정확도를 위해 둘 다 사용해야 한다. 자세한 모델 사용처는 [ai/solar.md](../ai/solar.md) 참조.

### 5. SummaryValidator

요약이 원문과 맞는지 검증한다.

판정:

- `pass`: 다음 단계 진행
- `retry`: 요약 재생성
- `skip`: 요약 비공개 또는 원문만 보기
- `review_required`: 사용자가 볼 수는 있지만 주의 표시 필요

### 6. QuizGenerator

검증을 통과한 요약을 바탕으로 O/X 퀴즈 3문항을 만든다.

조건:

- 정답이 명확해야 한다.
- 기사 요약에 근거해야 한다.
- 해설이 있어야 한다.
- 너무 상식적인 문제는 피한다.

### 7. Persistor

최종 결과를 DB에 저장한다.

저장 대상:

- 기사 메타데이터
- 요약
- 키워드
- 중요도 설명
- 퀴즈
- 처리 상태
- 실패 사유
- 재시도 횟수

## LangGraph State 설계 예시

LangGraph에서는 노드 간에 공유되는 상태를 명확히 정의하는 것이 중요하다.

예시:

```json
{
  "articleId": "article_001",
  "url": "https://example.com/news/1",
  "title": "기사 제목",
  "source": "ZDNet Korea",
  "category": "테크",
  "publishedAt": "2026-05-10T09:20:00+09:00",
  "rawText": "기사 본문",
  "rawTextStatus": "full_text",
  "summary": [],
  "keywords": [],
  "importance": "",
  "validation": {
    "status": "pending",
    "reason": ""
  },
  "quiz": [],
  "retryCount": 0,
  "status": "processing",
  "error": null
}
```

## 조건부 라우팅 예시

요약 검증 결과에 따라 다음 노드가 달라진다.

```text
if validation.status == "pass":
  -> QuizGenerator

if validation.status == "retry" and retryCount < 2:
  -> Summarizer

if validation.status == "retry" and retryCount >= 2:
  -> ReviewRequired

if validation.status == "skip":
  -> Skip
```

이 구조를 사용하면 AI 결과가 나쁘게 나왔을 때도 전체 파이프라인이 무너지지 않는다.

## 리포트용 LangGraph 흐름

데일리 리포트는 기사 하나가 아니라 하루치 기사 묶음을 처리한다.

흐름:

```text
DailyArticleLoader
-> ArticleClusterer
-> CategoryClusterer
-> TrendSummarizer
-> DailyReportGenerator
-> ReportPersistor
```

역할:

- `DailyArticleLoader`: 오늘 수집된 기사와 임베딩 불러오기
- `ArticleClusterer`: 임베딩 유사도 기반 HDBSCAN 클러스터링으로 헤드라인/서브 기사 선정
- `CategoryClusterer`: 카테고리별 기사 묶기
- `TrendSummarizer`: 카테고리별 핵심 흐름 한 줄 요약 (오늘의 흐름 섹션용)
- `DailyReportGenerator`: AI 브리핑 한 줄 문장 생성
- `ReportPersistor`: 리포트 저장

### ArticleClusterer 상세

```python
async def article_clusterer(state: ReportState) -> ReportState:
    articles = await db.fetch("""
        SELECT id, category, source, importance_score, embedding
        FROM articles
        WHERE DATE(published_at) = CURRENT_DATE
          AND status = 'summarized'
    """)

    embeddings = np.array([a["embedding"] for a in articles])

    # HDBSCAN 클러스터링 (min_cluster_size=2: 하루 20~30건 기준)
    clusterer = hdbscan.HDBSCAN(min_cluster_size=2, metric="euclidean")
    labels = clusterer.fit_predict(embeddings)

    clusters = defaultdict(list)
    for article, label in zip(articles, labels):
        if label != -1:  # -1은 단독 기사 (노이즈)
            clusters[label].append(article)

    # 클러스터 크기(기사 수) 기준 정렬
    ranked = sorted(clusters.values(), key=len, reverse=True)
    state["ranked_clusters"] = ranked
    return state
```

### 헤드라인 및 서브 기사 선정 로직

```python
def select_headline_and_subs(ranked_clusters):
    # 1위 클러스터에서 importance_score 최고 기사 → 헤드라인
    headline = max(ranked_clusters[0], key=lambda a: a["importance_score"])
    # 배지: 클러스터 내 고유 출처(source) 수 (받아쓰기 기사 제외)
    headline_source_count = len({a["source"] for a in ranked_clusters[0]})

    subs = []
    used_categories = {headline["category"]}
    for cluster in ranked_clusters[1:]:
        candidate = max(cluster, key=lambda a: a["importance_score"])
        if candidate["category"] not in used_categories:
            subs.append({
                "article": candidate,
                "source_count": len({a["source"] for a in cluster})
            })
            used_categories.add(candidate["category"])
        if len(subs) == 2:
            break

    return headline, headline_source_count, subs
```

"N개 매체 보도" 배지는 기사 수가 아닌 **고유 출처(source) 수** 기준으로 표시한다. 통신사 기사를 받아쓰기한 기사가 같은 클러스터에 묶이더라도 배지 수치가 과장되지 않는다.

## 구현 시 주의점

- LangGraph를 도입한다고 해서 모든 노드를 LLM으로 만들 필요는 없다.
- 중복 제거, 상태 저장, 카테고리 필터링은 일반 코드로 처리하는 것이 더 안정적이다.
- LLM은 요약, 검증, 퀴즈 생성, 리포트 문장화처럼 언어 판단이 필요한 곳에 집중해서 사용한다.
- LangSmith는 서비스 기능이 아니라 개발/운영 품질을 높이는 도구로 봐야 한다.
- 사용자가 보는 UI에는 도구명보다 `AI 요약`, `원문 기반`, `검토 필요` 같은 이해 가능한 상태를 보여주는 것이 좋다.
