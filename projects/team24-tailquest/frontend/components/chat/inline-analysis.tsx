"use client";

import { Icon } from "@/components/chrome/icon";
import { cn } from "@/lib/utils";
import type { AnalysisNote, Severity } from "@/lib/api";

const SEVERITY_TONE: Record<Severity, string> = {
  critical: "border-rausch text-rausch",
  moderate: "border-ink text-ink",
  minor: "border-hairline text-muted",
};

const SEVERITY_LABEL: Record<Severity, string> = {
  critical: "핵심 누락",
  moderate: "보통",
  minor: "경미",
};

interface Props {
  notes: AnalysisNote[];
}

/** Compact analysis card slipped into the conversation right after a user turn.
 *  Detailed view (full notes + history) lives in the right rail. */
export function InlineAnalysis({ notes }: Props) {
  return (
    <div className="flex gap-md">
      <div className="shrink-0">
        <span className="h-10 w-10 rounded-full bg-canvas border border-hairline flex items-center justify-center text-ink">
          <Icon name="analytics" size={20} />
        </span>
      </div>
      <div className="flex-1 min-w-0 max-w-[80%]">
        <div className="flex items-center gap-sm mb-sm">
          <span className="text-caption-sm text-muted">즉시 분석</span>
        </div>

        <div className="rounded-md border border-hairline bg-surface-soft p-md">
          <p className="text-caption-sm text-muted mb-sm">
            이 답변에서 짚을 부분 {notes.length}건 · 자세한 내용은 우측 패널 참조
          </p>
          <ul className="flex flex-col gap-1">
            {notes.map((n, i) => (
              <li
                key={i}
                className={cn(
                  "rounded-sm border-l-2 pl-sm py-1",
                  SEVERITY_TONE[n.severity],
                )}
              >
                <div className="flex items-baseline gap-sm flex-wrap">
                  <span className="text-body-sm text-ink font-semibold">
                    {n.label}
                  </span>
                  <span className="text-caption-sm text-muted">
                    {SEVERITY_LABEL[n.severity]}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
