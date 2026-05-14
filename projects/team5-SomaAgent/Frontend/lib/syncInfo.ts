import { apiFetch } from "@/lib/api";

export type SyncJobStatus = {
  lastRunAt: string | null;
  lastSuccessAt: string | null;
  lastError: string | null;
};

export type SyncJobKey = "notices_sync" | "mentorings_sync" | "webex_sync";

export type SyncInfoResponse = {
  jobs: Record<SyncJobKey, SyncJobStatus>;
};

export const SYNC_JOB_LABELS: Record<SyncJobKey, string> = {
  notices_sync: "공지 동기화",
  mentorings_sync: "멘토링 동기화",
  webex_sync: "Webex 동기화",
};

export async function fetchSyncInfo(
  signal?: AbortSignal,
): Promise<SyncInfoResponse> {
  return apiFetch<SyncInfoResponse>("/api/v1/system/sync-info", { signal });
}
