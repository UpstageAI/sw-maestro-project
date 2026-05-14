// FastAPI 백엔드와 통신하기 위한 공통 fetch 래퍼.
// X-Soma-Session(인증)·X-Session-Id(대화 세션) 헤더는 호출 측이 직접 주입한다.

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

export class ApiError extends Error {
  status: number;
  code?: string;
  details?: unknown;

  constructor(
    status: number,
    message: string,
    options?: { code?: string; details?: unknown },
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = options?.code;
    this.details = options?.details;
  }
}

export type ApiFetchOptions = RequestInit & {
  signal?: AbortSignal;
};

export async function apiFetch<T>(
  path: string,
  options: ApiFetchOptions = {},
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      Accept: "application/json",
      ...(options.headers ?? {}),
    },
  });

  if (!response.ok) {
    let code: string | undefined;
    let message = `HTTP ${response.status}`;
    let details: unknown;
    try {
      const body = (await response.json()) as {
        code?: string;
        message?: string;
        details?: unknown;
      };
      code = body.code;
      if (body.message) message = body.message;
      details = body.details;
    } catch {
      // 비-JSON 응답은 무시하고 기본 메시지 사용.
    }
    throw new ApiError(response.status, message, { code, details });
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
