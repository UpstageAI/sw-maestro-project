/**
 * 백엔드 (FastAPI orchestration API) 통신 클라이언트.
 *
 * 모든 비동기 작업은 job 기반: 시작 요청 → 202 Accepted + job_id → polling.
 * - 백엔드 명세: Detailed_API_USAGE.md
 * - rewrites 로 same-origin 요청처럼 호출 (next.config.ts).
 */

// ─────────────────────────────────────────────
// 타입 (백엔드 schema 와 1:1 매칭)
// ─────────────────────────────────────────────
export type Category = "역량" | "경험" | "문제해결" | "협업" | "적합성";

export interface Question {
  id: string;
  text: string;
  category: Category;
  difficulty: number;
  is_followup: boolean;
  parent_id: string | null;
}

export interface Evaluation {
  question: Question;
  user_answer: string;
  star_score: number;
  specificity_score: number;
  relevance_score: number;
  consistency_score: number;
  weakness_tags: string[];
  feedback: string;
  feedback_json: Record<string, unknown> | null;
}

export interface SessionSummary {
  session_id: string;
  status: "initializing" | "active" | "ended";
  is_active: boolean;
  busy_job_id: string | null;
  question_count: number;
  bundle_count: number;
  current_followup_depth: number;
  max_followup_depth: number;
  min_bundles_for_report: number;
  can_report: boolean;
  job_family: string;
  current_question: Question | null;
}

export interface Report {
  overall_score: number;
  category_scores: Record<string, number>;
  weakness_summary: string[];
  improvement_suggestions: string;
}

export type JobStatus = "queued" | "running" | "succeeded" | "failed";
export type JobType = "start_session" | "process_answer" | "generate_report";

export interface JobState<TResult = unknown> {
  job_id: string;
  job_type: JobType;
  session_id: string | null;
  status: JobStatus;
  step: string;
  progress: number;
  message: string;
  result: TResult | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface JobStartResponse {
  job_id: string;
  session_id: string | null;
  status_url: string;
  message: string;
}

// start_session 완료 result
export interface StartSessionResult {
  session: SessionSummary;
  question: Question;
}

// process_answer 완료 result
export type AnswerAction =
  | "retry"
  | "followup"
  | "next_question"
  | "can_report"
  | "force_end";

export interface ProcessAnswerResult {
  action: AnswerAction;
  evaluation?: Evaluation;
  question?: Question;
  can_report?: boolean;
  session?: SessionSummary;
  message?: string; // retry 일 때
}

// generate_report 완료 result
export interface GenerateReportResult {
  session: SessionSummary;
  report: Report;
}

// ─────────────────────────────────────────────
// fetch 래퍼
// ─────────────────────────────────────────────
class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(status: number, detail: unknown, message: string) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

async function apiFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const res = await fetch(path, init);
  if (!res.ok) {
    let detail: unknown = null;
    try {
      detail = await res.json();
    } catch {
      detail = await res.text().catch(() => null);
    }
    const msg =
      typeof detail === "object" && detail !== null && "detail" in detail
        ? typeof (detail as { detail: unknown }).detail === "string"
          ? (detail as { detail: string }).detail
          : JSON.stringify((detail as { detail: unknown }).detail)
        : res.statusText;
    throw new ApiError(res.status, detail, msg);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export { ApiError };

// ─────────────────────────────────────────────
// 엔드포인트
// ─────────────────────────────────────────────
export async function startSession(input: {
  files: File[];
  jobDescription: string;
  companyName?: string;
  companyCulture?: string;
}): Promise<JobStartResponse> {
  const fd = new FormData();
  input.files.forEach((f) => fd.append("files", f));
  fd.append("job_description", input.jobDescription);
  fd.append("company_name", input.companyName ?? "");
  fd.append("company_culture", input.companyCulture ?? "");

  return apiFetch<JobStartResponse>("/api/sessions", {
    method: "POST",
    body: fd,
  });
}

export async function getJob<TResult = unknown>(
  jobId: string,
): Promise<JobState<TResult>> {
  return apiFetch<JobState<TResult>>(`/api/jobs/${jobId}`);
}

export async function getSession(
  sessionId: string,
): Promise<SessionSummary> {
  return apiFetch<SessionSummary>(`/api/sessions/${sessionId}`);
}

export async function submitAnswer(
  sessionId: string,
  questionId: string,
  answer: string,
): Promise<JobStartResponse> {
  return apiFetch<JobStartResponse>(
    `/api/sessions/${sessionId}/answers`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question_id: questionId, answer }),
    },
  );
}

export async function generateReport(
  sessionId: string,
  force = true,
): Promise<JobStartResponse> {
  return apiFetch<JobStartResponse>(
    `/api/sessions/${sessionId}/report`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ force }),
    },
  );
}

// ─────────────────────────────────────────────
// pollJob — 1.5초 주기로 상태 조회. onProgress 콜백으로 step/message/progress 노출
// ─────────────────────────────────────────────
export async function pollJob<TResult>(
  jobId: string,
  options: {
    intervalMs?: number;
    signal?: AbortSignal;
    onProgress?: (job: JobState<TResult>) => void;
  } = {},
): Promise<TResult> {
  const { intervalMs = 1500, signal, onProgress } = options;

  while (true) {
    if (signal?.aborted) {
      throw new DOMException("polling aborted", "AbortError");
    }
    const job = await getJob<TResult>(jobId);
    onProgress?.(job);

    if (job.status === "succeeded") {
      if (job.result === null) {
        throw new Error("job succeeded but no result");
      }
      return job.result;
    }
    if (job.status === "failed") {
      throw new Error(job.error ?? "job failed");
    }

    await new Promise<void>((resolve, reject) => {
      const t = setTimeout(resolve, intervalMs);
      signal?.addEventListener(
        "abort",
        () => {
          clearTimeout(t);
          reject(new DOMException("polling aborted", "AbortError"));
        },
        { once: true },
      );
    });
  }
}
