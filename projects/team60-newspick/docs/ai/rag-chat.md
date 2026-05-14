# AI 챗 에이전트 (RAG 기반)

## 개요

하단 네비게이션 중앙 버튼으로 진입하는 AI 어시스턴트 기능이다. 사용자가 자연어로 질문하면 수집된 기사와 리포트 데이터를 검색해 답변한다. 별도 데이터 수집 없이 기존 기사 처리 파이프라인의 임베딩 결과를 재활용한다.

## 처리 흐름

```text
사용자 입력
  → 쿼리 임베딩 (solar-embedding-1-large-query, 4096-dim)
  → pgvector 유사도 검색 (articles 테이블)
  → 검색 결과 + 대화 히스토리 → Solar LLM (solar-pro2)
  → 응답 스트리밍 (SSE)
```

## LangGraph 노드 설계

```text
ChatInputNode
  → QueryEmbedder        # 사용자 입력 임베딩
  → ArticleRetriever     # pgvector 유사도 검색 (top-k 3~5건)
  → ContextBuilder       # 검색 기사 본문 + 대화 히스토리 조합
  → ResponseGenerator    # LLM 응답 생성
  → StreamResponder      # SSE로 프론트에 전달
```

## 라우팅 분기

사용자 입력 성격에 따라 검색 전략을 분기한다.

```text
날짜/카테고리 필터 감지
  → 날짜·카테고리 필터 + 벡터 검색 조합

특정 키워드 질문 ("오픈AI", "관세" 등)
  → 키워드 필터 우선 → 벡터 검색 보완

일반 질문 ("오늘 경제 흐름은?")
  → 순수 벡터 유사도 검색
```

## DB 요구사항

기사 처리 파이프라인에서 이미 저장되는 `embedding vector(4096)` 컬럼을 그대로 사용한다. 추가 스키마 변경 없음.

```sql
-- 유사도 검색 예시
SELECT id, title, summary, source, published_at, category
FROM articles
WHERE status = 'summarized'
ORDER BY embedding <=> $1  -- 쿼리 임베딩과 코사인 유사도
LIMIT 5;
```

## 대화 히스토리 관리

MVP에서는 세션 단위로 메모리 내 히스토리를 유지한다. DB 저장은 하지 않는다.

- 최근 5턴만 LLM 컨텍스트에 포함 (토큰 절약)
- 챗 초기화 버튼 클릭 시 히스토리 초기화

## 응답 형식

LLM에게 다음 형식으로 응답하도록 지시한다.

```text
1. 질문과 관련된 기사가 있으면 기사 카드(제목, 출처, 날짜)와 함께 답변
2. 기사 카드는 최대 3건
3. 요약 답변은 3문장 이내
4. 근거 기사가 없으면 "관련 기사를 찾지 못했어요" 안내
```

## 발표 시연 전략

- 발표 1~2일 전 파이프라인 1회 실행 → DB에 기사 20~30건 고정
- 발표 중 라이브 수집 없이 고정 DB 대상 벡터 검색만 수행
- 시연 질문 3~4개를 미리 확인해 해당 기사가 DB에 있는지 검증

> 제품 관점의 시연 시나리오 준비는 [product/demo-strategy.md](../product/demo-strategy.md) 참조.

## 프론트 연동

현재 `script.js`의 챗 플로우는 캔드 응답 방식으로 시안 동작 중이다. 실제 연동 시에는 `sendMessage` 함수에서 캔드 응답 대신 SSE 엔드포인트를 구독하도록 교체한다.

```js
// 현재 (mock)
const response = CHAT_RESPONSES[text] || DEFAULT_RESPONSE;

// 실제 연동 시
const es = new EventSource(`/api/chat-stream?q=${encodeURIComponent(text)}`);
es.addEventListener("token", (e) => appendToken(e.data));
es.addEventListener("done", () => es.close());
```
