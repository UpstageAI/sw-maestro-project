# SomaAgent Frontend Spec

> 본 문서는 백엔드 단일 진실 소스(`docs/SPEC.md`, 3차 리비전 2026-05-05)를 토대로 한 **Next.js Chat UI 측 스펙**입니다. 백엔드 변경 시 본 문서도 함께 동기화합니다.

> → <page url="https://www.notion.so/3561fc74ab068136a916f3b2ad605934">API 설계</page> (엔드포인트·Tool·UI Block 단위로 FE/BE Status 트래킹)

---

## 1. 범위 / 책임 분리

### 1.1 프론트가 담당하는 것

- 사용자 ID/PW 입력 → 백엔드 `/auth/login` 호출 → `session_id` 핸들 보관
- 페이지 새로고침 후 `/auth/status`로 세션 검증
- 채팅 입력 / 메시지 히스토리 / 후보 컨텍스트 재전송
- `ChatMessage.ui` 블록 렌더링 (멘토링 카드, 공지 리스트, Webex 요약, 액션 결과)
- **액션 확인 모달 + `/actions/execute` 호출** (멘토링 신청/취소)
- 카드 UI에서 "신청"/"취소" 버튼 직접 클릭 처리
- 출처(Source) / 공식 여부(official) / 작성 시각 표시
- `/system/sync-info`로 동기화 시각 표시 (선택, P2)
- 세션 만료 감지 → 재로그인 유도

### 1.2 프론트가 절대 다루지 않는 것

- 소마 홈페이지 ID/PW (로그인 1회만 백엔드로 전달, 절대 저장 금지)
- OpenSoma `JSESSIONID` / `csrfToken` 쿠키 원본 (sidecar 인메모리에만 존재)
- Webex 토큰, Solar API Key
- 운영자 계정 자격증명

### 1.3 시스템 컨텍스트

```
Next.js Chat UI  ──HTTPS──►  FastAPI (soma-agent)  ──►  OpenSoma Sidecar / Webex / Solar / MySQL / Qdrant
   │
   └─ 보관: session_id (UUID), 대화 히스토리, 직전 후보 목록
```

프론트는 FastAPI 앱하고만 통신합니다. Sidecar / 외부 시스템과 직접 통신하지 않습니다.

---

## 2. 인증 흐름

### 2.1 로그인 (1회)

`POST /api/v1/auth/login` 으로 ID/PW 전송, `session_id` 핸들 발급. 상세는 [API 설계](https://www.notion.so/API-3561fc74ab068136a916f3b2ad605934?pvs=21) §1.1 참조.

### 2.2 세션 보관 정책

- `session_id`는 **httpOnly 쿠키**(권장) 또는 SecureStorage 사용
- localStorage 직접 저장 금지 (XSS 노출)
- 페이지 새로고침 시 유지, 탭 종료 시 폐기 가능 (재로그인 부담 작음)
- 사용자 ID/PW는 메모리에서도 즉시 폐기 (제출 후 state에서 제거)

### 2.3 인증 헤더

이후 모든 `/api/v1/*` 요청에 다음 헤더를 동봉합니다.

```
X-Soma-Session: <session_id>
X-Session-Id:   <대화 세션 UUID, 프론트가 발급해 유지>
```

> `X-Soma-Session`은 OpenSoma 인증 핸들, `X-Session-Id`는 Agent 메모리 키입니다. 둘은 별개입니다.

### 2.4 세션 만료 처리

응답 헤더 `X-Soma-Session-Expired: true` + `code: SOMA_AUTH_REQUIRED` 감지 시 만료 처리.

**프론트 동작**

1. 진행 중인 모든 요청 취소
2. 보관 중인 `session_id` 폐기
3. 마지막 입력 메시지를 임시 보관(재시도용)
4. 로그인 모달 표시 → 성공 시 보관해둔 메시지로 자동 재전송

### 2.5 로그아웃 / 상태 확인

- `POST /api/v1/auth/logout` (헤더 `X-Soma-Session`) → `204 No Content` 후 클라이언트 상태 폐기.
- `GET /api/v1/auth/status`: 페이지 진입/새로고침 시 세션 유효성 + 외부 연동(opensoma/webex/calendar) 상태 확인. 만료 시 401.

---

## 3. 채팅 / 응답 계약

API 엔드포인트, `ChatMessage` / `Source` / `ChatUIBlock` / `ActionProposal` 타입 정의, 에러 응답, `candidates_context` 재전송 규칙, 확인 플로우는 모두 하위 페이지로 분리되었습니다.

→ **<page url="https://www.notion.so/3561fc74ab068136a916f3b2ad605934">API 설계</page>** (엔드포인트 5 / Tool 8 / UI Block 5 / Action Flow 2 — FE·BE Status 트래킹)

본 페이지는 프론트 화면 측 **렌더링 가이드**만 다룹니다.

### 3.1 컴포넌트 매핑

| `ui[].type`       | 컴포넌트                 | 비고                       |
| ----------------- | ------------------------ | -------------------------- |
| `source_list`     | `<SourceChips />`        | 답변 하단 칩 그리드        |
| `mentoring_cards` | `<MentoringCardList />`  | 카드형, 신청/취소 버튼     |
| `notice_list`     | `<NoticeList />`         | 리스트형, 제목·작성자·날짜 |
| `webex_summary`   | `<WebexSummary />`       | 비공식 배너 + 룸별 그룹핑  |
| `action_result`   | `<ActionResultBanner />` | 성공/실패 배너             |

`ui[]`는 순서대로 렌더링. 모르는 `type`은 무시(향후 추가 호환).

### 3.2 출처 렌더 규칙

- `official=true` → 파란 "공식" 배지
- `official=false` → 회색 "참고" 배지 + "비공식 출처" 안내 툴팁
- `url` 있으면 클릭 시 새 탭, 없으면 `rawRef` 텍스트 노출
- `createdAt` 표시는 상대 시간(`3일 전`) + 호버 시 절대 시간

### 3.3 액션 실행 흐름 (신청/취소)

> ⚠️ **3차 리비전 변경**: 채팅의 `needs_confirmation` 2턴 플로우 폐기. 모든 신청/취소는 `/actions/execute` 직통.

**(a) 채팅 follow-up 경로**

1. 사용자: "이거 신청해줘" → `POST /chat`
2. 응답 `actions[]`에 `ActionProposal { actionType, label, payload, requiresConfirmation }` 도착
3. 프론트: 답변 하단에 액션 버튼 노출
4. 사용자 클릭 → 자체 확인 모달 (`label` 재확인)
5. 확인 → `POST /actions/execute` 호출 (`{ actionType, payload }` 그대로)
6. 응답 `action_result` 블록으로 카드/배너 갱신

**(b) 카드 직접 클릭 경로**

1. 멘토링 카드의 "신청" 버튼 클릭
2. 프론트 자체 확인 모달
3. 확인 → `POST /actions/execute` `{ actionType: "MENTORING_APPLY", payload: { mentoringId } }`
4. 응답으로 카드 상태 갱신 (신청완료 표시)

**규칙**

- `requiresConfirmation: false`라도 신청/취소는 반드시 모달 거침 (안전장치)
- `/actions/execute`는 **자동 재시도 금지** (idempotent 보장 안 됨)
- 응답 `data.calendarInvite.status === "failed"`면 "신청은 완료됐지만 캘린더 등록 실패" 안내
- HTTP 409 `ACTION_CONFLICT`는 "이미 신청됨/마감됨" 등 — 모달로 표시

### 3.4 candidates_context 재전송

직전 응답의 후보(특히 멘토링 카드, 공지 리스트, ActionProposal)를 다음 턴에 그대로 동봉. 백엔드 router의 follow-up 해석용.

```tsx
// 다음 턴 전송 시
{
  message: userInput,
  candidates_context: previousChatMessage.ui.flatMap(b => {
    if (b.type === "mentoring_cards") return b.items;
    if (b.type === "notice_list") return b.items;
    return [];
  }).concat(previousChatMessage.actions ?? [])
}
```

---

## 4. 화면 구조

### 4.1 라우트

| 경로                       | 화면           | 인증 |
| -------------------------- | -------------- | ---- |
| `/login`                   | 로그인 폼      | 불요 |
| `/chat`                    | 대화 화면      | 필요 |
| `/chat/[sessionId]` (선택) | 과거 세션 복구 | 필요 |

### 4.2 `/chat` 레이아웃

```
┌────────────────────────────────────────────┐
│  Header: 사용자명 / 로그아웃 / trace toggle │
├────────────────────────────────────────────┤
│                                            │
│   [사용자 메시지]                          │
│                                            │
│   [에이전트 답변 — answer 텍스트]          │
│   [UI Block 1 — mentoring_cards]           │
│   [UI Block 2 — source_list]               │
│   [Action 버튼: "신청"]                    │
│                                            │
│   ...                                      │
│                                            │
├────────────────────────────────────────────┤
│  입력창 + 전송                             │
└────────────────────────────────────────────┘
```

### 4.3 클라이언트 상태

```tsx
type ChatState = {
  sessionId: string; // X-Session-Id (프론트 발급, 영속)
  somaSessionId: string | null; // X-Soma-Session (로그인 시 발급)
  user: { somaUserId: string; email?: string; role: string } | null;
  history: ChatTurn[];
  pendingAction: ActionProposal | null;
  inflight: AbortController | null;
};

type ChatTurn = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  ui?: ChatUIBlock[];
  sources?: Source[];
  actions?: ActionProposal[];
  status?: ChatMessage["status"];
  traceId?: string;
  createdAt: string;
};
```

세션 메모리는 백엔드도 최근 10턴을 유지하므로(SPEC §5.5), 프론트는 표시용으로 더 길게 가져도 됩니다. 단 `candidates_context`는 직전 1턴만 보내면 충분합니다.

---

## 5. 시연 시나리오 매핑 (SPEC §13)

| #   | 사용자 발화                      | 응답 status             | 주요 ui 블록                                |
| --- | -------------------------------- | ----------------------- | ------------------------------------------- |
| 1   | "이번 주 주요 공지 요약해줘"     | `success`               | `notice_list`, `source_list`                |
| 2   | "백엔드 멘토링 찾아줘"           | `success`               | `mentoring_cards`, `source_list`            |
| 3   | "내 접수 내역 보여줘"            | `success`               | `notice_list` 형태(접수 카드) 또는 마크다운 |
| 4-1 | "이거 신청해줘"                  | `success` • `actions[]` | `mentoring_cards` • 액션 버튼               |
| 4-2 | (확인 클릭) → `/actions/execute` | `success`               | `action_result` (신청 완료 + mock 캘린더)   |
| 5   | "Webex에서 X 얘기 정리해줘"      | `success`               | `webex_summary` (비공식 배너 강제)          |

---

## 6. UX / 비기능 요구사항

### 6.1 성능

- 첫 응답까지 P50 < 4s, P95 < 10s 목표 (백엔드 LLM 호출 포함)
- 입력창 디바운스 없음 (전송은 명시적 클릭/Enter)
- 인플라이트 요청 1개만 허용, 신규 전송 시 이전 요청 abort

### 6.2 접근성

- 모든 액션 버튼 `aria-label` 필수
- 출처 칩 키보드 네비게이션 (Tab)
- 로딩 상태 `aria-busy="true"`

### 6.3 i18n

- 1차: 한국어 단일
- 백엔드 `answer`는 LLM 생성 한국어 그대로 표시 (변환 금지)

### 6.4 표시 규칙 (SPEC 8.5와 정합)

- 사용자 메시지 본문은 클라이언트 분석 도구(Sentry, GA)에 **전송 금지**
- `trace_id`는 디버그 모드에서만 노출 (Cmd+Shift+T 토글)
- 이메일 / `soma_user_id` 마스킹: `user.****1234@***.com`

### 6.5 재시도

- 네트워크 에러 / 5xx: 자동 1회 재시도(2초 후), 실패 시 사용자에게 "재시도" 버튼
- 4xx: 자동 재시도 금지

---

## 7. 미해결 / 백엔드와 확정 필요

세부 미해결 항목은 [API 설계](https://www.notion.so/API-3561fc74ab068136a916f3b2ad605934?pvs=21) 페이지 트래커 DB의 `비고` 컬럼에서 추적합니다.

| #   | 항목                                                                       | 영향               |
| --- | -------------------------------------------------------------------------- | ------------------ |
| F-1 | `MentoringCard` / `NoticeCard` / `WebexSummaryItem` 정확한 필드 스키마     | 컴포넌트 props     |
| F-2 | `ApplicationHistory` 응답 형태 (전용 UI 블록 신설 vs `notice_list` 재사용) | UI 블록 추가 여부  |
| F-3 | 캘린더 mock 결과를 `action_result`에 어떻게 담을지                         | 배너 카피          |
| F-4 | `candidates_context` 최대 크기 제한                                        | 직전 N턴 동봉 정책 |
| F-5 | 출처 클릭 시 OpenSoma 페이지로의 직접 링크 가능 여부 (인증 필요)           | UX 분기            |
| F-6 | 세션 만료 시 자동 재시도 정책 (사용자 메시지/액션 보관 기간)               | UX 안전성          |
| F-7 | `MENTORING_CANCEL` 시 `applySn`/`qustnrSn` 매핑 실패 케이스 처리           | 에러 카피          |
| F-8 | sync 배지 폴링 주기 / 타임존 표시                                          | P2                 |
