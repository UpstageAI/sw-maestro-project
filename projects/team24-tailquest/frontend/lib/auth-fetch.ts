import { clearSession, getToken } from "@/lib/auth";

/**
 * Drop-in fetch wrapper that:
 *  1. Injects `Authorization: Bearer <token>` if a token is present.
 *  2. On 401 response: clears the session and hard-redirects to /login.
 *     This is the single chokepoint for unauthenticated redirects.
 */
export async function authFetch(
  url: string,
  init?: RequestInit
): Promise<Response> {
  const token = getToken();

  const headers = new Headers(init?.headers);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const res = await fetch(url, { ...init, headers });

  if (res.status === 401) {
    clearSession();
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
  }

  return res;
}
