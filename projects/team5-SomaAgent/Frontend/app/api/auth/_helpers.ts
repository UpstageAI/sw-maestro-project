import "server-only";
import { SOMA_SESSION_COOKIE, SomaApiError } from "@/lib/server/somaApi";

export const SESSION_COOKIE_NAME = SOMA_SESSION_COOKIE;

// Route Handler에서 SomaApiError를 표준 응답 본문으로 변환.
// 클라이언트 lib/api.ts의 ApiError 파싱 형태({ code, message, details })에 맞춘다.
export function errorResponse(error: SomaApiError): Response {
  return Response.json(
    {
      code: error.code ?? "UNKNOWN",
      message: error.message,
      details: error.details,
    },
    { status: error.status },
  );
}

export function unexpectedErrorResponse(error: unknown): Response {
  const message =
    error instanceof Error ? error.message : "예상치 못한 오류가 발생했습니다.";
  return Response.json(
    { code: "UNEXPECTED", message },
    { status: 500 },
  );
}

export const sessionCookieOptions = {
  httpOnly: true,
  sameSite: "lax" as const,
  path: "/",
  // dev(http://localhost)에서는 secure를 끈다. 운영(https)에서는 NODE_ENV로 자동 활성.
  secure: process.env.NODE_ENV === "production",
  // 로그인 세션 길이는 백엔드 정책을 모르므로 24h 보수적으로 설정.
  // 만료 후 401 응답을 받으면 클라이언트가 재로그인 모달을 띄운다.
  maxAge: 60 * 60 * 24,
};
