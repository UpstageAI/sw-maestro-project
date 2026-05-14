# SomaAgent API 설계

> 프론트엔드(Next.js) ↔ 백엔드(FastAPI) 간 계약 단일 진실 소스. 변경 시 양쪽이 본 문서를 함께 갱신합니다.

>

> **상태 트래킹은 아래 [API 트래커 DB](#tracker)에서 합니다.** FE/BE Status 컬럼을 직접 갱신해주세요.

>

> 참조: `docs/SPEC.md` (3차 리비전, 2026-05-05) · 부모: <page url="https://www.notion.so/3561fc74ab0680248396c13bf234ccde">SomaAgent Frontend</page>

---

## 0. 트래커 사용법

- **레이어**: API Endpoint(7) / Tool(8, BE 전용) / UI Block(5, FE 전용) / Action Flow(2)
- **상태값**: `미착수` / `설계중` / `구현중` / `리뷰` / `완료` / `블록` / `N/A`
- **우선순위**: P0(시연 필수) / P1(MVP 내) / P2(이후)
- **시연 시나리오**: SPEC §13 매핑 (#1~#5)

DB 뷰는 하단 **[그룹: Layer]** 가 기본. FE 담당자는 `FE Status ≠ 완료` 필터, BE 담당자는 `BE Status ∈ {구현중, 설계중}` 필터를 권장.

---

## 1. 인증 / 세션

### 1.1 `POST /api/v1/auth/login`

**요청**

```
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "<소마 ID>",
  "password": "<소마 PW>"
}
```

**200 응답**

```json
{
  "session_id": "8a4f...uuid",
  "soma_user_id": "trainee-1234",
  "email": "user@example.com",
  "role": "TRAINEE"
}
```

| HTTP | code                   | 설명                    |
| ---- | ---------------------- | ----------------------- |
| 401  | `INVALID_CREDENTIALS`  | 소마 홈페이지 인증 실패 |
| 503  | `UPSTREAM_UNAVAILABLE` | sidecar/소마 다운       |

**프론트 처리**: `session_id`는 httpOnly 쿠키 권장. `username`/`password`는 메모리에서 즉시 폐기.

### 1.2 `POST /api/v1/auth/logout`

```
POST /api/v1/auth/logout
X-Soma-Session: <session_id>
```

**204 No Content**. 백엔드는 sidecar `DELETE /sessions/{session_id}` 호출.

### 1.3 `GET /api/v1/auth/status`

페이지 새로고침 후 세션 유효성 + 외부 연동 상태 확인.

```
GET /api/v1/auth/status
X-Soma-Session: <session_id>
```

**200 응답**

```json
{
  "authenticated": true,
  "user": {
    "somaUserId": "trainee-1234",
    "email": "user@example.com",
    "role": "TRAINEE"
  },
  "integrations": {
    "opensoma": { "status": "connected" },
    "webex": { "status": "operator_managed" },
    "calendar": { "status": "mock" }
  }
}
```

**401**: 세션 만료. 응답 헤더 `X-Soma-Session-Expired: true` 동봉.

### 1.4 세션 만료 신호 (모든 엔드포인트 공통)

```
HTTP/1.1 401
X-Soma-Session-Expired: true
{ "code": "SOMA_AUTH_REQUIRED", "message": "세션이 만료되었습니다" }
```

---

## 2. 채팅

### 2.1 `POST /api/v1/chat`

**요청**

```
POST /api/v1/chat
X-Soma-Session: <session_id>
X-Session-Id:   <UUID, 프론트 발급 영속>
Content-Type:   application/json

{
  "message": "이번 주 백엔드 멘토링 찾아줘",
  "candidates_context": [ ... ]
}
```

**응답: `ChatMessage`**

```tsx
type ChatMessage = {
  answer: string;
  status: "success" | "partial" | "failed" | "needs_confirmation";
  sources: Source[];
  ui: ChatUIBlock[];
  actions?: ActionProposal[]; // 사용자 확인이 필요한 제안 — 실제 실행은 /actions/execute
  trace_id: string;
};
```

> ⚠️ **채팅은 신청/취소를 직접 실행하지 않습니다.** "이거 신청해줘" 같은 발화에는 `ActionProposal`만 반환합니다. 실제 실행은 §3 `/actions/execute`로.

### 2.2 공통 타입

```tsx
type Source = {
  id?: string;
  type:
    | "notice"
    | "notice_pdf"
    | "mentoring"
    | "application"
    | "webex_message"
    | "webex_summary"
    | "calendar"
    | "other";
  title: string;
  url?: string;
  createdAt?: string; // ISO 8601
  collectedAt?: string;
  official: boolean; // OpenSoma=true, Webex=false
  rawRef?: string;
};

type ChatUIBlock =
  | { type: "source_list"; sources: Source[] }
  | { type: "mentoring_cards"; items: MentoringCard[] }
  | { type: "notice_list"; items: NoticeCard[] }
  | { type: "webex_summary"; items: WebexSummaryItem[] }
  | { type: "action_result"; results: ActionResult[] };

type ActionType = "MENTORING_APPLY" | "MENTORING_CANCEL";

type ActionProposal = {
  actionType: ActionType;
  label: string; // 사용자 노출 버튼 라벨 (예: "백엔드 멘토링 신청")
  payload: ActionPayload; // /actions/execute에 그대로 재전송
  requiresConfirmation: boolean; // true면 프론트가 자체 확인 모달 표시
  expiresAt?: string; // ISO 8601, 제안 유효 시각
};

type ActionPayload =
  | { mentoringId: string } // MENTORING_APPLY
  | { mentoringId: string } // MENTORING_CANCEL — 백엔드가 매핑
  | { mentoringId: string; applySn: number; qustnrSn: number }; // MENTORING_CANCEL — 명시
```

> `MentoringCard` / `NoticeCard` / `WebexSummaryItem` 정확한 필드는 sidecar PoC 후 확정 (트래커 비고 참조).

### 2.3 에러 응답

공통 형식 `{ code, message, details? }`.

| HTTP | code                   | 의미                     |
| ---- | ---------------------- | ------------------------ |
| 401  | `SOMA_AUTH_REQUIRED`   | X-Soma-Session 누락/만료 |
| 403  | `SOMA_AUTH_REJECTED`   | OpenSoma 권한 거부       |
| 422  | `INVALID_REQUEST`      | Pydantic 검증 실패       |
| 429  | `RATE_LIMITED`         | Solar/Webex rate limit   |
| 503  | `UPSTREAM_UNAVAILABLE` | sidecar/외부 다운        |

---

## 3. 액션 실행 (신청/취소)

### 3.1 `POST /api/v1/actions/execute`

도메인 액션 전용 디스패처. 채팅의 `ActionProposal`을 그대로 페이로드로 사용하거나, 카드 UI에서 직접 호출 가능.

**요청**

```
POST /api/v1/actions/execute
X-Soma-Session: <session_id>
X-Session-Id:   <UUID>
Content-Type:   application/json

{
  "actionType": "MENTORING_APPLY",
  "payload": { "mentoringId": "M123" }
}
```

**200 응답: `ActionExecutionResponse`**

```tsx
type ActionExecutionResponse = {
  actionType: ActionType;
  status: "success" | "failed";
  message: string; // 사용자 노출 메시지 (한국어)
  data?: {
    application?: {
      // MENTORING_APPLY 성공
      applySn: number;
      qustnrSn: number;
      mentoringId: string;
      title: string;
      sessionStartedAt?: string;
    };
    calendarInvite?: {
      // MENTORING_APPLY 부수 결과
      status: "created" | "skipped" | "failed";
      eventId?: string; // mock에서는 UUID
      errorMessage?: string;
    };
  };
  error?: { code: string; message: string; recoverable: boolean };
  trace_id: string;
};
```

### 3.2 액션별 페이로드/응답 요약

| `actionType`       | 페이로드                                                    | 성공 응답 `data`                  |
| ------------------ | ----------------------------------------------------------- | --------------------------------- |
| `MENTORING_APPLY`  | `{ mentoringId }`                                           | `{ application, calendarInvite }` |
| `MENTORING_CANCEL` | `{ mentoringId }` 또는 `{ mentoringId, applySn, qustnrSn }` | `{ application: {…cancelled} }`   |

> `MENTORING_CANCEL` 페이로드에 `applySn`/`qustnrSn`이 없으면 백엔드가 사용자 `applications` 캐시에서 자동 매핑 (필요 시 즉시 history 재조회).

### 3.3 처리 절차 (백엔드)

1. `actionType` 디스패치 → 해당 tool 매핑
2. `opensoma.mentoring.get`으로 직전 상태 재검증 (닫힘/마감/이미신청 등)
3. `MENTORING_CANCEL` + payload에 매핑 정보 없으면 `applications` 캐시에서 매핑
4. 실제 tool 호출 (`opensoma.mentoring.apply` / `.cancel`)
5. `MENTORING_APPLY` 성공 시 `calendar.invite.create` (mock) 후속 호출 — 실패해도 신청 롤백 안 함
6. 신청/취소 직후 해당 사용자 `applications` 행 즉시 삭제

### 3.4 에러 응답

| HTTP | code                   | 의미                                    |
| ---- | ---------------------- | --------------------------------------- |
| 401  | `SOMA_AUTH_REQUIRED`   | 세션 만료                               |
| 409  | `ACTION_CONFLICT`      | 이미 신청/마감됨/정원 초과 등 상태 충돌 |
| 422  | `INVALID_ACTION_TYPE`  | 알 수 없는 `actionType`                 |
| 422  | `INVALID_REQUEST`      | 페이로드 검증 실패                      |
| 503  | `UPSTREAM_UNAVAILABLE` | sidecar/소마 다운                       |

### 3.5 프론트 호출 패턴

**(a) 채팅 follow-up**

```tsx
// 1턴: 사용자 "이거 신청해줘"
const resp = await POST("/api/v1/chat", { message, candidates_context });
// resp.actions = [{ actionType: "MENTORING_APPLY", label: "...", payload: {...}, requiresConfirmation: true }]

// 사용자 확인 모달 → 확인
const result = await POST("/api/v1/actions/execute", {
  actionType: resp.actions[0].actionType,
  payload: resp.actions[0].payload,
});
```

**(b) 카드 UI 직접 클릭**

```tsx
// 멘토링 카드의 "신청" 버튼 클릭 → 자체 확인 모달 → 확인
const result = await POST("/api/v1/actions/execute", {
  actionType: "MENTORING_APPLY",
  payload: { mentoringId: card.id },
});
```

두 경로 다 백엔드 처리는 동일.

---

## 4. 시스템 상태

### 4.1 `GET /api/v1/system/sync-info`

스케줄러 동기화 시각 표시용. 인증 불필요.

```
GET /api/v1/system/sync-info
```

**200 응답**

```json
{
  "jobs": {
    "notices_sync": {
      "lastRunAt": "2026-05-05T08:30:00Z",
      "lastSuccessAt": "2026-05-05T08:30:00Z",
      "lastError": null
    },
    "mentorings_sync": {
      "lastRunAt": "2026-05-05T08:30:00Z",
      "lastSuccessAt": "2026-05-05T08:30:00Z",
      "lastError": null
    },
    "webex_sync": {
      "lastRunAt": "2026-05-05T08:00:00Z",
      "lastSuccessAt": "2026-05-05T07:00:00Z",
      "lastError": "401 from Webex"
    }
  }
}
```

> `sync_state` 테이블(SPEC §3.1)을 그대로 직렬화.

---

## 5. 헬스체크

| Path           | 용도                     |
| -------------- | ------------------------ |
| `GET /healthz` | 프로세스 살아있음        |
| `GET /readyz`  | MySQL ping + Qdrant ping |

---

## 6. 트래커 {#tracker}

아래 데이터베이스에서 진행 상태를 갱신해주세요. 새로운 엔드포인트/툴 추가 시 행을 추가합니다.
