# NewPick AI 구현 계획

## 목표

NewPick의 AI는 뉴스를 새로 쓰는 역할이 아니라, RSS로 수집한 기사 내용을 사용자가 빠르게 이해하고 복습할 수 있도록 정제하는 역할을 맡는다.

핵심 목표는 다음과 같다.

1. RSS 기사에서 필요한 메타데이터와 본문을 수집한다.
2. 기사 내용을 사실 중심으로 3~5문장 요약한다.
3. 요약 품질을 검증하고 실패한 요약은 재시도하거나 제외한다.
4. 요약 내용을 바탕으로 O/X 퀴즈 3문항을 만든다.
5. 하루 단위로 카테고리별 핵심 이슈를 묶어 데일리 리포트를 만든다.

## AI가 맡는 역할

### 1. 콘텐츠 수집 에이전트

RSS 피드에서 신규 기사를 가져오는 역할이다.

입력:

- RSS 피드 URL
- 마지막 수집 시각
- 관심 카테고리 목록

출력:

- 기사 URL
- 제목
- 출처
- 발행 시각
- 카테고리
- RSS description
- 본문 후보 텍스트

주의할 점:

- 공식 RSS가 제공되는 매체만 사용한다.
- 같은 URL이나 같은 제목의 중복 기사는 제거한다.
- 본문 파싱이 실패하면 RSS description 기반 요약 후보로 표시한다.

### 2. 요약 에이전트

기사 본문을 읽고 사실 중심의 짧은 요약을 만든다.

요약 원칙:

- 3~5문장으로 제한한다.
- 원문에 없는 내용을 추가하지 않는다.
- 추측, 평가, 과장 표현을 넣지 않는다.
- 사용자가 이해하기 쉬운 문장으로 바꾼다.
- 출처가 불명확한 정보는 요약에 포함하지 않는다.

출력 예시:

```json
{
  "summary": [
    "AI 검색 서비스들이 검색 결과를 요약형 답변으로 제공하는 기능을 강화하고 있다.",
    "사용자는 긴 기사 목록을 보기 전에 핵심 흐름과 배경을 먼저 확인할 수 있다.",
    "서비스 경쟁의 중심은 출처 표시와 개인화 추천으로 이동하고 있다."
  ],
  "keywords": ["AI 검색", "뉴스 요약", "출처 신뢰도"],
  "importance": "검색 결과를 단순히 나열하는 방식에서 AI가 먼저 흐름을 정리해주는 방식으로 뉴스 소비가 바뀌고 있다."
}
```

### 3. 검증 에이전트

AI 요약이 원문과 어긋나지 않는지 확인한다.

검증 기준:

- 원문에 없는 정보가 들어갔는가
- 숫자, 기관명, 인물명, 시점이 잘못 바뀌었는가
- 요약이 너무 추상적이거나 기사 핵심을 놓쳤는가
- 정치적/사회적 사안에서 주관적 판단이 들어갔는가

판정 결과:

```json
{
  "status": "pass",
  "reason": "원문 주요 내용과 요약이 일치함"
}
```

또는:

```json
{
  "status": "retry",
  "reason": "원문에 없는 전망 표현이 포함됨"
}
```

실패 처리:

- 1차 실패: 요약 재생성
- 2차 실패: 해당 기사 요약 제외
- 본문 부족: 원문 링크만 제공하고 `본문 확인 필요` 상태로 저장

### 4. 퀴즈 생성 에이전트

요약을 바탕으로 O/X 퀴즈 3문항을 만든다.

퀴즈 원칙:

- 반드시 요약 또는 원문에 근거해야 한다.
- 애매한 판단형 문항은 만들지 않는다.
- 정답이 명확히 O 또는 X로 나뉘어야 한다.
- 문항은 짧고 사실 확인 중심이어야 한다.
- 해설은 1~2문장으로 충분하다.

출력 예시:

```json
{
  "quizzes": [
    {
      "question": "AI 검색 서비스는 검색 결과를 요약형 답변으로 보여주는 기능을 강화하고 있다.",
      "answer": "O",
      "explanation": "요약에서 검색 결과를 문장형 답변으로 제공하는 기능이 확대되고 있다고 설명했다."
    },
    {
      "question": "사용자는 긴 기사 목록을 보기 전에 핵심 흐름을 먼저 확인할 수 있다.",
      "answer": "O",
      "explanation": "요약은 사용자가 원문을 읽기 전 맥락을 빠르게 잡도록 돕는다."
    },
    {
      "question": "이 기사에서 중요한 경쟁 포인트는 오프라인 배달 속도다.",
      "answer": "X",
      "explanation": "기사의 핵심은 출처 표시, 개인화 추천, 답변 품질 같은 AI 검색 경험이다."
    }
  ]
}
```

### 5. 리포트 생성 에이전트

하루 동안 수집된 기사와 사용자 활동을 묶어 데일리 리포트를 만든다.

입력:

- 오늘 수집된 기사 목록
- 카테고리별 기사 수
- 주요 키워드
- 사용자가 읽은 기사
- 퀴즈 정답률

출력:

- 오늘의 핵심 이슈 3개
- 카테고리별 요약
- 많이 등장한 키워드
- 사용자의 읽기/퀴즈 활동 요약

리포트 예시:

```json
{
  "date": "2026-05-10",
  "headline": "오늘은 AI 검색과 환율 변동 이슈가 두드러졌어요.",
  "categories": [
    {
      "category": "테크",
      "summary": "AI 검색 서비스들이 요약형 답변과 출처 표시 기능을 강화하고 있다.",
      "keywords": ["AI 검색", "요약", "출처"]
    },
    {
      "category": "경제",
      "summary": "환율 변동성과 금리 전망이 시장의 주요 변수로 언급됐다.",
      "keywords": ["환율", "금리", "물가"]
    }
  ],
  "userStats": {
    "readArticles": 5,
    "quizAccuracy": 80
  }
}
```

## 전체 처리 흐름

```text
RSS 수집
-> 신규 기사 필터링
-> 기사 본문 추출
-> AI 요약 생성
-> 요약 검증
-> 실패 시 재요약 또는 제외
-> O/X 퀴즈 생성
-> DB 저장
-> 홈 피드 / 상세 / 리포트 UI에서 조회
```

## LangGraph와 LangSmith 적용 방식

기획서에서 말하는 AI 구현은 단순히 LLM을 한 번 호출해 요약을 만드는 방식이 아니다. RSS 기사 하나가 들어오면 여러 단계의 AI/비AI 처리를 순서대로 실행하고, 실패하면 재시도하거나 제외하는 흐름이 필요하다.

이때 역할을 정확히 나누면 다음과 같다.

- LangGraph: AI 파이프라인의 오케스트레이션 담당
- LangSmith: 실행 과정 관측, 디버깅, 품질 추적 담당

즉, `LangSmith 오케스트레이션`이라기보다는 `LangGraph 오케스트레이션 + LangSmith 관측/트레이싱`으로 이해하는 것이 정확하다.

### LangGraph를 사용하는 이유

NewPick의 AI 처리는 다음처럼 단계가 나뉜다.

```text
RSS 수집
-> 본문 추출
-> 요약 생성
-> 요약 검증
-> 검증 실패 시 재요약
-> 퀴즈 생성
-> 저장
-> 리포트 생성
```

이 흐름은 단순 함수 하나보다 그래프 구조로 관리하는 것이 좋다.

LangGraph를 사용하면 다음을 명확하게 표현할 수 있다.

- 각 처리 단계를 노드로 분리
- 노드 간 상태 전달
- 검증 결과에 따른 조건부 분기
- 실패 시 재시도 횟수 관리
- 최종 저장 전 품질 검증
- 기사 단위 처리와 리포트 단위 처리 분리

### LangGraph 노드 설계

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

### 노드별 역할

#### 1. Collector

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

#### 2. Deduplicator

이미 처리한 기사인지 확인한다.

중복 판단 기준:

- URL 동일
- 제목 동일
- 제목이 거의 동일하고 출처가 같은 경우

결과:

- 신규 기사면 다음 단계 진행
- 중복이면 종료

#### 3. ArticleExtractor

RSS description 또는 원문 페이지에서 본문 텍스트를 추출한다.

주의:

- robots.txt 또는 접근 제한이 있는 페이지는 무리하게 크롤링하지 않는다.
- 본문 파싱이 실패하면 `rawTextStatus: "description_only"`로 표시한다.
- 본문이 너무 짧으면 요약 품질이 낮아질 수 있으므로 검증 단계에서 다룬다.

#### 4. Summarizer

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

#### 4-1. EmbeddingGenerator

Summarizer 직후 실행되며, 요약 텍스트를 벡터로 변환한다.

역할:

- 요약 문장(3~5개)을 이어붙인 텍스트를 입력으로 사용
- OpenAI `text-embedding-3-small` 모델 호출 (출력 차원: 1536)
- 생성된 벡터를 DB의 `embedding` 컬럼에 저장

DB 요구사항:

- PostgreSQL + pgvector 확장
- `articles` 테이블에 `embedding vector(1536)`, `importance_score smallint` 컬럼 추가
- 유사도 검색 인덱스: `CREATE INDEX ON articles USING ivfflat (embedding vector_cosine_ops)`

```python
async def embedding_generator(state: ArticleState) -> ArticleState:
    text = " ".join(state["summary"])
    response = await openai.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    state["embedding"] = response.data[0].embedding
    return state
```

#### 5. SummaryValidator

요약이 원문과 맞는지 검증한다.

판정:

- `pass`: 다음 단계 진행
- `retry`: 요약 재생성
- `skip`: 요약 비공개 또는 원문만 보기
- `review_required`: 사용자가 볼 수는 있지만 주의 표시 필요

#### 6. QuizGenerator

검증을 통과한 요약을 바탕으로 O/X 퀴즈 3문항을 만든다.

조건:

- 정답이 명확해야 한다.
- 기사 요약에 근거해야 한다.
- 해설이 있어야 한다.
- 너무 상식적인 문제는 피한다.

#### 7. Persistor

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

### LangGraph State 설계 예시

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

### 조건부 라우팅 예시

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

### 리포트용 LangGraph 흐름

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

#### ArticleClusterer 상세

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

#### 헤드라인 및 서브 기사 선정 로직

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

## RSS 피드 구성

클러스터링 효과를 위해 같은 이슈를 여러 매체가 다루는 환경이 필요하다. 피드는 종합 매체와 전문 매체를 함께 구독한다.

| 역할 | 매체 | 커버 카테고리 |
|---|---|---|
| 종합 (필수) | 연합뉴스, 뉴시스, 뉴스1 | 전체 |
| 테크 전문 | ZDNet Korea, 전자신문, IT동아 | 테크 |
| 경제 전문 | 한국경제, 매일경제, 이데일리 | 경제 |
| 방송 | KBS, YTN | 이슈/정책 |

목표: 피드 10~12개, 하루 수집 기사 20~30건.

종합 매체(연합뉴스, 뉴시스 등)는 대부분의 주요 이슈를 모두 다루기 때문에, 큰 이슈일수록 자연스럽게 클러스터 크기가 커진다. 전문 매체는 해당 카테고리의 심층 기사를 보완한다.

주의: 통신사 기사를 신문사가 그대로 받아쓰는 경우가 많다. Deduplicator에서 제목+출처 기준으로 1차 필터링하고, 배지 표시 시에는 고유 출처 수 기준을 사용해 과장을 방지한다.

## LangSmith 적용 방식

LangSmith는 사용자가 보는 기능을 직접 만드는 도구라기보다, AI 파이프라인이 제대로 동작하는지 확인하는 도구다.

NewPick에서는 다음 목적으로 사용할 수 있다.

### 1. 노드별 입력/출력 추적

각 기사 처리 과정에서 다음을 추적한다.

- 어떤 원문이 들어갔는가
- 어떤 요약이 생성되었는가
- 검증 결과가 무엇인가
- 퀴즈가 어떤 근거로 생성되었는가
- 어느 단계에서 실패했는가

이를 통해 요약 품질 문제를 빠르게 찾을 수 있다.

### 2. 요약 품질 디버깅

예를 들어 사용자가 `요약이 이상해요`를 신고했을 때 LangSmith trace를 보면 다음을 확인할 수 있다.

- 원문 본문이 충분했는가
- RSS description만 사용했는가
- 요약 프롬프트가 잘 적용되었는가
- 검증 노드가 왜 통과시켰는가
- 퀴즈 문항도 같은 오류를 따라갔는가

### 3. 비용과 지연시간 추적

기사 수가 늘어나면 AI 호출 비용과 처리 시간이 중요해진다.

LangSmith로 볼 수 있는 지표:

- 노드별 실행 시간
- 기사 1건당 전체 처리 시간
- 요약 생성 평균 지연
- 검증 재시도 비율
- 실패 기사 비율
- 토큰 사용량

### 4. 프롬프트 개선 실험

요약 프롬프트를 바꾸었을 때 결과가 좋아졌는지 비교할 수 있다.

비교 기준:

- 요약 길이
- 원문 충실도
- 퀴즈 정답 명확성
- 검증 실패율
- 사용자 신고율

### 5. 운영 중 모니터링

MVP 단계에서는 복잡한 대시보드보다 다음 정도만 확인해도 충분하다.

- 오늘 처리한 기사 수
- 요약 실패 기사 수
- 재시도 발생 기사 수
- 평균 처리 시간
- 사용자 신고 기사 수

## LangGraph와 LangSmith의 관계

두 도구의 관계를 간단히 정리하면 다음과 같다.

```text
LangGraph = 일을 진행하는 흐름 설계자
LangSmith = 그 일이 어떻게 진행됐는지 기록하고 분석하는 관찰자
```

NewPick에서는:

```text
LangGraph가 RSS 기사 처리 그래프를 실행한다.
LangSmith가 각 노드 실행 기록을 남긴다.
문제가 생기면 LangSmith trace를 보고 프롬프트나 노드 로직을 수정한다.
```

## MVP에서의 적용 범위

MVP에서 반드시 필요한 것:

- LangGraph 기반 기사 처리 흐름
- 요약 실패 시 재시도
- 퀴즈 생성
- 처리 상태 저장

MVP에서 있으면 좋은 것:

- LangSmith trace 연결
- 실패 케이스 확인
- 프롬프트 버전 관리

MVP 이후 고도화:

- 자동 평가 데이터셋 구축
- 카테고리별 요약 품질 비교
- 사용자 신고 기반 프롬프트 개선
- 리포트 품질 평가

## 구현 시 주의점

- LangGraph를 도입한다고 해서 모든 노드를 LLM으로 만들 필요는 없다.
- 중복 제거, 상태 저장, 카테고리 필터링은 일반 코드로 처리하는 것이 더 안정적이다.
- LLM은 요약, 검증, 퀴즈 생성, 리포트 문장화처럼 언어 판단이 필요한 곳에 집중해서 사용한다.
- LangSmith는 서비스 기능이 아니라 개발/운영 품질을 높이는 도구로 봐야 한다.
- 사용자가 보는 UI에는 도구명보다 `AI 요약`, `원문 기반`, `검토 필요` 같은 이해 가능한 상태를 보여주는 것이 좋다.

## 데이터 구조 초안

### Article

```json
{
  "id": "article_001",
  "url": "https://example.com/news/1",
  "title": "기사 원문 제목",
  "source": "ZDNet Korea",
  "category": "테크",
  "publishedAt": "2026-05-10T09:20:00+09:00",
  "rawText": "기사 본문",
  "summary": ["요약 문장 1", "요약 문장 2", "요약 문장 3"],
  "keywords": ["AI 검색", "요약", "출처"],
  "importance": "왜 중요한지 한 줄 설명",
  "context": "조금 더 알아야 할 배경 2~3문장",
  "status": "summarized"
}
```

### Quiz

```json
{
  "articleId": "article_001",
  "items": [
    {
      "question": "O/X 문항",
      "answer": "O",
      "explanation": "해설"
    }
  ]
}
```

### UserActivity

```json
{
  "userId": "session_uuid",
  "articleId": "article_001",
  "readAt": "2026-05-10T09:40:00+09:00",
  "quizScore": 3,
  "quizTotal": 3
}
```

## UI와 연결되는 AI 상태

AI 파이프라인 상태는 UI에 반드시 드러나야 한다.

추천 상태:

- `수집 중`: RSS에서 새 기사를 가져오는 중
- `요약 중`: AI 요약 생성 중
- `요약 완료`: 홈 카드에 노출 가능
- `검토 필요`: 요약 검증 실패 또는 본문 부족
- `원문만 보기`: 본문 파싱 실패로 요약이 불가능한 상태
- `비공개`: 사용자 신고 또는 검증 실패로 숨김 처리

## 구현 우선순위

1. RSS 기사 수집 및 중복 제거
2. 기사 본문 추출
3. 기사 요약 생성
4. 요약 검증 및 재시도
5. O/X 퀴즈 생성
6. 기사/퀴즈 저장
7. 홈 피드 API 연결
8. 상세 페이지 API 연결
9. 데일리 리포트 생성
10. 사용자 활동 기록 및 리포트 반영

## 프롬프트 설계 초안

### 요약 프롬프트

```text
아래 기사 본문을 3~5문장으로 사실 중심 요약하시오.
원문에 없는 정보, 추측, 평가, 과장 표현을 포함하지 마시오.
숫자, 인물명, 기관명, 시점은 원문과 다르게 바꾸지 마시오.
사용자가 모바일 화면에서 빠르게 이해할 수 있도록 간결한 문장으로 작성하시오.
추가로 이 기사를 이해하는 데 도움이 되는 배경 맥락을 2~3문장으로 작성하시오 (context 필드).
context는 원문에 근거하며 추측을 포함하지 않는다.
```

### 퀴즈 프롬프트

```text
아래 기사 요약을 바탕으로 O/X 퀴즈 3문항을 생성하시오.
각 문항은 요약에 명시된 사실만 근거로 해야 한다.
정답은 반드시 O 또는 X 중 하나여야 한다.
각 문항에는 1~2문장의 해설을 포함하시오.
JSON 형식으로만 응답하시오.
```

### 검증 프롬프트

```text
아래 원문과 AI 요약을 비교하시오.
요약에 원문에 없는 정보가 포함되었는지 확인하시오.
숫자, 기관명, 인물명, 시점이 원문과 다르게 바뀌었는지 확인하시오.
문제가 없으면 pass, 문제가 있으면 retry 또는 skip으로 판정하시오.
이유를 짧게 작성하시오.
```

## 주의할 점

- AI 요약은 원문을 대체하는 것이 아니라 원문을 빠르게 이해하기 위한 보조 정보다.
- 모든 상세 페이지에는 원문 링크가 있어야 한다.
- AI 요약임을 사용자에게 명확히 알려야 한다.
- 정치, 사회, 경제 기사에서는 주관적 판단 표현을 피해야 한다.
- 퀴즈는 사용자를 평가하기보다 이해를 확인하는 가벼운 경험이어야 한다.
- 본문 파싱 실패나 요약 실패는 정상적인 예외로 보고 UI 상태를 준비해야 한다.

## 현재 UI와의 연결

현재 UI에서 AI 결과가 들어갈 위치는 다음과 같다.

- 홈 카드: `title`, `source`, `publishedAt`, `summary`, `keywords`, `status`
- 상세 상단: `title`, `source`, `publishedAt`, `originalUrl`
- 상세 본문: `summary`, `importance`, `context`
- 상세 퀴즈: `quiz.items`
- 리포트: `dailyReport.briefing`, `dailyReport.flow`, `dailyReport.headline`, `dailyReport.headlineSourceCount`, `dailyReport.subArticles`, `dailyReport.keywords`

리포트 UI는 C+ 보강형(타임라인 메타포)으로 확정됐다. 상단부터 다음 순서로 구성된다.

1. **헤더** — 큰 날짜 (`reportDate`) + 업데이트 시각 (`reportUpdatedAt`) + 요일 라벨
2. **AI 브리핑 카드** — `briefing`: DailyReportGenerator가 생성하는 오늘 하루 한 줄 요약. 단독 카드로 강조
3. **타임라인 (가장 많이 다뤄진 순)** — 클러스터 크기 기준 정렬된 노드 리스트
   - **헤드라인 노드** (큰 노드, 색상 ring): 1위 클러스터의 최고 importance_score 기사. 본문 미리보기 + `headlineSourceCount`개 매체 dots 시각화
   - **서브 노드 1~2개** (작은 노드): 2~3위 클러스터의 헤드라인과 다른 카테고리 기사. 한 줄 제목 + `source_count`개 매체 텍스트
4. **오늘의 흐름** — `flow`: 카테고리별 한 줄 요약 (TrendSummarizer 출력). 카테고리 라벨에 카테고리 컬러 적용
5. **오늘의 키워드** — `keywords`: 빈도 차등 클라우드. `data-w` 속성(2~9)으로 사이즈/불투명도 단계 표시
6. **마침표** — 점선 디바이더 + 체크 아이콘 + 다음 업데이트 안내 한 줄

타임라인의 시간 표시는 `tl-time` 필드에 들어가지만, "타임라인" 메타포보다 "가장 많이 다뤄진 순" 정렬이 우선이다. 시간 데이터가 좁게 모이는 날에도 메타포가 깨지지 않도록 헤더는 "가장 많이 다뤄진 순"으로 명시한다.

현재는 정적 예시 데이터로 채워져 있으며, 다음 단계는 실제 API 응답 형태에 맞춰 동적 데이터로 교체하는 것이다. 상태 UI(요약 중, 검토 필요 등)도 홈 카드와 상세 페이지에 추가 필요하다.

## 홈 로딩 화면 — 실시간 진행률 연동

기존의 "관심 카테고리 확인 / 주요 뉴스 수집 / AI 요약 생성" 3단계 텍스트 표시는 백엔드 진행률과 무관한 연출이었다. 사용자에게 신뢰를 주려면 실제 LangGraph 노드 진행을 SSE 또는 WebSocket으로 흘려 프론트에서 카운터로 갱신해야 한다.

### UI 단계 매핑

UI는 두 단계만 노출한다. (카테고리 확인은 DB 조회로 즉시 끝나므로 표시하지 않는다.)

| UI 단계 | LangGraph 노드 | 카운터 단위 |
|---|---|---|
| 주요 뉴스 수집 | Collector + Deduplicator | `N / 12 매체` (RSS 피드 수) |
| AI 요약 생성 | ArticleExtractor + Summarizer + SummaryValidator | `N / 8 기사` (당일 처리 대상 수) |

`12 매체`, `8 기사`는 예시 값이며, 실제로는 백엔드가 첫 이벤트로 `total`을 알려준 뒤 `current`를 점진 갱신한다.

### 권장 SSE 이벤트 스키마

```
event: step  data: {"step": "collect", "current": 0, "total": 12}
event: step  data: {"step": "collect", "current": 7, "total": 12}
event: step  data: {"step": "collect", "current": 12, "total": 12}
event: step  data: {"step": "summarize", "current": 0, "total": 8}
event: step  data: {"step": "summarize", "current": 3, "total": 8}
event: step  data: {"step": "summarize", "current": 8, "total": 8}
event: done  data: {"articleIds": [...]}
```

### LangGraph 연동 방법

LangGraph는 `astream_events` API를 통해 노드 진입/종료 이벤트를 노출한다. 백엔드는 이를 구독하여 위 SSE 스키마로 변환한다.

```python
async def stream_pipeline(user_id: str):
    yield sse("step", {"step": "collect", "current": 0, "total": len(feeds)})
    collected = 0
    async for event in graph.astream_events({"userId": user_id}, version="v2"):
        kind = event["event"]
        node = event.get("name")

        if kind == "on_chain_end" and node == "Collector":
            collected += 1
            yield sse("step", {"step": "collect", "current": collected, "total": len(feeds)})

        if kind == "on_chain_start" and node == "Summarizer":
            # 첫 Summarizer 진입 시 collect 100% 마감 + summarize 시작 알림
            ...

        if kind == "on_chain_end" and node == "SummaryValidator":
            summarized += 1
            yield sse("step", {"step": "summarize", "current": summarized, "total": total_articles})

    yield sse("done", {"articleIds": result_ids})
```

### 프론트 연동

현재 `script.js`의 `startHomeLoading`은 ease-out cubic 애니메이션으로 카운터를 mock한다. 실제 연동 시에는 mock 부분을 `EventSource` 구독으로 갈아끼우면 된다. DOM 구조(`.loading-step[data-step] [data-cur] / [data-total] / .loading-step-bar span`)는 그대로 재사용한다.

```js
const es = new EventSource("/api/refresh-stream");
es.addEventListener("step", (e) => {
  const { step, current, total } = JSON.parse(e.data);
  const el = document.querySelector(`.loading-step[data-step="${step}"]`);
  if (!el) return;
  el.classList.add("is-active");
  el.querySelector("[data-cur]").textContent = current;
  el.querySelector("[data-total]").textContent = total;
  el.querySelector(".loading-step-bar span").style.width = `${(current / total) * 100}%`;
  if (current === total) {
    el.classList.remove("is-active");
    el.classList.add("is-done");
  }
});
es.addEventListener("done", () => {
  document.querySelector('[data-page="home"]').classList.replace("is-loading", "is-loaded");
  es.close();
});
```

### 실패 처리

- 특정 매체 수집 실패: `current`는 그대로 두고 `event: warn`으로 별도 알림 (UI는 진행률에 영향 없이 진행)
- 요약 검증 실패 (`review_required` 또는 `skip`): `summarize` 카운트에는 포함하되, 최종 `done` 응답에서 제외
- 전체 파이프라인 타임아웃: `event: error` → 프론트는 로딩 화면 숨기고 "잠시 후 다시 시도" 빈 상태로 전환

## AI 챗 에이전트 (RAG 기반)

### 개요

하단 네비게이션 중앙 버튼으로 진입하는 AI 어시스턴트 기능이다. 사용자가 자연어로 질문하면 수집된 기사와 리포트 데이터를 검색해 답변한다. 별도 데이터 수집 없이 기존 기사 처리 파이프라인의 임베딩 결과를 재활용한다.

### 처리 흐름

```text
사용자 입력
  → 쿼리 임베딩 (text-embedding-3-small)
  → pgvector 유사도 검색 (articles 테이블)
  → 검색 결과 + 대화 히스토리 → LLM
  → 응답 스트리밍 (SSE)
```

### LangGraph 노드 설계

```text
ChatInputNode
  → QueryEmbedder        # 사용자 입력 임베딩
  → ArticleRetriever     # pgvector 유사도 검색 (top-k 3~5건)
  → ContextBuilder       # 검색 기사 본문 + 대화 히스토리 조합
  → ResponseGenerator    # LLM 응답 생성
  → StreamResponder      # SSE로 프론트에 전달
```

### 라우팅 분기

사용자 입력 성격에 따라 검색 전략을 분기한다.

```text
날짜/카테고리 필터 감지
  → 날짜·카테고리 필터 + 벡터 검색 조합

특정 키워드 질문 ("오픈AI", "관세" 등)
  → 키워드 필터 우선 → 벡터 검색 보완

일반 질문 ("오늘 경제 흐름은?")
  → 순수 벡터 유사도 검색
```

### DB 요구사항

기사 처리 파이프라인에서 이미 저장되는 `embedding vector(1536)` 컬럼을 그대로 사용한다. 추가 스키마 변경 없음.

```sql
-- 유사도 검색 예시
SELECT id, title, summary, source, published_at, category
FROM articles
WHERE status = 'summarized'
ORDER BY embedding <=> $1  -- 쿼리 임베딩과 코사인 유사도
LIMIT 5;
```

### 대화 히스토리 관리

MVP에서는 세션 단위로 메모리 내 히스토리를 유지한다. DB 저장은 하지 않는다.

- 최근 5턴만 LLM 컨텍스트에 포함 (토큰 절약)
- 챗 초기화 버튼 클릭 시 히스토리 초기화

### 응답 형식

LLM에게 다음 형식으로 응답하도록 지시한다.

```text
1. 질문과 관련된 기사가 있으면 기사 카드(제목, 출처, 날짜)와 함께 답변
2. 기사 카드는 최대 3건
3. 요약 답변은 3문장 이내
4. 근거 기사가 없으면 "관련 기사를 찾지 못했어요" 안내
```

### 발표 시연 전략

- 발표 1~2일 전 파이프라인 1회 실행 → DB에 기사 20~30건 고정
- 발표 중 라이브 수집 없이 고정 DB 대상 벡터 검색만 수행
- 시연 질문 3~4개를 미리 확인해 해당 기사가 DB에 있는지 검증

### 프론트 연동

현재 `script.js`의 챗 플로우는 캔드 응답 방식으로 시안 동작 중이다. 실제 연동 시에는 `sendMessage` 함수에서 캔드 응답 대신 SSE 엔드포인트를 구독하도록 교체한다.

```js
// 현재 (mock)
const response = CHAT_RESPONSES[text] || DEFAULT_RESPONSE;

// 실제 연동 시
const es = new EventSource(`/api/chat-stream?q=${encodeURIComponent(text)}`);
es.addEventListener("token", (e) => appendToken(e.data));
es.addEventListener("done", () => es.close());
```
