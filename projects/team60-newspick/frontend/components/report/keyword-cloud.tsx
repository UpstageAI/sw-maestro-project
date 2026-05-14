import type { DailyReportKeyword } from "../../lib/api/reports";

type KeywordCloudProps = {
  keywords: DailyReportKeyword[];
};

const weightClassNames: Record<number, string> = {
  1: "weight-1 text-[11px] opacity-[0.62]",
  2: "weight-2 text-[11px] opacity-[0.62]",
  3: "weight-3 text-[12px] opacity-[0.72]",
  4: "weight-4 text-[12px] opacity-[0.82]",
  5: "weight-5 text-[13px] opacity-90",
  6: "weight-6 text-[14px] opacity-[0.95]",
  7: "weight-7 text-[15px]",
  9: "weight-9 text-[17px]",
};

function weightClassName(weight: number) {
  return weightClassNames[weight] ?? weightClassNames[1];
}

export function KeywordCloud({ keywords }: KeywordCloudProps) {
  return (
    <section>
      <h2 className="mb-3 mt-0 text-[12px] font-[700] tracking-[0.4px] text-muted">
        오늘의 키워드
      </h2>
      <ul
        aria-label="핵심 키워드"
        className="m-0 mb-7 flex list-none flex-wrap items-baseline gap-x-2 gap-y-1.5 p-0"
      >
        {keywords.map((keyword) => (
          <li
            key={keyword.text}
            aria-label={`${keyword.text} 중요도 ${keyword.weight}`}
            className={`rounded-full border border-line bg-surface px-2.5 py-1.5 font-[600] tracking-[-0.1px] text-ink ${weightClassName(keyword.weight)}`}
          >
            {keyword.text}
          </li>
        ))}
      </ul>
    </section>
  );
}
