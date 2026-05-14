import { cookies } from "next/headers";
import {
  SESSION_COOKIE_NAME,
  errorResponse,
  unexpectedErrorResponse,
} from "@/app/api/auth/_helpers";
import { somaFetch, SomaApiError } from "@/lib/server/somaApi";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(
  request: Request,
  ctx: { params: Promise<{ mentoringId: string }> },
) {
  const { mentoringId: rawId } = await ctx.params;
  const mentoringId = Number.parseInt(rawId, 10);
  if (Number.isNaN(mentoringId) || mentoringId < 1) {
    return Response.json(
      { code: "INVALID_REQUEST", message: "멘토링 ID가 올바르지 않습니다." },
      { status: 400 },
    );
  }

  let body: { confirmed?: boolean; soma_user_id?: string };
  try {
    body = (await request.json()) as typeof body;
  } catch {
    return Response.json(
      { code: "INVALID_REQUEST", message: "잘못된 요청 본문입니다." },
      { status: 400 },
    );
  }

  if (
    !body?.soma_user_id ||
    typeof body.soma_user_id !== "string" ||
    body.soma_user_id.trim().length === 0
  ) {
    return Response.json(
      { code: "INVALID_REQUEST", message: "soma_user_id가 필요합니다." },
      { status: 400 },
    );
  }

  const cookieStore = await cookies();
  const session = cookieStore.get(SESSION_COOKIE_NAME)?.value ?? null;

  try {
    const data = await somaFetch<unknown>(
      `/api/v1/mentoring/${mentoringId}/apply`,
      {
        method: "POST",
        sessionId: session,
        json: {
          confirmed: body.confirmed ?? true,
          soma_user_id: body.soma_user_id.trim(),
        },
      },
    );
    return Response.json(data, { status: 200 });
  } catch (cause) {
    if (cause instanceof SomaApiError) return errorResponse(cause);
    return unexpectedErrorResponse(cause);
  }
}
