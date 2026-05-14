"use client";

import Link from "next/link";
import { use } from "react";
import { BottomNav } from "../../../../components/bottom-nav";
import { PhoneFrame } from "../../../../components/phone-frame";
import { KeywordCloud } from "../../../../components/report/keyword-cloud";
import { ReportFlow } from "../../../../components/report/report-flow";
import { ReportTimeline } from "../../../../components/report/report-timeline";
import { DailyReportNotReadyError, useDailyReport } from "../../../../lib/api/reports";
import { formatSeoulTime } from "../../../../lib/datetime";

type DailyReportPageProps = {
  params: Promise<{ date: string }>;
};

function formatDateLabel(date: string) {
  return new Intl.DateTimeFormat("ko-KR", {
    month: "long",
    day: "numeric",
    timeZone: "Asia/Seoul",
  }).format(new Date(`${date}T00:00:00+09:00`));
}

function formatUpdateLabel(updatedAt: string) {
  const time = formatSeoulTime(updatedAt);

  if (time === updatedAt) {
    return "업데이트";
  }

  return `${time} 업데이트`;
}

function formatWeekdayLabel(date: string) {
  return new Intl.DateTimeFormat("ko-KR", { weekday: "long", timeZone: "Asia/Seoul" }).format(
    new Date(`${date}T00:00:00+09:00`),
  );
}

function ReportLoading() {
  return (
    <section role="status" aria-label="리포트 불러오는 중" className="grid gap-4">
      <span className="skeleton-shimmer h-8 w-32 rounded-full" />
      <span className="skeleton-shimmer h-3 w-36 rounded-full" />
      <div className="flex gap-3 rounded-[14px] border border-line bg-surface p-4">
        <span className="skeleton-shimmer h-7 w-7 rounded-lg" />
        <div className="grid flex-1 gap-2">
          <span className="skeleton-shimmer h-3 w-20 rounded-full" />
          <span className="skeleton-shimmer h-4 w-full rounded-full" />
        </div>
      </div>
    </section>
  );
}

function getReportErrorCopy(error: unknown) {
  if (error instanceof DailyReportNotReadyError) {
    return {
      title: "아직 리포트가 준비되지 않았어요",
      message: "새 리포트가 만들어지면 이곳에 표시됩니다.",
      action: true,
    };
  }

  return {
    title: "리포트를 불러오지 못했어요",
    message: "잠시 후 다시 시도해주세요.",
    action: false,
  };
}

function ReportError({ error }: { error: unknown }) {
  const copy = getReportErrorCopy(error);

  return (
    <section role="alert" className="rounded-card border border-line bg-surface p-5 text-center">
      <p className="text-[15px] font-extrabold text-ink">{copy.title}</p>
      <p className="mt-2 text-[13px] font-semibold leading-[1.5] text-muted">
        {copy.message}
      </p>
      {copy.action ? (
        <Link
          href="/feed"
          className="mt-4 inline-flex min-h-10 items-center justify-center rounded-full bg-brand-500 px-4 text-[13px] font-[800] text-white no-underline shadow-[0_8px_18px_rgba(255,138,61,0.18)]"
        >
          피드로 돌아가기
        </Link>
      ) : null}
    </section>
  );
}

function DailyReportContent({ date }: { date: string }) {
  const { data: report, error, isLoading } = useDailyReport(date);

  if (isLoading) {
    return <ReportLoading />;
  }

  if (error || !report) {
    return <ReportError error={error} />;
  }

  return (
    <>
      <h1 className="sr-only">오늘의 리포트</h1>
      <div className="report-top mt-1 flex items-baseline justify-between gap-3">
        <p className="m-0 text-[30px] font-[800] tracking-[-0.6px] text-ink">
          {formatDateLabel(report.date)}
        </p>
        <time
          className="text-[12px] font-[600] text-hint"
          dateTime={report.updatedAt}
        >
          {formatUpdateLabel(report.updatedAt)}
        </time>
      </div>
      <p className="mb-[18px] mt-1 text-[13px] text-muted">
        {formatWeekdayLabel(report.date)} · 데일리 리포트
      </p>

      <section className="mb-6 flex items-start gap-3 rounded-[14px] border border-line bg-surface px-4 pb-4 pt-3.5">
        <span
          aria-hidden="true"
          className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-[11px] font-[800] tracking-[0.4px] text-brand-500"
        >
          AI
        </span>
        <div>
          <span className="mb-1 block text-[10px] font-[700] tracking-[1.2px] text-hint">
            BRIEFING
          </span>
          <h2 className="sr-only">
            {report.briefing.headline}
          </h2>
          <p className="m-0 max-w-none text-[14px] font-[400] leading-[1.55] text-ink break-keep">
            {report.briefing.summary}
          </p>
        </div>
      </section>

      <ReportTimeline items={report.timeline} />
      <ReportFlow items={report.flow} />
      <KeywordCloud keywords={report.keywords} />
      <div className="mb-2 mt-1 flex items-center justify-center gap-2 border-t border-dashed border-line pt-[18px] text-[12px] font-[600] text-hint">
        <span
          aria-hidden="true"
          className="inline-flex h-4 w-4 items-center justify-center rounded-full bg-brand-50 text-[10px] text-brand-500"
        >
          ✓
        </span>
        <span>오늘 따라잡기 끝 — 내일 09:30에 다시 만나요</span>
      </div>
    </>
  );
}

export default function DailyReportPage({ params }: DailyReportPageProps) {
  const { date } = use(params);

  return (
    <main className="flex min-h-dvh items-center justify-center bg-bg px-5 py-6 text-ink">
      <PhoneFrame>
        <div className="page-enter-soft scrollbar-none min-h-0 flex-1 overflow-y-auto px-[22px] pb-[18px] pt-[18px]">
          <DailyReportContent date={date} />
        </div>
        <BottomNav active="report" />
      </PhoneFrame>
    </main>
  );
}
