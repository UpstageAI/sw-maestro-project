"use client";

import { REFRESH_STEP_NAMES, useRefreshStore, type RefreshStepName } from "../lib/store/refresh";

type LoadingStepProps = {
  label: string;
  current: number;
  total: number;
  unit: string;
  valueMode?: "fraction" | "percent";
};

const stepLabels: Record<
  RefreshStepName,
  { label: string; unit: string; valueMode?: LoadingStepProps["valueMode"] }
> = {
  collect: { label: "주요 뉴스 수집", unit: "매체" },
  summarize: { label: "AI 요약 생성", unit: "기사" },
  prepare: { label: "기사 준비 중", unit: "작업", valueMode: "percent" },
};

function LoadingStep({ label, current, total, unit, valueMode = "fraction" }: LoadingStepProps) {
  const progress = total > 0 ? Math.min(100, Math.round((current / total) * 100)) : 0;
  const isDone = total > 0 && current >= total;
  const isActive = current > 0 && !isDone;
  const progressText =
    total > 0 && valueMode === "percent" ? (
      <>{progress}%</>
    ) : total > 0 ? (
      <>
        <span>{current}</span>
        <span className="mx-0.5 opacity-55">/</span>
        <span>{total}</span> {unit}
      </>
    ) : (
      "준비 중"
    );

  return (
    <li className="grid gap-1.5" data-step={label}>
      <div className="flex items-baseline justify-between gap-2.5">
        <span
          className={`text-[13px] font-[700] tracking-[0] ${
            isActive || isDone ? "text-ink" : "text-muted"
          }`}
        >
          {label}
        </span>
        <span
          className={`text-[12px] font-[700] tabular-nums tracking-[0] ${
            isActive ? "text-brand-500" : isDone ? "text-muted" : "text-hint"
          }`}
        >
          {progressText}
        </span>
      </div>
      <div className="relative h-1 overflow-hidden rounded-sm bg-line">
        <div
          aria-hidden="true"
          className={`absolute inset-y-0 left-0 rounded-sm bg-brand-500 transition-[width] duration-[400ms] ease-out ${
            isDone ? "opacity-55" : ""
          }`}
          style={{ width: `${progress}%` }}
        />
      </div>
    </li>
  );
}

function LoadingOrbit() {
  return (
    <div
      aria-hidden="true"
      className="relative h-12 w-12 rounded-[18px] bg-white"
      data-testid="loading-orbit"
    >
      <span className="animate-orbit absolute inset-[9px] rounded-full border-2 border-[rgba(255,138,61,0.22)] border-t-brand-500" />
      <span className="absolute inset-[18px] rounded-full bg-brand-500 shadow-[0_0_0_6px_rgba(255,138,61,0.12)]" />
    </div>
  );
}

function NewsSkeleton() {
  return (
    <div className="grid gap-2.5 overflow-hidden rounded-[22px] bg-chip p-4" data-testid="news-skeleton">
      <span className="skeleton-shimmer h-2.5 w-[72px] rounded-full" />
      <strong className="skeleton-shimmer h-4 w-[86%] rounded-full" />
      <p className="skeleton-shimmer h-3 w-[62%] rounded-full" />
    </div>
  );
}

export function FeedLoadingProgress() {
  const collect = useRefreshStore((state) => state.collect);
  const summarize = useRefreshStore((state) => state.summarize);
  const prepare = useRefreshStore((state) => state.prepare);
  const finalizing = useRefreshStore((state) => state.finalizing);
  const stepValues = { collect, summarize, prepare };

  return (
    <div aria-live="polite">
      <article
        aria-label="뉴스 로딩 상태"
        className="mt-7 grid grid-cols-[48px_1fr] gap-3.5 rounded-[24px] bg-brand-50 p-[18px]"
      >
        <LoadingOrbit />
        <div>
          <h3 className="mb-[7px] mt-0.5 text-[17px] font-[850] leading-[1.35] text-ink">
            {finalizing ? "뉴스를 마무리 중이에요" : "오늘의 뉴스를 정리 중이에요"}
            <span aria-hidden="true" className="typing-dots" />
          </h3>
          <p className="text-[13px] font-[600] leading-[1.45] text-muted break-keep">
            {finalizing
              ? "요약된 기사를 저장하고 리포트까지 준비하고 있어요."
              : "잠시만 기다리면 오늘의 핵심을 정리해드릴게요."}
          </p>
        </div>

        <ol className="col-span-full mt-3.5 grid gap-3">
          {REFRESH_STEP_NAMES.map((step) => (
            <LoadingStep key={step} {...stepLabels[step]} {...stepValues[step]} />
          ))}
        </ol>
      </article>

      <div className="mt-4 grid gap-2.5" aria-hidden="true">
        <NewsSkeleton />
        <NewsSkeleton />
      </div>
    </div>
  );
}
