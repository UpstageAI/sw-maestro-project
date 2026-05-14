# 데이터 구조 초안

## Article

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

> 위 스키마에 더해 EmbeddingGenerator 노드가 `embedding vector(4096)` 컬럼(Upstage Solar 임베딩)과 `importance_score smallint` 컬럼을 추가한다. 자세한 DB 컬럼·인덱스는 [architecture/pipeline-design.md](pipeline-design.md) 의 EmbeddingGenerator 섹션 및 [data/pgvector.md](../data/pgvector.md) 참조.

## Quiz

```json
{
  "articleId": "article_001",
  "items": [
    {
      "question": "O/X 문항",
      "answer": true,
      "explanation": "해설"
    }
  ]
}
```

## UserActivity

```json
{
  "userId": "session_uuid",
  "articleId": "article_001",
  "readAt": "2026-05-10T09:40:00+09:00",
  "quizScore": 3,
  "quizTotal": 3
}
```

> **MVP 메모**: Phase B 결정으로 인증을 완전 생략한다. UserActivity 기록·조회는 MVP 범위 밖이며, 위 스키마는 향후 확장용 참고 정의로만 둔다. 데일리 리포트의 "사용자가 읽은 기사" / "퀴즈 정답률" 같은 통계는 MVP 단계에서 생성하지 않는다 — 발표 시연은 기사 요약·퀴즈·리포트 자체가 핵심이며 사용자 활동 데이터는 데모 효과가 적다.
