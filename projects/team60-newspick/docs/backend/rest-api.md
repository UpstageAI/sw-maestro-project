# REST API 스펙

> 본 문서는 엔드포인트 **목록과 시그니처** 까지만 정의한다. 응답 필드 단위 상세 스키마는 첫 구현 후 OpenAPI 문서로 자동 생성하거나, 필요 시 본 문서에 표로 보강한다.

## 설계 원칙

- 인증 없음 — 모든 엔드포인트는 공개. ([backend/auth.md](auth.md))
- 응답 포맷: `application/json` 기본, SSE 엔드포인트는 `text/event-stream`.
- 시간대: 모든 timestamp 는 ISO-8601 + `+09:00` (KST).
- 에러 응답:
  ```json
  { "error": "ERROR_CODE", "message": "사용자에게 보일 안내 (선택)" }
  ```
- 필드 명명: camelCase (Article 스키마 그대로).

## 엔드포인트 목록

| 메서드 | 경로 | 설명 | 응답 |
|---|---|---|---|
| `GET` | `/api/feed` | 홈 피드 (오늘의 기사 목록) | `Article[]` (요약/키워드 포함, 본문 제외) |
| `GET` | `/api/articles/{id}` | 기사 상세 (요약 + 퀴즈 + context) | `Article` |
| `GET` | `/api/report/today` | 오늘의 데일리 리포트 | `DailyReport` |
| `GET` | `/api/report/{date}` | 특정 날짜 리포트 (`YYYY-MM-DD`) | `DailyReport` |
| `GET` | `/api/refresh-stream` | RSS 수집 + AI 요약 진행률 (SSE) | `text/event-stream` |
| `GET` | `/api/chat-stream?q={query}` | RAG 챗 응답 스트리밍 (SSE) | `text/event-stream` |

## 응답 스키마 베이스

스키마 정의는 [architecture/data-schema.md](../architecture/data-schema.md) 의 Article / Quiz / DailyReport 를 따른다.

### `GET /api/feed` 응답 예

```json
{
  "articles": [
    {
      "id": "article_001",
      "title": "오픈AI·앤트로픽, AI 에이전트 경쟁 본격화",
      "source": "ZDNet Korea",
      "category": "테크",
      "publishedAt": "2026-05-10T09:20:00+09:00",
      "summary": ["..."],
      "keywords": ["AI 에이전트", "오픈AI"],
      "status": "summarized"
    }
  ]
}
```

### `GET /api/articles/{id}` 응답 예

홈 피드 응답에 `rawText`(선택), `importance`, `context`, `quiz` 추가.

### `GET /api/report/today` 응답 예

```json
{
  "reportDate": "2026-05-10",
  "reportUpdatedAt": "2026-05-10T09:30:00+09:00",
  "briefing": "AI 자동화와 통상 압박, 인구 위기가 동시에 부상한 하루였습니다.",
  "headline": {
    "articleId": "article_001",
    "category": "테크",
    "title": "...",
    "previewText": "...",
    "headlineSourceCount": 4
  },
  "subArticles": [
    { "articleId": "article_002", "category": "경제", "title": "...", "sourceCount": 3 },
    { "articleId": "article_003", "category": "이슈", "title": "...", "sourceCount": 2 }
  ],
  "flow": [
    { "category": "테크", "text": "AI 에이전트 경쟁이 ..." }
  ],
  "keywords": [
    { "text": "AI 에이전트", "weight": 9 },
    { "text": "미국 관세", "weight": 7 }
  ]
}
```

> `weight` 는 키워드 클라우드의 `data-w` 값(2~9)에 1대1 매핑된다. 디자인 정의는 [design.md](../design.md) §4.7 참조.

### SSE 엔드포인트

이벤트 스키마는 [architecture/realtime-ui-states.md](../architecture/realtime-ui-states.md) 의 `step / done / warn / error` 그대로. 본 백엔드는 Python 의 SSE 를 받아 그대로 프록시한다 ([backend/sse.md](sse.md)).

## CORS

dev 환경에서 Next.js dev server (`http://localhost:3000`) 는 allowlist 에 포함. 프로덕션 도메인은 MVP 시연 단계 이후 결정.

## 페이지네이션

홈 피드는 하루 20~30건이라 페이지네이션 불요. 향후 필요해지면 cursor 기반(`?after=articleId`)으로.

## 버저닝

`/api/v1/...` 식 prefix 는 도입하지 않는다. 3주 MVP, 1회 시연 이후 변경 시 일괄 갱신.

## 주의점

- `/api/refresh-stream` 은 사용자 트리거(홈 진입)로만 호출. 자동 폴링 X.
- 챗 SSE 는 1요청 1스트림. 멀티 동시 호출 시 Spring `SseEmitter` 가 서로 다른 인스턴스로 작동.
- Python 서비스 호출 timeout 은 120s (LangGraph 파이프라인 1회 실행 기준). 환경변수 `AI_SERVICE_TIMEOUT_SECONDS`.

## 레퍼런스

- Spring REST docs: https://docs.spring.io/spring-framework/reference/web/webmvc.html
- 응답 스키마 출처: [architecture/data-schema.md](../architecture/data-schema.md)
