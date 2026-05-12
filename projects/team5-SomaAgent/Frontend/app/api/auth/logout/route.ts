import { cookies } from "next/headers";
import { somaFetch, SomaApiError } from "@/lib/server/somaApi";
import {
  SESSION_COOKIE_NAME,
  errorResponse,
  unexpectedErrorResponse,
} from "../_helpers";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST() {
  const cookieStore = await cookies();
  const session = cookieStore.get(SESSION_COOKIE_NAME)?.value ?? null;

  // 쿠키는 항상 폐기 — 백엔드 호출 성공 여부와 무관하게 프론트는 로그아웃 상태.
  cookieStore.delete(SESSION_COOKIE_NAME);

  if (!session) return new Response(null, { status: 204 });

  try {
    await somaFetch<void>("/auth/session", {
      method: "DELETE",
      sessionId: session,
    });
    return new Response(null, { status: 204 });
  } catch (cause) {
    // 401(이미 만료) 등은 무시해도 사용자 입장에서는 로그아웃이 끝난 상태.
    if (cause instanceof SomaApiError && cause.status === 401) {
      return new Response(null, { status: 204 });
    }
    if (cause instanceof SomaApiError) return errorResponse(cause);
    return unexpectedErrorResponse(cause);
  }
}
