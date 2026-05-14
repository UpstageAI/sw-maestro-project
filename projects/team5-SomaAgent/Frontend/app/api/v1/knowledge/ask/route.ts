import type { KnowledgeAskRequest, KnowledgeAskResponse } from "@/lib/types/knowledge";
import {
  errorResponse,
  unexpectedErrorResponse,
} from "@/app/api/auth/_helpers";
import { somaFetch, SomaApiError } from "@/lib/server/somaApi";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function isKnowledgeAskBody(value: unknown): value is KnowledgeAskRequest {
  if (!value || typeof value !== "object") return false;
  const q = (value as KnowledgeAskRequest).query;
  return typeof q === "string" && q.trim().length > 0;
}

export async function POST(request: Request) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return Response.json(
      { code: "INVALID_REQUEST", message: "잘못된 요청 본문입니다." },
      { status: 400 },
    );
  }

  if (!isKnowledgeAskBody(body)) {
    return Response.json(
      {
        code: "INVALID_REQUEST",
        message: "질문(query)을 한 글자 이상 입력해 주세요.",
      },
      { status: 400 },
    );
  }

  const payload: KnowledgeAskRequest = {
    query: body.query.trim(),
  };
  if (body.source_types != null) payload.source_types = body.source_types;
  if (typeof body.official_only === "boolean")
    payload.official_only = body.official_only;
  if (body.room_name !== undefined) payload.room_name = body.room_name;
  if (typeof body.k === "number") payload.k = body.k;

  try {
    const data = await somaFetch<KnowledgeAskResponse>(
      "/api/v1/knowledge/ask",
      {
        method: "POST",
        json: payload,
      },
    );
    return Response.json(data, { status: 200 });
  } catch (cause) {
    if (cause instanceof SomaApiError) return errorResponse(cause);
    return unexpectedErrorResponse(cause);
  }
}
