"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import ViolationCard from "@/components/violation-card";

type Risk = "low" | "medium" | "high";
type AnalyzeItem = { title: string; risk_level: Risk; issue: string; law_reference?: string; action?: string };
type AnalyzeRes = {
  id: string;
  parsed: any;
  rule: { violations: any[]; checkedRules: string[] } | null;
  ai: { summary: string; items: AnalyzeItem[]; source: string } | null;
  ocrSource?: string;
};

const MIN_LOADING_MS = 1500;

// mock 응답은 SSR로 박혀 보이게 두지 않고, 항상 로딩 → 새 분석 흐름을 탄다.
function isUsableInitial(res: AnalyzeRes | null): boolean {
  return !!res?.ai && res.ai.source !== "mock";
}

export default function AnalyzeTrigger({ id, initial }: { id: string; initial: AnalyzeRes | null }) {
  const router = useRouter();
  const usable = isUsableInitial(initial);
  const [data, setData] = useState<AnalyzeRes | null>(usable ? initial : null);
  const [loading, setLoading] = useState<boolean>(!usable);
  const [error, setError] = useState<string | null>(null);
  const ran = useRef(false);

  const run = useCallback(async () => {
    setError(null);
    setData(null);
    setLoading(true);
    const startedAt = Date.now();
    try {
      const res = await fetch(`/api/analyze`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ id }),
      });
      if (!res.ok) throw new Error(await res.text());
      const json = (await res.json()) as AnalyzeRes;
      const elapsed = Date.now() - startedAt;
      if (elapsed < MIN_LOADING_MS) {
        await new Promise((r) => setTimeout(r, MIN_LOADING_MS - elapsed));
      }
      setData(json);
      router.refresh();
    } catch (e) {
      setError((e as Error).message || "분석에 실패했어요.");
    } finally {
      setLoading(false);
    }
  }, [id, router]);

  useEffect(() => {
    if (ran.current) return;
    if (usable) return;
    ran.current = true;
    void run();
  }, [usable, run]);

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="rounded-2xl bg-white border border-grey-200 p-5">
          <div className="flex items-center justify-between">
            <p className="text-[14px] font-bold text-grey-900">
              AI가 계약서를 분석 중이에요
            </p>
            <span className="inline-flex items-center gap-1.5 text-[11px] font-semibold text-toss-blue">
              <span className="relative flex h-1.5 w-1.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-toss-blue opacity-75" />
                <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-toss-blue" />
              </span>
              처리 중
            </span>
          </div>
          <div className="relative mt-3 h-1.5 w-full overflow-hidden rounded-full bg-grey-100">
            <span className="animate-loading-bar absolute top-0 h-full rounded-full bg-toss-blue" />
          </div>
          <p className="mt-2 text-[12px] text-grey-500">
            OCR · 조항 추출 · 근로기준법 비교 · AI 검토 순서로 진행됩니다.
          </p>
        </div>

        <div className="grid gap-3">
          <div className="rounded-2xl bg-grey-100 animate-pulse h-[120px]" />
          <div className="rounded-2xl bg-grey-100 animate-pulse h-[120px]" />
          <div className="rounded-2xl bg-grey-100 animate-pulse h-[120px]" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-2xl bg-danger-bg p-6 text-center">
        <div className="mx-auto inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-danger text-white">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
        </div>
        <p className="mt-3 text-[15px] font-bold text-danger">분석에 실패했어요</p>
        <p className="mt-1 text-[13px] text-grey-700 break-all">{error}</p>
        <button
          type="button"
          onClick={() => void run()}
          className="mt-4 inline-flex items-center justify-center rounded-xl bg-grey-900 hover:bg-grey-800 text-white text-[13px] font-semibold px-4 py-2"
        >
          다시 시도
        </button>
      </div>
    );
  }

  if (!data?.ai) {
    return (
      <div className="rounded-2xl border border-grey-200 bg-white p-8 text-center">
        <p className="text-[14px] font-semibold text-grey-900">분석 결과가 없어요</p>
        <button
          type="button"
          onClick={() => void run()}
          className="mt-4 inline-flex items-center justify-center rounded-xl bg-toss-blue hover:bg-toss-blue-hover text-white text-[13px] font-semibold px-4 py-2"
        >
          다시 분석하기
        </button>
      </div>
    );
  }

  const counts = data.ai.items.reduce(
    (acc, it) => { acc[it.risk_level]++; return acc; },
    { low: 0, medium: 0, high: 0 } as Record<Risk, number>
  );

  return (
    <div className="space-y-5">
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-toss-blue-bg to-toss-blue-bg-strong p-5 sm:p-6">
        <div className="flex items-start gap-3">
          <span className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-toss-blue text-white shadow-[0_4px_12px_rgba(49,130,246,0.35)]">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M12 2l1.6 4.6L18 8l-4.4 1.4L12 14l-1.6-4.6L6 8l4.4-1.4L12 2z" />
              <path d="M19 14l.7 2.1L22 17l-2.3.9L19 20l-.7-2.1L16 17l2.3-.9L19 14z" />
            </svg>
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-[12px] font-bold tracking-wider text-toss-blue uppercase">AI 요약</p>
            <p className="mt-1 text-[15px] sm:text-[16px] font-semibold leading-relaxed text-grey-900 whitespace-pre-wrap">
              {data.ai.summary}
            </p>
            <p className="mt-3 text-[11px] font-medium text-toss-blue/70">출처: {data.ai.source}</p>
          </div>
        </div>
      </div>

      <div className="flex items-end justify-between gap-3 pt-1">
        <h2 className="text-[18px] font-bold tracking-tight text-grey-900">
          검토 항목 <span className="text-toss-blue">{data.ai.items.length}</span>개
        </h2>
        <div className="flex flex-wrap gap-1.5">
          {counts.high > 0 && (
            <span className="rounded-full bg-danger-bg text-danger text-[11px] font-bold px-2 py-0.5">위반 {counts.high}</span>
          )}
          {counts.medium > 0 && (
            <span className="rounded-full bg-warning-bg text-warning text-[11px] font-bold px-2 py-0.5">주의 {counts.medium}</span>
          )}
          {counts.low > 0 && (
            <span className="rounded-full bg-success-bg text-success text-[11px] font-bold px-2 py-0.5">안전 {counts.low}</span>
          )}
        </div>
      </div>

      <div className="grid gap-3">
        {data.ai.items.map((it, i) => (
          <ViolationCard
            key={i}
            title={it.title}
            risk={it.risk_level}
            message={it.issue}
            lawReference={it.law_reference}
            action={it.action}
          />
        ))}
      </div>
    </div>
  );
}
