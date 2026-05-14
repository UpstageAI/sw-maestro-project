# Handoff: `/api/generate` 요청 body에 `session_id` 필드 추가

- 날짜: 2026-05-11
- 작성자: 박서연 (Frontend, 2번)
- 받는 사람: 이진중 (Backend & Agent, 3번), 황현석 (AI/RAG, 4번)
- 관련 Frontend PR: `feature/frontend-generate-session`

## 요약

대화형 명세서 수정 기능 도입의 두 번째 단계. 프론트엔드가 클라이언트 측 UUID v4를 생성해 보관(`PR #16 머지 완료`)하고 있고, 이제 그 ID를 `/api/generate` 요청 body에 함께 보냅니다. 백엔드는 이 ID를 키로 대화 컨텍스트와 명세서 버전을 저장해야 합니다.

## 변경 요청 (백엔드 작업 필요)

### POST `/api/generate` — request body에 `session_id` 필드 추가

**현재 body (`docs/API_CONTRACT.md` 기준):**

```json
{
  "idea": "방구로 가는 자동차",
  "tone": "serious",
  "use_search": true
}
```

**변경 후:**

```json
{
  "idea": "방구로 가는 자동차",
  "tone": "serious",
  "use_search": true,
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**필드 명세:**

| 이름 | 타입 | 필수 | 설명 |
|------|------|-----|------|
| `session_id` | string (UUID v4 형식) | yes | 프론트가 `sessionStorage`에 생성·보관하는 세션 식별자. 한 브라우저 탭당 1개. |

### 백엔드 측 기대 동작 (협의 필요)

1. `/api/generate` 호출이 들어오면 `session_id`를 키로 새 세션을 생성하거나 기존 세션을 갱신
2. 생성된 명세서(`document` 필드)를 해당 `session_id`에 연결해서 저장 (메모리 dict, sqlite, redis 등 무엇이든 OK — 데모 범위)
3. PR 5에서 추가될 신규 엔드포인트 `POST /api/sessions/{session_id}/messages`가 이 저장소를 참조해서 이전 명세서를 컨텍스트로 사용할 예정
4. 응답 스키마는 **기존 그대로 유지**. `session_id`를 응답에 echo back 할지 여부는 백엔드 판단.

### 에러 처리

- `session_id` 형식이 UUID v4가 아닐 때 → 기존 `INVALID_INPUT` 코드 재사용 또는 그냥 무시하고 새 ID로 처리 (백엔드 선호 방식 회신 부탁)
- `session_id` 누락 시 → 데모 안정성을 위해 백엔드가 임의 UUID 생성해서 진행해도 OK (frontend가 항상 보내지만, robustness 차원)

## 응답 스키마 변경

없음. 기존 `GenerateResponse` 그대로 유지.

## 환경 변수 변경

없음.

## Frontend 측 변경 사항

- `frontend/lib/api.ts` — `generatePatent()` 내부에서 `getOrCreateSessionId()`로 세션 ID 가져와 body에 자동 첨부
- `frontend/lib/session.ts` — 이전 PR(#16)에서 추가 완료

## 머지 순서

1. (지금) 본 handoff 문서 + frontend PR을 백엔드팀에 공유
2. **백엔드팀** — 위 명세대로 백엔드 변경 PR 생성·머지 (또는 "지금은 받기만 하고 무시" 모드로 OK 회신)
3. **Frontend** — 백엔드 OK 받은 후 본 frontend PR 머지

> 💡 백엔드가 `session_id`를 일단 받기만 하고 저장 로직은 PR 5 직전에 추가해도 됩니다. 그래도 본 PR은 머지해도 frontend 동작에 문제 없음 (fallback이 있어서).

## 질문

1. 세션 저장소를 무엇으로 할지 (메모리 dict / sqlite / redis)? 데모 규모면 메모리 dict로 충분할 듯
2. 세션 TTL이 필요한지? (한 발표 세션 동안만 살아있으면 OK)
3. PR 5의 신규 엔드포인트 명세는 별도 handoff로 보낼 예정 — 그때까지 본 PR을 머지 보류해도 되고, 일단 머지하고 PR 5 합의 따로 가도 됨

## 참고 자료

- 본 frontend PR: (PR 생성 후 URL 추가)
- 관련 머지 완료 PR: #16 (`feat(frontend): session id 생성/저장`)
- 현재 API 명세 truth: `docs/API_CONTRACT.md`
