import { NextResponse } from "next/server";
import type { ErrorBody, ErrorCode } from "@cat-dog-diary/shared-types";

const STATUS: Record<ErrorCode, number> = {
  UNAUTHENTICATED: 401,
  NOT_FOUND: 404,
  VALIDATION_FAILED: 422,
  PET_DELETED: 409,
  DAILY_QUOTA_EXCEEDED: 429,
  REGEN_QUOTA_EXCEEDED: 429,
  GATEWAY_ERROR: 502,
  INTERNAL_ERROR: 500,
};

export function errorResponse(code: ErrorCode, message: string) {
  const body: ErrorBody = { error: { code, message } };
  return NextResponse.json(body, { status: STATUS[code] });
}
