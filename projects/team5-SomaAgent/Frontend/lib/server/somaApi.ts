import "server-only";

// 서버 측 Route Handler 전용 백엔드(FastAPI) 호출 래퍼.
// 브라우저는 이 모듈을 import 할 수 없다 (SOMA_API_BASE_URL 노출 방지 + CORS 우회).

const BASE_URL =
  process.env.SOMA_API_BASE_URL ?? "http://insung-server.servemp3.com:8000";

export const SOMA_SESSION_COOKIE =
  process.env.SOMA_SESSION_COOKIE_NAME ?? "soma_session";

// FastAPI 422 표준 응답 형태.
type FastApiValidationError = {
  detail: Array<{
    loc: Array<string | number>;
    msg: string;
    type: string;
    input?: unknown;
    ctx?: Record<string, unknown>;
  }>;
};

// docs/spec/API.md §2.3 공통 에러 형식.
type SomaErrorBody = {
  code?: string;
  message?: string;
  details?: unknown;
};

export type SomaApiErrorPayload = {
  status: number;
  code?: string;
  message: string;
  details?: unknown;
};

export class SomaApiError extends Error {
  status: number;
  code?: string;
  details?: unknown;

  constructor(payload: SomaApiErrorPayload) {
    super(payload.message);
    this.name = "SomaApiError";
    this.status = payload.status;
    this.code = payload.code;
    this.details = payload.details;
  }

  toJSON(): SomaApiErrorPayload {
    return {
      status: this.status,
      code: this.code,
      message: this.message,
      details: this.details,
    };
  }
}

type SomaFetchOptions = Omit<RequestInit, "body"> & {
  // JSON으로 직렬화할 객체. 원시 string body가 필요하면 RequestInit.body 사용을 위해 별도 처리.
  json?: unknown;
  sessionId?: string | null;
  // 백엔드 자체 타임아웃이 길 수 있으므로 ms 단위로 제어.
  timeoutMs?: number;
};

const DEFAULT_TIMEOUT_MS = 15_000;

async function parseErrorBody(response: Response): Promise<SomaApiErrorPayload> {
  let code: string | undefined;
  let message = `HTTP ${response.status}`;
  let details: unknown;

  try {
    const body = (await response.json()) as SomaErrorBody & FastApiValidationError;

    if (typeof body?.message === "string" && body.message.length > 0) {
      message = body.message;
      code = body.code;
      details = body.details;
    } else if (Array.isArray(body?.detail) && body.detail.length > 0) {
      // FastAPI 422.
      const first = body.detail[0];
      message = first?.msg ?? message;
      code = "INVALID_REQUEST";
      details = body.detail;
    }
  } catch {
    // 비-JSON 응답은 무시.
  }

  return { status: response.status, code, message, details };
}

export async function somaFetch<T>(
  path: string,
  options: SomaFetchOptions = {},
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const { json, sessionId, timeoutMs, headers, signal, ...rest } = options;

  const controller = new AbortController();
  const timeoutId = setTimeout(
    () => controller.abort(new Error("UPSTREAM_TIMEOUT")),
    timeoutMs ?? DEFAULT_TIMEOUT_MS,
  );

  // 호출자가 signal을 넘긴 경우 두 신호를 합친다.
  if (signal) {
    if (signal.aborted) controller.abort(signal.reason);
    else signal.addEventListener("abort", () => controller.abort(signal.reason));
  }

  const finalHeaders: Record<string, string> = {
    Accept: "application/json",
    ...(json !== undefined ? { "Content-Type": "application/json" } : {}),
    ...(sessionId ? { "x-soma-session": sessionId } : {}),
    ...((headers as Record<string, string> | undefined) ?? {}),
  };

  let response: Response;
  try {
    response = await fetch(url, {
      ...rest,
      headers: finalHeaders,
      body: json !== undefined ? JSON.stringify(json) : undefined,
      signal: controller.signal,
      cache: "no-store",
    });
  } catch (cause) {
    clearTimeout(timeoutId);
    const aborted =
      cause instanceof DOMException && cause.name === "AbortError";
    throw new SomaApiError({
      status: 503,
      code: aborted ? "UPSTREAM_TIMEOUT" : "UPSTREAM_UNAVAILABLE",
      message: aborted
        ? "백엔드 응답이 지연되어 요청을 중단했습니다."
        : "백엔드에 연결할 수 없습니다.",
      details: cause instanceof Error ? { cause: cause.message } : undefined,
    });
  }

  clearTimeout(timeoutId);

  if (!response.ok) {
    const payload = await parseErrorBody(response);
    throw new SomaApiError(payload);
  }

  if (response.status === 204) return undefined as T;

  // 일부 엔드포인트는 빈 본문을 보낼 수 있어 안전하게 처리.
  const text = await response.text();
  if (!text) return undefined as T;
  return JSON.parse(text) as T;
}
