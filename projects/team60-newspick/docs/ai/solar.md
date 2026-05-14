# Upstage Solar

NewPick 의 LLM·임베딩은 모두 **Upstage Solar** API 로 처리한다. 단일 벤더, 단일 API 키.

## 사용 모델

| 용도 | 모델 | 비고 |
|---|---|---|
| 요약 생성 (Summarizer) | `solar-pro2` | 기사 본문 → 3~5문장 요약 + 키워드 + importance + context + importance_score |
| 요약 검증 (SummaryValidator) | `solar-pro2` | 원문 vs 요약 사실성 비교, pass/retry/skip 판정 |
| 퀴즈 생성 (QuizGenerator) | `solar-pro2` | O/X 3문항 + 해설 |
| 카테고리 흐름·헤드라인 문장화 (TrendSummarizer, DailyReportGenerator) | `solar-pro2` | |
| AI 챗 응답 (ResponseGenerator) | `solar-pro2` | RAG 검색 결과 + 대화 히스토리 → 답변 |
| 임베딩 (저장) | `solar-embedding-1-large-passage` | 출력 차원 **4096**. 기사 요약 텍스트 벡터화 후 `articles.embedding` 저장 |
| 임베딩 (검색) | `solar-embedding-1-large-query` | 챗 사용자 입력 벡터화. passage 와 짝을 이뤄야 검색 정확도 보장 |

> 비용 최적화 차원에서 챗·검증을 `solar-mini` 로 낮추는 분기는 Phase B 이후 LangSmith 트레이싱 결과를 보고 결정한다 (현재는 일관성 우선 `solar-pro2` 통일).

## 연동 방식

`langchain-upstage` SDK 를 사용한다. LangGraph/LangChain 생태계와 자연 연동되며, LangSmith 트레이싱이 자동으로 포함된다.

```python
from langchain_upstage import ChatUpstage, UpstageEmbeddings

llm = ChatUpstage(
    model="solar-pro2",
    api_key=os.environ["UPSTAGE_API_KEY"],
)

embeddings_passage = UpstageEmbeddings(
    model="solar-embedding-1-large-passage",
    api_key=os.environ["UPSTAGE_API_KEY"],
)

embeddings_query = UpstageEmbeddings(
    model="solar-embedding-1-large-query",
    api_key=os.environ["UPSTAGE_API_KEY"],
)
```

## 환경 변수

| 키 | 값 |
|---|---|
| `UPSTAGE_API_KEY` | Upstage 콘솔에서 발급 |
| `LANGCHAIN_TRACING_V2` | `true` (LangSmith 활성) |
| `LANGCHAIN_API_KEY` | LangSmith API 키 |
| `LANGCHAIN_PROJECT` | `newspick-mvp` |

## 임베딩 차원 / DB 스키마

Solar 임베딩은 **4096차원** 이다. 기존 docs 에 적힌 `text-embedding-3-small`(1536) 과 다르며, DB 컬럼은 `embedding vector(4096)` 로 정의해야 한다. 자세한 스키마/인덱스 결정은 [data/pgvector.md](../data/pgvector.md) 참조.

## 비용·지연시간 추적

LangSmith 트레이싱으로 토큰 사용량·평균 지연·실패율 모니터. 자세한 활용은 [ai/langsmith.md](langsmith.md) 참조.

## 프롬프트

요약·검증·퀴즈 프롬프트 템플릿은 [ai/prompts.md](prompts.md) 에 정리되어 있다.

## 주의

- Solar API 는 OpenAI 호환 스키마지만, **embedding 모델명·차원이 다르다**. 코드/문서에서 OpenAI 흔적이 남지 않도록 검색 후 일괄 갱신해야 한다.
- `langchain-upstage` 는 비교적 신생 패키지이므로 버전 고정(`pip` lock 또는 `uv` lock)을 권장한다.
