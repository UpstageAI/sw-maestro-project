import { cookies } from "next/headers";
import { normalizeAuthUser, type RawAuthUser } from "@/lib/auth";
import { somaFetch, SomaApiError } from "@/lib/server/somaApi";
import {
  SESSION_COOKIE_NAME,
  errorResponse,
  unexpectedErrorResponse,
} from "../_helpers";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  const cookieStore = await cookies();
  const session = cookieStore.get(SESSION_COOKIE_NAME)?.value ?? null;

  if (!session) {
    return Response.json(
      { code: "SOMA_AUTH_REQUIRED", message: "로그인이 필요합니다." },
      { status: 401 },
    );
  }

  try {
    const raw = await somaFetch<RawAuthUser>("/auth/whoami", {
      method: "GET",
      sessionId: session,
    });
    return Response.json(normalizeAuthUser(raw), { status: 200 });
  } catch (cause) {
    if (cause instanceof SomaApiError) {
      if (cause.status === 401) {
        // 백엔드가 세션 만료라고 한 경우 쿠키도 함께 폐기.
        cookieStore.delete(SESSION_COOKIE_NAME);
      }
      return errorResponse(cause);
    }
    return unexpectedErrorResponse(cause);
  }
}
