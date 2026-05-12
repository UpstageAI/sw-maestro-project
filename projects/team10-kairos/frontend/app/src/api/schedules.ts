import type {
  AnalyzeScheduleResponse,
  Schedule,
  ScheduleCreatePayload,
} from "../types/schedule";

const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
  "http://127.0.0.1:8000";

const TIMEZONE = process.env.EXPO_PUBLIC_TIMEZONE ?? "Asia/Seoul";

export async function analyzeSchedule(
  text: string,
): Promise<AnalyzeScheduleResponse> {
  return request<AnalyzeScheduleResponse>("/api/schedules/analyze", {
    method: "POST",
    body: JSON.stringify({ text, timezone: TIMEZONE }),
  });
}

export async function createSchedule(
  payload: ScheduleCreatePayload,
): Promise<Schedule> {
  return request<Schedule>("/api/schedules", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function listSchedules(): Promise<Schedule[]> {
  return request<Schedule[]>("/api/schedules");
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new Error(
      detail
        ? `API ${response.status}: ${detail}`
        : `API ${response.status}: request failed`,
    );
  }

  return response.json() as Promise<T>;
}

async function readErrorDetail(response: Response): Promise<string | null> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    return typeof body.detail === "string" ? body.detail : null;
  } catch {
    return null;
  }
}
