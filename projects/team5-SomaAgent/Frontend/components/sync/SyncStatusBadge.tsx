"use client";

import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  CircleAlert,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  formatAbsoluteTime,
  formatRelativeTime,
} from "@/lib/relativeTime";
import {
  SYNC_JOB_LABELS,
  type SyncInfoResponse,
  type SyncJobKey,
  type SyncJobStatus,
} from "@/lib/syncInfo";
import { useSyncInfo } from "@/hooks/useSyncInfo";

type OverallTone = "ok" | "warn" | "error" | "loading" | "empty";

type Summary = {
  tone: OverallTone;
  label: string;
};

const JOB_KEYS: SyncJobKey[] = [
  "notices_sync",
  "mentorings_sync",
  "webex_sync",
];

const TONE_BADGE: Record<OverallTone, string> = {
  ok: "border-emerald-200 bg-emerald-50 text-emerald-700",
  warn: "border-amber-200 bg-amber-50 text-amber-700",
  error: "border-rose-200 bg-rose-50 text-rose-700",
  loading: "border-slate-200 bg-slate-50 text-slate-500",
  empty: "border-slate-200 bg-slate-50 text-slate-500",
};

const TONE_DOT: Record<OverallTone, string> = {
  ok: "bg-emerald-500",
  warn: "bg-amber-500",
  error: "bg-rose-500",
  loading: "bg-slate-400",
  empty: "bg-slate-300",
};

function buildSummary(
  data: SyncInfoResponse | null,
  status: ReturnType<typeof useSyncInfo>["status"],
): Summary {
  if (status === "error") {
    return { tone: "error", label: "동기화 확인 실패" };
  }
  if (!data) {
    return { tone: "loading", label: "동기화 확인 중" };
  }

  const jobs = JOB_KEYS.map((key) => data.jobs[key]).filter(
    (job): job is SyncJobStatus => Boolean(job),
  );

  if (jobs.length === 0) {
    return { tone: "empty", label: "동기화 정보 없음" };
  }

  const hasError = jobs.some((job) => job.lastError);
  const successTimestamps = jobs
    .map((job) => job.lastSuccessAt)
    .filter((value): value is string => Boolean(value));

  if (successTimestamps.length === 0) {
    return { tone: "warn", label: "동기화 이력 없음" };
  }

  const latest = successTimestamps.reduce((max, current) =>
    new Date(current).getTime() > new Date(max).getTime() ? current : max,
  );

  const tone: OverallTone = hasError ? "warn" : "ok";
  const prefix = hasError ? "일부 실패 · " : "";
  return { tone, label: `${prefix}${formatRelativeTime(latest)} 동기화` };
}

export function SyncStatusBadge() {
  const { data, status, error, lastFetchedAt, refresh } = useSyncInfo();
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const summary = useMemo(() => buildSummary(data, status), [data, status]);

  useEffect(() => {
    if (!open) return;
    const onClick = (event: MouseEvent) => {
      if (!containerRef.current) return;
      if (!containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        aria-haspopup="true"
        aria-expanded={open}
        aria-label="동기화 상태 자세히 보기"
        className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium transition hover:brightness-95 ${TONE_BADGE[summary.tone]}`}
      >
        {status === "loading" && !data ? (
          <Loader2 className="h-3 w-3 animate-spin" />
        ) : (
          <span className={`h-1.5 w-1.5 rounded-full ${TONE_DOT[summary.tone]}`} />
        )}
        <span>{summary.label}</span>
        <ChevronDown
          className={`h-3 w-3 transition ${open ? "rotate-180" : ""}`}
        />
      </button>

      {open && (
        <div
          role="dialog"
          aria-label="동기화 상태 상세"
          className="absolute right-0 top-full z-30 mt-2 w-80 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-lg"
        >
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
            <div>
              <p className="text-sm font-semibold text-slate-900">동기화 상태</p>
              <p className="text-[11px] text-slate-500">
                {lastFetchedAt
                  ? `${formatRelativeTime(lastFetchedAt.toISOString())} 확인`
                  : "확인 중"}
              </p>
            </div>
            <button
              type="button"
              onClick={refresh}
              aria-label="지금 새로고침"
              className="grid h-8 w-8 place-items-center rounded-lg text-slate-500 transition hover:bg-slate-100 hover:text-slate-700"
            >
              <RefreshCw
                className={`h-4 w-4 ${status === "loading" ? "animate-spin" : ""}`}
              />
            </button>
          </div>

          {status === "error" && (
            <div className="flex items-start gap-2 border-b border-rose-100 bg-rose-50/60 px-4 py-3 text-xs text-rose-700">
              <CircleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              <div>
                <p className="font-medium">동기화 정보를 가져오지 못했습니다.</p>
                <p className="mt-0.5 text-[11px] text-rose-600/80">
                  {error ?? "잠시 후 다시 시도해 주세요."}
                </p>
              </div>
            </div>
          )}

          <ul className="divide-y divide-slate-100">
            {JOB_KEYS.map((key) => {
              const job = data?.jobs[key];
              return <JobRow key={key} jobKey={key} job={job} />;
            })}
          </ul>

          <div className="border-t border-slate-100 bg-slate-50 px-4 py-2 text-[11px] text-slate-500">
            매 60초마다 자동 갱신 · /api/v1/system/sync-info
          </div>
        </div>
      )}
    </div>
  );
}

function JobRow({
  jobKey,
  job,
}: {
  jobKey: SyncJobKey;
  job: SyncJobStatus | undefined;
}) {
  if (!job) {
    return (
      <li className="flex items-start gap-3 px-4 py-3">
        <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-slate-300" />
        <div className="min-w-0">
          <p className="text-sm font-medium text-slate-700">
            {SYNC_JOB_LABELS[jobKey]}
          </p>
          <p className="text-xs text-slate-400">정보 없음</p>
        </div>
      </li>
    );
  }

  const hasError = Boolean(job.lastError);
  const Icon = hasError ? AlertTriangle : CheckCircle2;
  const iconClass = hasError ? "text-amber-500" : "text-emerald-500";

  return (
    <li className="flex items-start gap-3 px-4 py-3">
      <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${iconClass}`} />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-slate-800">
          {SYNC_JOB_LABELS[jobKey]}
        </p>
        <dl className="mt-1 space-y-0.5 text-[11px] text-slate-500">
          <div className="flex justify-between gap-3">
            <dt>마지막 성공</dt>
            <dd
              className="truncate text-slate-700"
              title={formatAbsoluteTime(job.lastSuccessAt)}
            >
              {formatRelativeTime(job.lastSuccessAt)}
            </dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt>마지막 실행</dt>
            <dd
              className="truncate text-slate-700"
              title={formatAbsoluteTime(job.lastRunAt)}
            >
              {formatRelativeTime(job.lastRunAt)}
            </dd>
          </div>
        </dl>
        {hasError && (
          <p className="mt-1.5 rounded-md bg-amber-50 px-2 py-1 text-[11px] text-amber-700">
            {job.lastError}
          </p>
        )}
      </div>
    </li>
  );
}
