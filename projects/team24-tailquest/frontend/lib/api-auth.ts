import { type AuthUser, clearSession, setSession } from "@/lib/auth";
import { authFetch } from "@/lib/auth-fetch";

const BASE = "/api/backend/auth";

/** FastAPI's `detail` is normally a string but for 422 validation errors it's
 *  an array of `{type, loc, msg, ...}` objects. Coerce both to a readable
 *  Korean message — without this the UI showed "[object Object]". */
async function extractError(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: unknown };
    const d = body.detail;
    if (typeof d === "string" && d.length > 0) return d;
    if (Array.isArray(d) && d.length > 0) {
      // Pydantic v2 validation error shape
      const messages = d.map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object") {
          const o = item as { msg?: unknown; loc?: unknown };
          const field =
            Array.isArray(o.loc) && o.loc.length > 1
              ? `${String(o.loc[o.loc.length - 1])}: `
              : "";
          return `${field}${typeof o.msg === "string" ? o.msg : JSON.stringify(item)}`;
        }
        return JSON.stringify(item);
      });
      return messages.join(" / ");
    }
    return `HTTP ${res.status}`;
  } catch {
    return `HTTP ${res.status}`;
  }
}

export async function register({
  email,
  password,
  displayName,
}: {
  email: string;
  password: string;
  displayName?: string;
}): Promise<AuthUser> {
  const res = await fetch(`${BASE}/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, displayName }),
  });

  if (!res.ok) {
    throw new Error(await extractError(res));
  }

  const data = (await res.json()) as { token: string; user: AuthUser };
  setSession(data);
  return data.user;
}

export async function login({
  email,
  password,
}: {
  email: string;
  password: string;
}): Promise<AuthUser> {
  const res = await fetch(`${BASE}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    throw new Error(await extractError(res));
  }

  const data = (await res.json()) as { token: string; user: AuthUser };
  setSession(data);
  return data.user;
}

export async function logout(): Promise<void> {
  try {
    await authFetch(`${BASE}/logout`, { method: "POST" });
  } catch {
    // best-effort — clear locally regardless
  } finally {
    clearSession();
  }
}

export async function me(): Promise<AuthUser> {
  const res = await authFetch(`${BASE}/me`);
  if (!res.ok) {
    throw new Error(await extractError(res));
  }
  return res.json() as Promise<AuthUser>;
}
