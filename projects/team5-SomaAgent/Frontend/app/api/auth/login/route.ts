import { cookies } from "next/headers";
import {
  normalizeAuthUser,
  type LoginRequest,
  type RawLoginResponse,
} from "@/lib/auth";
import { somaFetch, SomaApiError } from "@/lib/server/somaApi";
import {
  SESSION_COOKIE_NAME,
  errorResponse,
  sessionCookieOptions,
  unexpectedErrorResponse,
} from "../_helpers";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  let body: LoginRequest;
  try {
    body = (await request.json()) as LoginRequest;
  } catch {
    return Response.json(
      { code: "INVALID_REQUEST", message: "잘못된 요청 본문입니다." },
      { status: 400 },
    );
  }

  if (
    !body ||
    typeof body.username !== "string" ||
    typeof body.password !== "string" ||
    body.username.length === 0 ||
    body.password.length === 0
  ) {
    return Response.json(
      {
        code: "INVALID_REQUEST",
        message: "아이디와 비밀번호를 모두 입력해 주세요.",
      },
      { status: 400 },
    );
  }

  try {
    const raw = await somaFetch<RawLoginResponse>("/auth/login", {
      method: "POST",
      json: { username: body.username, password: body.password },
    });

    const cookieStore = await cookies();
    cookieStore.set(SESSION_COOKIE_NAME, raw.session_id, sessionCookieOptions);

    return Response.json(normalizeAuthUser(raw), { status: 200 });
  } catch (cause) {
    if (cause instanceof SomaApiError) return errorResponse(cause);
    return unexpectedErrorResponse(cause);
  }
}
