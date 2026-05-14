# Auth API 연동

> SomaAgent FastAPI 백엔드의 인증 엔드포인트와 Next.js 프론트의 연동 방식을 정리한 문서.
> 백엔드 단일 진실 소스: `docs/spec/API.md` §1, 프론트 가이드: `docs/spec/frontEndSpec.md` §2.
>
> **백엔드 베이스 URL:** `http://insung-server.servemp3.com:8000` (`.env.local`의 `SOMA_API_BASE_URL`로 주입, 서버 사이드 전용)

---

## 1. 백엔드 실제 스펙

> Swagger UI: `http://insung-server.servemp3.com:8000/docs#/auth`
> 주의: `docs/spec/API.md`는 `/api/v1/auth/*`로 적혀 있지만 **실제 백엔드는 prefix 없이 `/auth/*`** 다. 본 문서가 실제 백엔드를 따른다.

### 1.1 `POST /auth/login`

**요청**

```http
POST /auth/login
Content-Type: application/json

{
  "username": "<SOMA 이메일>",
  "password": "<SOMA 비밀번호>"
}
```

**200 응답**

```json
{
  "session_id": "string",
  "soma_user_id": "string",
  "user_no": "string",
  "user_name": "string",
  "role": "string"
}
```

**에러 응답** (실측 기준)

| HTTP | code | 의미 | 비고 |
| --- | --- | --- | --- |
| 422 | (FastAPI 422) | 요청 본문 검증 실패 | `{ detail: [{ loc, msg, type, ... }] }` 형태 |
| 503 | `UPSTREAM_UNAVAILABLE` | OpenSoma sidecar/소마 홈페이지 다운 또는 잘못된 자격증명 | `{"code":"UPSTREAM_UNAVAILABLE","message":"OpenSoma is temporarily unavailable"}` |

> ⚠️ **실측 주의:** 잘못된 ID/PW를 보내도 백엔드가 401이 아니라 **503 `UPSTREAM_UNAVAILABLE`** 을 응답한다 (sidecar가 SOMA 홈페이지 인증을 시도하다 실패). 프론트는 503을 받으면 자격증명 오류 가능성을 함께 안내한다 (§3.2 참조).

### 1.2 `DELETE /auth/session`

**요청**

```http
DELETE /auth/session
x-soma-session: <session_id>
```

**204 No Content** — 백엔드는 sidecar 세션도 함께 폐기.

| HTTP | 비고 |
| --- | --- |
| 204 | 정상 |
| 401 | 이미 만료된 세션 — 프론트는 무시하고 정상 로그아웃 처리 |
| 422 | 헤더 누락 등 검증 실패 |

### 1.3 `GET /auth/whoami`

**요청**

```http
GET /auth/whoami
x-soma-session: <session_id>
```

**200 응답**

```json
{
  "soma_user_id": "string",
  "user_no": "string",
  "user_name": "string",
  "role": "string"
}
```

| HTTP | 비고 |
| --- | --- |
| 401 | 세션 만료/없음 — 프론트는 쿠키 폐기 후 `/login`으로 |
| 422 | 헤더 누락 등 검증 실패 |

---

## 2. 프론트 아키텍처

### 2.1 BFF (Backend-For-Frontend) 패턴

브라우저는 **Next.js Route Handler** (`/api/auth/*`) 만 호출하고, 실제 백엔드 호출은 서버 사이드에서 수행한다. 이렇게 한 이유:

- `frontEndSpec §1.2/2.2` "**localStorage 직접 저장 금지 / httpOnly 쿠키 권장**" 준수 — `session_id`는 `httpOnly` 쿠키로만 보관되며 브라우저 JS에서 읽을 수 없다.
- 백엔드 베이스 URL을 클라이언트 번들에 노출하지 않는다.
- CORS 우회 (브라우저가 외부 origin을 직접 부르지 않음).
- HTTPS 배포 시 mixed-content 차단 회피.

```
브라우저 ─────► /api/auth/* (Next.js Route Handler) ─────► FastAPI /auth/*
              (same-origin, 자동 쿠키)                  (Server-side fetch + x-soma-session)
```

### 2.2 폴더/파일 구성

| 경로 | 역할 |
| --- | --- |
| `.env.local` | `SOMA_API_BASE_URL` (서버 전용) · `SOMA_SESSION_COOKIE_NAME` |
| `lib/server/somaApi.ts` | 서버 전용 백엔드 fetch 래퍼 (`somaFetch`, `SomaApiError`, 15s 타임아웃, FastAPI 422 파싱) — `import "server-only"` |
| `lib/auth.ts` | 타입 정의(`AuthUser`, `LoginRequest`, `RawAuthUser`, `RawLoginResponse`) + 클라이언트용 함수(`loginUser`, `logoutUser`, `fetchWhoami`) + snake_case → camelCase 정규화(`normalizeAuthUser`) |
| `lib/contexts/AuthContext.tsx` | `<AuthProvider>` + `useAuth()` 훅 (status, user, login, logout, refresh) |
| `app/api/auth/_helpers.ts` | 쿠키 옵션, 표준 에러 응답 헬퍼 |
| `app/api/auth/login/route.ts` | `POST` — 백엔드 호출 후 `session_id`를 httpOnly 쿠키 set, 사용자 정보(camelCase)만 응답 |
| `app/api/auth/logout/route.ts` | `POST` — 백엔드 `DELETE /auth/session` 호출 + 쿠키 삭제 (백엔드 실패해도 쿠키는 폐기) |
| `app/api/auth/whoami/route.ts` | `GET` — 쿠키에서 세션 추출 → 백엔드 호출, 401 시 쿠키 자동 폐기 |
| `app/login/page.tsx` | 로그인 폼 (SOMA 이메일/비밀번호) |
| `app/chat/page.tsx` | 인증 가드 — `unauthenticated` 시 `/login` 자동 이동 |

### 2.3 쿠키 정책

```ts
{
  name: "soma_session",        // SOMA_SESSION_COOKIE_NAME으로 오버라이드 가능
  httpOnly: true,              // JS 접근 차단
  sameSite: "lax",             // CSRF 완화
  path: "/",
  secure: process.env.NODE_ENV === "production",  // dev http에서는 자동 비활성
  maxAge: 60 * 60 * 24,        // 24h, 백엔드 정책 미상으로 보수적 설정
}
```

### 2.4 데이터 변환 (snake_case → camelCase)

백엔드는 `soma_user_id`, `user_no`, `user_name` 같은 snake_case 필드를 보낸다. Route Handler가 `normalizeAuthUser`로 camelCase로 변환한 뒤 클라이언트에 전달한다.

```ts
// lib/auth.ts
export type AuthUser = {
  somaUserId: string;
  userNo: string;
  userName: string;
  role: string;
};
```

---

## 3. 흐름

### 3.1 정상 흐름

```
[/login 페이지]
  사용자: 이메일/비밀번호 입력
       │
       ▼
useAuth().login({ username: email, password })
       │
       ▼
POST /api/auth/login (same-origin, JSON body)
       │
       ▼ (Route Handler)
somaFetch("/auth/login", { json: {...} }) → FastAPI /auth/login
       │
       ▼
응답에서 session_id 추출 → httpOnly 쿠키로 set
응답 본문은 사용자 정보만(camelCase) 클라이언트에 전달
       │
       ▼
AuthContext.status = "authenticated", user = AuthUser
       │
       ▼
router.replace("/chat") + setPassword("")  ← 비밀번호 메모리 폐기
```

### 3.2 잘못된 자격증명 처리

백엔드 동작:
- 잘못된 ID/PW → `503 UPSTREAM_UNAVAILABLE`
- (현재 백엔드는 401을 반환하지 않는다 — sidecar가 SOMA 인증을 시도하다 실패)

프론트 처리 (`AuthContext.extractMessage`):

```ts
if (status === 401) → "이메일 또는 비밀번호가 올바르지 않습니다."
if (status === 503 && context === "login")
  → "로그인에 실패했습니다. 이메일·비밀번호가 정확한지 확인하거나 잠시 후 다시 시도해 주세요."
if (status === 503 && context !== "login")
  → "백엔드 서비스가 잠시 응답하지 않습니다. 잠시 후 다시 시도해 주세요."
```

향후 백엔드가 자격증명 오류와 sidecar 다운을 분리해서 (예: `INVALID_CREDENTIALS` code) 응답하면 더 정확한 메시지로 분기 가능.

### 3.3 새로고침/세션 유지

```
[페이지 진입]
       │
       ▼
<AuthProvider> 마운트
       │
       ▼
useEffect → GET /api/auth/whoami (쿠키 자동 동봉)
       │
       ▼
200 → status="authenticated"
401 → status="unauthenticated" (chat 페이지였다면 /login으로 자동 이동)
```

### 3.4 로그아웃

```
useAuth().logout()
       │
       ▼
POST /api/auth/logout (쿠키 자동 동봉)
       │
       ▼ (Route Handler)
쿠키에서 session 추출 → DELETE /auth/session 호출 → 쿠키 삭제
       │
       ▼
AuthContext.status = "unauthenticated", user = null
       │
       ▼
router.replace("/login")
```

---

## 4. 에러 응답 정규화

`SomaApiError`(서버) → 표준 본문(`{ code, message, details }`) → `ApiError`(클라이언트)로 통일.

| 위치 | 클래스 | 형태 |
| --- | --- | --- |
| 서버 측 fetch 실패 | `SomaApiError` (`lib/server/somaApi.ts`) | `{ status, code, message, details }` |
| Route Handler 응답 | `errorResponse(error)` | HTTP `status` + `{ code, message, details }` |
| 클라이언트 측 파싱 | `ApiError` (`lib/api.ts`) | 그대로 throw |
| AuthContext 사용자 노출 메시지 | `extractMessage(cause, { context })` | 한국어 문자열 |

FastAPI 표준 422 응답(`{ detail: [...] }`)도 `somaFetch`가 `INVALID_REQUEST` code로 정규화한다.

---

## 5. UX 결정 사항

| 항목 | 결정 |
| --- | --- |
| 로그인 입력 | SOMA 이메일 + 비밀번호 (소셜 로그인/회원가입 없음) |
| 비밀번호 폐기 | 로그인 성공 직후 `setPassword("")` |
| 인증 가드 | `/chat`은 `useAuth().status === "authenticated"`일 때만 렌더, 아니면 `/login`으로 `replace` |
| 로그인 후 진입 | `router.replace("/chat")` (history에 `/login` 남기지 않음) |
| 세션 만료 감지 | `whoami` 401 또는 임의 요청 401 시 쿠키 폐기 + `/login`로 |
| 로그아웃 버튼 위치 | `ChatHeader` 우측 (`LogOut` 아이콘) |
| 사용자 표시 | `ChatHeader`(이름 + 이메일/ID), `Sidebar`(이름 + role) |

---

## 6. 미해결 / 백엔드와 확정 필요

| # | 항목 | 영향 |
| --- | --- | --- |
| A-1 | 잘못된 자격증명 응답을 401 `INVALID_CREDENTIALS`로 분리할지 | 사용자 안내 정확도 |
| A-2 | `role` 필드의 가능한 값 enum (`TRAINEE` / `OPERATOR` / `MENTOR` …) | Sidebar/권한 UI 분기 |
| A-3 | 세션 TTL — 백엔드가 만료 정책을 명시하면 쿠키 `maxAge` 동기화 | 자동 로그아웃 타이밍 |
| A-4 | `frontEndSpec §1.4`의 `X-Soma-Session-Expired: true` 헤더 실제 백엔드 지원 여부 | 만료 감지 신호 다양화 |
| A-5 | `/auth/status`(통합 상태 확인) 엔드포인트 추가 여부 (`API.md §1.3` 참조) | 외부 연동(Webex/Calendar) 상태 표시 |
