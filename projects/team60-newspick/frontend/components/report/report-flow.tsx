import type { CSSProperties } from "react";
import type { DailyReportFlowItem, ReportCategory } from "../../lib/api/reports";

type ReportFlowProps = {
  items: DailyReportFlowItem[];
};

const categoryColors: Record<ReportCategory, string> = {
  테크: "#ff8a3d",
  경제: "#4f9cf9",
  정책: "#10b981",
  이슈: "#9b7cf8",
};

function colorForCategory(category: string) {
  return categoryColors[category as ReportCategory] ?? "#ff8a3d";
}

export function ReportFlow({ items }: ReportFlowProps) {
  const visibleItems = items.filter((item) => item.description.trim().length > 0);

  return (
    <section role="region" aria-labelledby="report-flow-heading">
      <div className="mb-3 flex items-center gap-2.5 text-[12px] font-[700] tracking-[0.4px] text-muted">
        <h2 id="report-flow-heading" className="m-0 text-[12px] font-[700] text-muted">
          오늘의 흐름
        </h2>
        <span className="h-px flex-1 bg-line" aria-hidden="true" />
        <span className="text-[11px] font-[600] text-hint">카테고리별 한 줄</span>
      </div>

      <div className="mb-7 grid gap-2.5 rounded-xl border border-line bg-surface px-3.5 py-3">
        {visibleItems.map((item) => {
          const color = colorForCategory(item.category);
          return (
            <div
              key={`${item.category}-${item.description}`}
              className="grid grid-cols-[44px_1fr] items-baseline gap-2.5"
            >
              <span
                className="text-[11px] font-[700] tracking-[0.2px]"
                style={{ color } as CSSProperties}
              >
                {item.category}
              </span>
              <span className="text-[13px] leading-[1.5] text-ink text-balance-pretty">
                {item.description}
              </span>
            </div>
          );
        })}
      </div>
    </section>
  );
}
