const SESSION_KEY = "brainrot-session-id";

export function getOrCreateSessionId(): string {
  if (typeof window === "undefined") {
    return ";";
  }

  const existing = window.sessionStorage.getItem(SESSION_KEY);
  if (existing) {
    return existing;
  }

  const fresh = window.crypto.randomUUID();
  window.sessionStorage.setItem(SESSION_KEY, fresh);
  return fresh;
}
export function resetSessionId(): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(SESSION_KEY);
}
