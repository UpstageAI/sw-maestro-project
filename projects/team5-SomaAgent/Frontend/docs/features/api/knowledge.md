### POST /api/v1/knowledge/ask Ask Knowledge

Parameters
Try it out
No parameters

Request body

application/json
Example Value
Schema
{
"query": "string",
"source_types": [
"NOTICE"
],
"official_only": false,
"room_name": "string",
"k": 5
}
Responses
Code Description Links
200
Successful Response

Media type

application/json
Controls Accept header.
Example Value
Schema
{
"answer": "string",
"sources": [
{
"chunk_id": "string",
"source_type": "NOTICE",
"source_id": "string",
"title": "string",
"text": "string",
"official": true,
"score": 0,
"created_at": "2026-05-10T05:48:13.790Z",
"source_url": "string",
"room_name": "string"
}
],
"llm_used": true,
"llm_error": "string"
}
No links
422
Validation Error

Media type

application/json
Example Value
Schema
{
"detail": [
{
"loc": [
"string",
0
],
"msg": "string",
"type": "string",
"input": "string",
"ctx": {}
}
]
}

---

## 프론트 구현 (Next.js)

> 단일 진실: [SomaAgent Swagger](http://insung-server.servemp3.com:8000/docs#/knowledge). 아래는 본 레포에 반영한 구현 요약이다.

### BFF

| 경로 | 역할 |
| --- | --- |
| `POST /api/v1/knowledge/ask` | `app/api/v1/knowledge/ask/route.ts` — 요청 본문 검증(`query` 필수·trim) 후 `SOMA_API_BASE_URL`로 동일 경로 프록시. 에러는 `lib/server/somaApi`의 `SomaApiError` → `{ code, message, details }`. |

브라우저는 **항상 same-origin** `/api/v1/knowledge/ask`만 호출한다.

### 클라이언트

| 파일 | 역할 |
| --- | --- |
| `lib/types/knowledge.ts` | `KnowledgeAskRequest`, `KnowledgeAskResponse`, `KnowledgeSource`, `KnowledgeSourceType` |
| `lib/knowledge.ts` | `askKnowledge(body, signal?)` → `apiFetch` |
| `lib/knowledgeChat.ts` | 채팅 스레드 `ThreadMessage` 타입(user / assistant·knowledge / assistant·error / agent·action_result) |
| `lib/knowledgeSourceToUi.ts` | `knowledgeSourcesToUiSources` — API 출처를 `SourceList`용 `Source[]`로 매핑(NOTICE→notice 등) |
| `app/chat/page.tsx` | 직전 스레드(`buildKnowledgeQueryWithContext`)를 묶어 `query`로 전송 후 `askKnowledge` 호출. `AbortController`로 인플라이트 요청 취소. |
| `lib/knowledgeContext.ts` | `buildKnowledgeQueryWithContext` — 이전 사용자·어시스턴트(knowledge) 턴을 텍스트 블록으로 합성(스펙의 `candidates_context` JSON 필드 대체). |
| `lib/knowledgeToMentoring.ts` | `source_type === MENTORING` 이고 `source_id`가 숫자인 출처만 `MentoringCard[]`로 변환. |
| `lib/mentoringApply.ts` | `applyMentoringViaApi` + Swagger 응답 정규화(`normalizeMentoringApplyResponse`). |
| `app/api/v1/mentoring/[mentoringId]/apply/route.ts` | 로그인 쿠키 → 백엔드 `POST /api/v1/mentoring/{id}/apply` 프록시. |
| `components/chat/ChatContainer.tsx` | 빈 스레드 안내 + 답변 대기 로딩 버블. |
| `components/chat/ChatInput.tsx` | 전송만; 요청 중 `disabled`. |
| `components/chat/ChatMessage.tsx` | 멘토링 카드 영역 + 접이식 `SourceList`. |
| `components/chat/MentoringCardList.tsx` | `applyMode="openapi_mentoring"` 시 위 BFF로 신청. |
| `components/chat/SourceList.tsx` | `<details>` 스타일 접기/펼치기(기본 접힘). |

### 제거·정리

- `lib/mockChat.ts`에서 시연용 `MOCK_MESSAGES` 및 구 `ChatMessage` 타입 제거. 사이드바용 `MOCK_HISTORY`만 유지.
- mock 기반 멘토링/공지/Webex UI 블록은 `/chat`에서 기본 경로로 쓰이지 않음. 멘토링은 **RAG `MENTORING` 출처 + 숫자 ID**일 때만 카드·신청 UI가 뜸 (`ChatMessage` 연동).

### 인증

OpenAPI상 `knowledge/ask`에 세션 헤더는 없음. 필요 시 Route Handler에서 쿠키·헤더를 백엔드로 전달하도록 확장하면 된다.

### `docs/spec/frontEndSpec.md` §3 과의 차이

| 스펙 항목 | 현재 구현 |
| --- | --- |
| `POST /chat` + `ChatMessage.ui[]` (`mentoring_cards`, `notice_list` …) | 배포 Swagger에 `/chat` 없음. RAG는 `knowledge/ask` 단일 엔드포인트. |
| `candidates_context` JSON 재전송 | 백엔드 스키마에 필드 없음 → **`buildKnowledgeQueryWithContext`로 이전 턴을 `query` 문자열 안에 포함**하는 방식으로 유사 동작. |
| 멘토링 신청 | `MENTORING` 출처 중 **`source_id`가 숫자**인 것만 카드화 후 `POST /api/v1/mentoring/{id}/apply` BFF + `soma_user_id`(로그인 사용자)로 신청. 공지/Webex 전용 UI 블록은 미구현. |
| 출처 UI | 길이 절약을 위해 **`SourceList`를 기본 접힘**으로 표시; 펼치면 칩 그리드 + 비공식 안내. |

전체 스펙 정합을 위해서는 백엔드에 `POST /api/v1/chat` 및 `candidates_context` 수용이 필요하다.
