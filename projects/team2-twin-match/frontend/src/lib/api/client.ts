import createClient from "openapi-fetch";

import type { paths } from "./types";

const baseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export const api = createClient<paths>({ baseUrl });

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

type FetchResult<T> = {
  data?: T;
  error?: { detail?: string } | unknown;
  response: Response;
};

/**
 * 백엔드 spec §1.4: 모든 에러는 {"detail": "..."} 포맷.
 * 호출부는 unwrap()으로 통일된 ApiError만 다루면 된다.
 */
export async function unwrap<T>(promise: Promise<FetchResult<T>>): Promise<T> {
  const { data, error, response } = await promise;
  if (error) {
    const detail =
      typeof error === "object" && error !== null && "detail" in error
        ? String((error as { detail?: unknown }).detail ?? "")
        : "";
    throw new ApiError(response.status, detail || `HTTP ${response.status}`);
  }
  if (data === undefined) {
    throw new ApiError(response.status, "Empty response");
  }
  return data;
}
