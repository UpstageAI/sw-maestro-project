"use client";

const TOKEN_KEY = "tq:auth_token";
const USER_KEY = "tq:auth_user";
const BOOT_KEY = "tq:server_boot_id";

// sessionStorage keys that are scoped to the logged-in identity. Cleared on
// every setSession/clearSession so a logout-then-register-as-different-user
// flow doesn't carry the previous account's onboarding draft, chat turns, or
// material selection into the new session. Keep this list in sync with the
// constants in lib/onboarding-state.ts, lib/chat-state.ts, lib/materials-
// selection.ts, and the active-session key inside chat-shell.tsx.
const IDENTITY_SCOPED_KEYS = [
  "tq.onboarding",        // onboarding draft
  "tq:chat_turns",        // chat turns cache
  "tq:selected_materials",// materials selection
  "tq:active_session_id", // active /chat/[sid] route hint
];

function clearIdentityScopedState(): void {
  if (typeof window === "undefined") return;
  for (const k of IDENTITY_SCOPED_KEYS) {
    window.sessionStorage.removeItem(k);
  }
}

export interface AuthUser {
  id: string;
  email: string;
  displayName: string | null;
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function getUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function setSession(payload: { token: string; user: AuthUser }): void {
  if (typeof window === "undefined") return;
  // Identity boundary — wipe any state from a prior session in this tab.
  // This is what prevents a fresh signup from immediately landing in
  // /chat seeded with the previous account's onboarding draft.
  clearIdentityScopedState();
  window.localStorage.setItem(TOKEN_KEY, payload.token);
  window.localStorage.setItem(USER_KEY, JSON.stringify(payload.user));
}

export function clearSession(): void {
  if (typeof window === "undefined") return;
  clearIdentityScopedState();
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(USER_KEY);
}

/**
 * Compare the backend's boot_id with the one we cached. If they differ, the
 * server has restarted and all JWTs are invalid — wipe session and force re-login.
 *
 * No-op on SSR. Network failures are silently ignored.
 */
export async function syncWithServerBoot(): Promise<void> {
  if (typeof window === "undefined") return;
  try {
    const res = await fetch("/api/backend/health", { cache: "no-store" });
    if (!res.ok) return;
    const data = (await res.json()) as { boot_id?: unknown };
    const bootId = typeof data.boot_id === "string" ? data.boot_id : "";
    if (!bootId) return;
    const stored = window.localStorage.getItem(BOOT_KEY);
    if (stored && stored !== bootId) {
      clearSession();
    }
    window.localStorage.setItem(BOOT_KEY, bootId);
  } catch {
    // backend unreachable — leave state alone
  }
}

/**
 * @deprecated Use getUser()?.email ?? null. Kept for backward compat during
 * Workstream E migration. Will be removed once lib/api.ts is updated.
 */
export function getUserId(): string | null {
  return getUser()?.email ?? null;
}
