# Handoff: 신규 엔드포인트 `POST /api/sessions/{session_id}/messages`

- 날짜: 2026-05-11
- 작성자: 박서연 (Frontend, 2번)
- 받는 사람: 이진중 (Backend & Agent, 3번), 황현석 (AI/RAG, 4번)
- 관련 Frontend PR: `feature/frontend-chat-ui` (PR 4·5 통합)
- 선행 합의: `docs/handoff/2026-05-11-session-id-on-generate.md`

## 요약

대화형 명세서 수정의 핵심 엔드포인트입니다. 사용자가 채팅창에 자연어로 수정 요청("청구항 1번을 더 황당하게 바꿔줘")을 보내면, 백엔드는 해당 `session_id`의 이전 명세서를 컨텍스트로 LLM에 보내 수정된 명세서 전체를 반환합니다.

## 변경 요청 (백엔드 작업 필요)

### POST `/api/sessions/{session_id}/messages` — 신규

**Request:**

```http
POST /api/sessions/550e8400-e29b-41d4-a716-446655440000/messages
Content-Type: application/json

{
  "message": "청구항 1번을 더 황당하게 바꿔줘"
}
```

**Request Path Parameters:**

| 이름 | 타입 | 설명 |
|------|------|------|
| `session_id` | string (UUID v4) | URL path. PR 3 handoff로 생성·저장된 세션 키 |

**Request Body Fields:**

| 이름 | 타입 | 필수 | 설명 |
|------|------|-----|------|
| `message` | string | yes | 사용자가 자연어로 입력한 수정 요청 |

**Success Response (200):**

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "assistant_message": "청구항 1번을 더 황당한 톤으로 다시 작성했습니다.",
  "document": {
    "title": "...",
    "technical_field": "...",
    "background": "...",
    "problem": "...",
    "configuration": "...",
    "claims": ["...", "...", "...", "..."],
    "summary": "..."
  },
  "warnings": [
    "본 결과물은 엔터테인먼트 목적이며 실제 특허 출원 자문이 아닙니다."
  ]
}
```

**Response Fields:**

| 이름 | 타입 | 설명 |
|------|------|------|
| `session_id` | string | echo back. 클라이언트가 보낸 것과 동일 |
| `assistant_message` | string | AI가 채팅창에 보여줄 짧은 메시지 (1~2문장) |
| `document` | object | 수정된 명세서 **전체**. 기존 `GenerateResponse.document`와 동일한 7개 섹션 스키마 |
| `warnings` | string[] | 기존 `GenerateResponse.warnings`와 동일 |

### 동작 흐름 (백엔드 측 기대)

1. URL의 `session_id`로 세션 컨텍스트 조회 (PR 3 handoff에서 저장한 세션)
2. 해당 세션의 **최신 명세서**를 컨텍스트로 LLM에 전달
3. 사용자의 `message`를 수정 요청으로 해석하여 명세서 부분 또는 전체를 갱신
4. 갱신된 명세서를 세션 저장소에 덮어쓰기 (다음 메시지에서 또 컨텍스트로 사용)
5. 응답 반환

### 에러 처리

| 상황 | 코드 | HTTP |
|------|------|------|
| `session_id` 형식 오류 또는 UUID 아님 | `INVALID_INPUT` | 400 |
| `session_id`에 해당 세션이 없음 | `SESSION_NOT_FOUND` | 404 |
| LLM 호출 실패 | `GENERATION_FAILED` | 500 |
| 위험 주제 메시지 | `UNSAFE_TOPIC` | 400 |

**Frontend 처리:**
- `SESSION_NOT_FOUND` → 사용자에게 "세션이 만료되었습니다. 새로 시작해주세요" 안내 + sessionStorage clear
- `GENERATION_FAILED` → 채팅창에 "응답을 받지 못했습니다. 다시 시도해주세요" 표시 (명세서는 갱신 안 함)
- 기타 에러 → 메시지를 채팅창에 그대로 표시

## 응답 스키마 변경 (`docs/API_CONTRACT.md`)

본 handoff가 합의되면 `docs/API_CONTRACT.md`에 위 엔드포인트 추가 필요. **본 frontend PR에서는 API_CONTRACT.md를 수정하지 않음** (다른 담당자 영역). 백엔드 측 변경 PR 또는 별도 docs PR에서 반영.

## 환경 변수 변경

없음.

## Frontend 측 변경 사항

- `frontend/lib/api.ts` — `sendRevisionMessage(message)` 함수 추가
- `frontend/components/RevisionChat.tsx` — dummy 응답 → 실제 API 호출
- `frontend/app/page.tsx` — RevisionChat에 `onDocumentUpdate` 콜백 전달, 응답으로 명세서 미리보기 갱신

## 머지 순서

1. (현재) handoff + frontend PR을 백엔드팀에 공유
2. **백엔드팀** — 위 엔드포인트 구현 (메모리 dict 또는 sqlite 기반 세션 저장소)
3. PR 3 (`feature/frontend-generate-session`) 백엔드 OK 후 머지
4. 본 PR(`feature/frontend-chat-ui`) base가 자동으로 main으로 변경됨 → 머지

## 질문

1. `session_id`에 명세서가 없는 상태(즉 `/api/generate` 한 번도 안 부르고 메시지부터 보냄)에서 `/messages`가 호출되면 `SESSION_NOT_FOUND`로 처리할지, 아니면 그냥 새 명세서 생성으로 fallback할지?
2. 메시지 history도 세션에 저장할지(추후 대화 컨텍스트 활용), 아니면 최신 명세서만 들고 갈지?
3. 응답 시간 — LLM 호출이 끼니까 수 초 걸릴 수 있음. 60초 타임아웃이면 충분할지?

## 참고 자료

- 선행 handoff: `docs/handoff/2026-05-11-session-id-on-generate.md`
- 관련 PR (Frontend): #17 (PR 3 — session_id 첨부), #(PR 만들면 추가)
- 현재 API 명세 truth: `docs/API_CONTRACT.md`
