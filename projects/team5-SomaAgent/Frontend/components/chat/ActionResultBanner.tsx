import {
  CalendarCheck,
  CalendarOff,
  CalendarX,
  CheckCircle2,
  CircleAlert,
  ExternalLink,
  Hash,
  TriangleAlert,
} from "lucide-react";
import {
  ACTION_TYPE_LABEL,
  type ActionResult,
  type ActionResultTone,
  deriveActionResultTone,
} from "@/lib/types/action";
import { formatAbsoluteTime } from "@/lib/relativeTime";

const TONE_STYLES: Record<
  ActionResultTone,
  {
    container: string;
    iconWrap: string;
    title: string;
    label: string;
    badge: string;
  }
> = {
  success: {
    container: "border-emerald-200 bg-emerald-50/70",
    iconWrap: "bg-emerald-100 text-emerald-600",
    title: "text-emerald-900",
    label: "신청 완료",
    badge: "bg-emerald-100 text-emerald-700",
  },
  partial: {
    container: "border-amber-200 bg-amber-50/70",
    iconWrap: "bg-amber-100 text-amber-600",
    title: "text-amber-900",
    label: "부분 완료",
    badge: "bg-amber-100 text-amber-700",
  },
  failed: {
    container: "border-rose-200 bg-rose-50/70",
    iconWrap: "bg-rose-100 text-rose-600",
    title: "text-rose-900",
    label: "실패",
    badge: "bg-rose-100 text-rose-700",
  },
};

function ToneIcon({ tone }: { tone: ActionResultTone }) {
  if (tone === "success") return <CheckCircle2 className="h-5 w-5" />;
  if (tone === "partial") return <TriangleAlert className="h-5 w-5" />;
  return <CircleAlert className="h-5 w-5" />;
}

export function ActionResultBanner({ result }: { result: ActionResult }) {
  const tone = deriveActionResultTone(result);
  const styles = TONE_STYLES[tone];
  const actionLabel =
    result.actionType === "MENTORING_CANCEL" && tone === "success"
      ? "취소 완료"
      : styles.label;

  return (
    <article
      className={`rounded-2xl border px-4 py-3 ${styles.container}`}
      role={tone === "failed" ? "alert" : "status"}
      aria-live={tone === "failed" ? "assertive" : "polite"}
    >
      <header className="flex items-start gap-3">
        <span
          className={`grid h-9 w-9 shrink-0 place-items-center rounded-full ${styles.iconWrap}`}
        >
          <ToneIcon tone={tone} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className={`text-sm font-semibold ${styles.title}`}>
              {actionLabel}
            </p>
            <span
              className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${styles.badge}`}
            >
              {ACTION_TYPE_LABEL[result.actionType]}
            </span>
          </div>
          <p className="mt-1 text-sm leading-relaxed text-slate-700">
            {result.message}
          </p>
        </div>
      </header>

      {result.data?.application && (
        <ApplicationSummary application={result.data.application} />
      )}

      {result.data?.calendarInvite && (
        <CalendarSummary invite={result.data.calendarInvite} tone={tone} />
      )}

      {result.error && <ErrorSummary error={result.error} />}
    </article>
  );
}

function ApplicationSummary({
  application,
}: {
  application: NonNullable<ActionResult["data"]>["application"];
}) {
  if (!application) return null;
  return (
    <dl className="mt-3 grid grid-cols-1 gap-1 rounded-xl bg-white/70 px-3 py-2 text-xs text-slate-600 sm:grid-cols-[auto_1fr] sm:gap-x-3">
      <dt className="font-medium text-slate-500">멘토링</dt>
      <dd className="truncate text-slate-800">{application.title}</dd>

      {application.sessionStartedAt && (
        <>
          <dt className="font-medium text-slate-500">시작</dt>
          <dd className="text-slate-800">
            {formatAbsoluteTime(application.sessionStartedAt)}
          </dd>
        </>
      )}

      <dt className="font-medium text-slate-500">접수번호</dt>
      <dd className="flex items-center gap-1 text-slate-700">
        <Hash className="h-3 w-3 text-slate-400" />
        {application.applySn}
      </dd>
    </dl>
  );
}

function CalendarSummary({
  invite,
  tone,
}: {
  invite: NonNullable<ActionResult["data"]>["calendarInvite"];
  tone: ActionResultTone;
}) {
  if (!invite) return null;

  if (invite.status === "created") {
    return (
      <p className="mt-3 inline-flex items-center gap-1.5 text-xs text-emerald-700">
        <CalendarCheck className="h-3.5 w-3.5" />
        Google Calendar 등록 완료
        {invite.eventId && (
          <span className="ml-1 rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] text-emerald-700">
            event {invite.eventId.slice(0, 8)}
          </span>
        )}
      </p>
    );
  }

  if (invite.status === "skipped") {
    return (
      <p className="mt-3 inline-flex items-center gap-1.5 text-xs text-slate-600">
        <CalendarOff className="h-3.5 w-3.5" />
        Google Calendar 등록 건너뜀
      </p>
    );
  }

  // failed
  return (
    <div
      className={`mt-3 flex items-start gap-2 rounded-lg px-3 py-2 text-xs ${
        tone === "partial"
          ? "bg-amber-100/70 text-amber-800"
          : "bg-rose-100/70 text-rose-800"
      }`}
    >
      <CalendarX className="mt-0.5 h-3.5 w-3.5 shrink-0" />
      <div className="min-w-0">
        <p className="font-medium">캘린더 등록 실패</p>
        <p className="mt-0.5 leading-relaxed">
          멘토링 신청은 정상 처리됐지만 Google Calendar 등록은 실패했어요. 캘린더
          앱에서 직접 일정을 추가해 주세요.
          {invite.errorMessage && (
            <>
              <br />
              <span className="text-[11px] opacity-80">
                상세: {invite.errorMessage}
              </span>
            </>
          )}
        </p>
      </div>
    </div>
  );
}

function ErrorSummary({
  error,
}: {
  error: NonNullable<ActionResult["error"]>;
}) {
  return (
    <div className="mt-3 rounded-lg bg-white/70 px-3 py-2 text-xs text-rose-800">
      <div className="flex items-center gap-1.5 font-medium">
        <ExternalLink className="h-3 w-3" />
        {error.code}
      </div>
      <p className="mt-1 leading-relaxed text-rose-700">{error.message}</p>
      {error.recoverable && (
        <p className="mt-1.5 text-[11px] text-rose-600/80">
          잠시 후 다시 시도할 수 있어요.
        </p>
      )}
    </div>
  );
}
