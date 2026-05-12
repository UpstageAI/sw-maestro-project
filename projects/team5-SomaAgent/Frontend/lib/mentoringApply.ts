import { apiFetch, ApiError } from "@/lib/api";
import type { ActionResult, ActionType, ApplicationData } from "@/lib/types/action";

// Swagger ActionResult: type, status, message, payload
type RawApplyResponse = {
  type?: string;
  status?: string;
  message?: string;
  payload?: Record<string, unknown>;
};

function mapBackendTypeToActionType(t: string | undefined): ActionType {
  if (t === "MENTORING_CANCEL" || t === "mentoring_cancel") {
    return "MENTORING_CANCEL";
  }
  return "MENTORING_APPLY";
}

function pickApplicationFromPayload(
  payload: Record<string, unknown> | undefined,
): ApplicationData | undefined {
  if (!payload || typeof payload !== "object") return undefined;
  const p = payload;
  const applySn = p.apply_sn ?? p.applySn;
  const qustnrSn = p.qustnr_sn ?? p.qustnrSn;
  const mid = p.mentoring_id ?? p.mentoringId;
  const mentoringId =
    typeof mid === "string"
      ? mid
      : typeof mid === "number"
        ? String(mid)
        : undefined;
  const title = p.title;
  if (
    typeof applySn !== "number" ||
    typeof qustnrSn !== "number" ||
    !mentoringId ||
    typeof title !== "string"
  ) {
    return undefined;
  }
  return {
    applySn,
    qustnrSn,
    mentoringId,
    title,
    sessionStartedAt:
      typeof p.session_started_at === "string"
        ? p.session_started_at
        : typeof p.sessionStartedAt === "string"
          ? p.sessionStartedAt
          : undefined,
  };
}

export function normalizeMentoringApplyResponse(raw: unknown): ActionResult {
  if (!raw || typeof raw !== "object") {
    return {
      actionType: "MENTORING_APPLY",
      status: "failed",
      message: "알 수 없는 응답 형식입니다.",
      error: {
        code: "INVALID_RESPONSE",
        message: "서버 응답을 해석할 수 없습니다.",
        recoverable: true,
      },
    };
  }

  const r = raw as RawApplyResponse;

  if (r.status === "success" || r.status === "failed") {
    const payload =
      r.payload && typeof r.payload === "object"
        ? (r.payload as Record<string, unknown>)
        : undefined;
    const application = pickApplicationFromPayload(payload);
    return {
      actionType: mapBackendTypeToActionType(r.type),
      status: r.status,
      message:
        r.message ??
        (r.status === "success" ? "처리되었습니다." : "처리에 실패했습니다."),
      ...(application
        ? { data: { application } }
        : {}),
      traceId: undefined,
    };
  }

  if ("label" in raw && "payload" in raw) {
    return {
      actionType: "MENTORING_APPLY",
      status: "failed",
      message: "확인 단계 응답을 받았습니다. 백엔드 설정을 점검해 주세요.",
      error: {
        code: "ACTION_PROPOSAL",
        message: "서버가 추가 확인을 요청했습니다.",
        recoverable: true,
      },
    };
  }

  return {
    actionType: "MENTORING_APPLY",
    status: "failed",
    message: r.message ?? "처리에 실패했습니다.",
    error: {
      code: "UNKNOWN",
      message: "응답을 해석할 수 없습니다.",
      recoverable: true,
    },
  };
}

export async function applyMentoringViaApi(
  mentoringId: number,
  args: { confirmed: boolean; somaUserId: string },
  signal?: AbortSignal,
): Promise<ActionResult> {
  try {
    const raw = await apiFetch<unknown>(
      `/api/v1/mentoring/${mentoringId}/apply`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          confirmed: args.confirmed,
          soma_user_id: args.somaUserId,
        }),
        credentials: "same-origin",
        signal,
      },
    );
    return normalizeMentoringApplyResponse(raw);
  } catch (cause) {
    if (cause instanceof ApiError) {
      return {
        actionType: "MENTORING_APPLY",
        status: "failed",
        message: cause.message,
        error: {
          code: cause.code ?? `HTTP_${cause.status}`,
          message: cause.message,
          recoverable: cause.status >= 500,
        },
      };
    }
    throw cause;
  }
}
