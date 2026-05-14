// docs/features/api/auth.md (실제 백엔드 스펙)
// - POST /auth/login   { username, password } → { session_id, soma_user_id, user_no, user_name, role }
// - DELETE /auth/session  (header x-soma-session) → 204
// - GET /auth/whoami   (header x-soma-session) → { soma_user_id, user_no, user_name, role }
//
// 본 모듈은 브라우저(클라이언트 컴포넌트)에서 사용한다.
// 실제 백엔드 호출은 /api/auth/* Next.js Route Handler가 BFF로 프록시하며,
// session_id는 httpOnly 쿠키로 보관되므로 프론트 코드는 직접 접근하지 않는다.

import { apiFetch, ApiError } from "@/lib/api";

export type AuthUser = {
  somaUserId: string;
  userNo: string;
  userName: string;
  role: string;
};

export type LoginRequest = {
  username: string;
  password: string;
};

// 백엔드 원본 응답 — Route Handler 내부에서만 사용 (snake_case).
export type RawAuthUser = {
  soma_user_id: string;
  user_no: string;
  user_name: string;
  role: string;
};

export type RawLoginResponse = RawAuthUser & {
  session_id: string;
};

export function normalizeAuthUser(raw: RawAuthUser): AuthUser {
  return {
    somaUserId: raw.soma_user_id,
    userNo: raw.user_no,
    userName: raw.user_name,
    role: raw.role,
  };
}

export type WhoamiResponse = {
  authenticated: boolean;
  user: AuthUser | null;
};

// 클라이언트 → Next.js BFF 호출.
// session_id는 httpOnly 쿠키로 자동 동봉되므로 헤더를 직접 다루지 않는다.

export async function loginUser(
  body: LoginRequest,
  signal?: AbortSignal,
): Promise<AuthUser> {
  return apiFetch<AuthUser>("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    credentials: "same-origin",
    signal,
  });
}

export async function logoutUser(signal?: AbortSignal): Promise<void> {
  await apiFetch<void>("/api/auth/logout", {
    method: "POST",
    credentials: "same-origin",
    signal,
  });
}

export async function fetchWhoami(signal?: AbortSignal): Promise<WhoamiResponse> {
  try {
    const user = await apiFetch<AuthUser>("/api/auth/whoami", {
      method: "GET",
      credentials: "same-origin",
      signal,
    });
    return { authenticated: true, user };
  } catch (cause) {
    if (cause instanceof ApiError && cause.status === 401) {
      return { authenticated: false, user: null };
    }
    throw cause;
  }
}
