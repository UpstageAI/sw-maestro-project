import type { CSSProperties } from "react";
import type { DailyReportTimelineItem, ReportCategory } from "../../lib/api/reports";

type ReportTimelineProps = {
  items: DailyReportTimelineItem[];
};

const categoryColors: Record<ReportCategory, string> = {
  테크: "#ff8a3d",
  경제: "#4f9cf9",
  정책: "#10b981",
  이슈: "#9b7cf8",
};

function categoryColor(category: ReportCategory) {
  return categoryColors[category];
}

function SourceDots({ count, color }: { count: number; color: string }) {
  return (
    <span className="inline-flex gap-0.5" aria-hidden="true">
      {Array.from({ length: count }).map((_, index) => (
        <span
          key={index}
          className="h-[5px] w-[5px] rounded-full"
          style={{ backgroundColor: color }}
        />
      ))}
    </span>
  );
}

export function ReportTimeline({ items }: ReportTimelineProps) {
  return (
    <section>
      <div className="mb-3.5 flex items-center gap-2.5 text-[12px] font-[700] tracking-[0.4px] text-muted">
        <span>가장 많이 다뤄진 순</span>
        <span className="h-px flex-1 bg-line" aria-hidden="true" />
        <span className="text-[11px] font-[600] text-hint">{items.length}건</span>
      </div>

      <ol aria-label="주요 흐름" className="relative m-0 mb-7 list-none p-0 pl-7">
        <span
          className="absolute bottom-1.5 left-[9px] top-1.5 w-0.5 rounded-full bg-[linear-gradient(to_bottom,var(--color-line),var(--color-line)_70%,transparent)]"
          aria-hidden="true"
        />

        {items.map((item, index) => {
          const color = categoryColor(item.category);
          const isHeadline = index === 0;
          const nodeStyle: CSSProperties = isHeadline
            ? {
                backgroundColor: color,
                boxShadow: `0 0 0 3px #ffffff, 0 0 0 6px ${color}2e`,
              }
            : { backgroundColor: color, boxShadow: "0 0 0 3px #ffffff" };

          return (
            <li
              key={item.articleId}
              className={`relative ${index === items.length - 1 ? "mb-0" : "mb-[18px]"}`}
            >
              <span
                className={`absolute rounded-full ${
                  isHeadline
                    ? "left-[-27px] top-1 h-4 w-4"
                    : "left-[-24px] top-1.5 h-2.5 w-2.5"
                }`}
                style={nodeStyle}
                aria-hidden="true"
              />
              <span className="mb-2 block text-[11px] font-[600] tracking-[0.2px] text-hint">
                <span>{item.timeLabel}</span>
                {isHeadline ? <span> · 가장 많이 다뤄진 이슈</span> : null}
              </span>

              <article
                className={
                  isHeadline
                    ? "rounded-[14px] border border-line bg-surface px-4 pb-3.5 pt-4"
                    : "rounded-xl border border-line bg-surface px-3.5 py-3"
                }
              >
                <p
                  className="mb-1.5 mt-0 text-[11px] font-[700] tracking-[0.2px]"
                  style={{ color }}
                >
                  ● {item.category}
                </p>
                {isHeadline ? (
                  <>
                    <h3 className="m-0 mb-1.5 text-[17px] font-[700] leading-[1.4] tracking-[-0.3px] text-ink text-balance-pretty">
                      {item.title}
                    </h3>
                    {item.summary ? (
                      <p className="m-0 max-w-none text-[13px] leading-[1.5] text-muted">
                        {item.summary}
                      </p>
                    ) : null}
                    <span className="mt-2.5 inline-flex items-center gap-[5px] text-[11px] font-[700] text-muted">
                      <SourceDots count={item.sourceCount} color={color} />
                      {item.sourceCount}개 매체가 동시에 보도
                    </span>
                  </>
                ) : (
                  <>
                    <h3 className="m-0 text-[14px] font-[600] leading-[1.45] tracking-[-0.2px] text-ink">
                      {item.title}
                    </h3>
                    <p className="m-0 mt-1 text-[11px] font-[600] text-hint">
                      {item.sourceCount}개 매체 보도
                    </p>
                  </>
                )}
              </article>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
