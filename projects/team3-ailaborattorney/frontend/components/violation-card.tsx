import RiskBadge from "./risk-badge";

type Risk = "low" | "medium" | "high";

export interface ViolationCardProps {
  title: string;
  risk: Risk;
  message: string;
  lawReference?: string;
  action?: string;
}

export default function ViolationCard(p: ViolationCardProps) {
  return (
    <article className="rounded-2xl bg-white border border-grey-200 p-5 hover:border-grey-300 transition-colors">
      <header className="flex items-start justify-between gap-3">
        <h3 className="text-[16px] font-bold tracking-tight text-grey-900 leading-snug">{p.title}</h3>
        <div className="shrink-0 pt-0.5">
          <RiskBadge level={p.risk} />
        </div>
      </header>

      <p className="mt-2.5 text-[14px] leading-6 text-grey-700 whitespace-pre-wrap">{p.message}</p>

      {p.lawReference && (
        <div className="mt-3 inline-flex items-center gap-1.5 rounded-full border border-grey-200 bg-grey-50 px-2.5 py-1 text-[11px] font-medium text-grey-600">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
          </svg>
          {p.lawReference}
        </div>
      )}

      {p.action && (
        <div className="mt-4 flex items-start gap-2.5 rounded-xl bg-toss-blue-bg p-3">
          <span className="mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-toss-blue text-white">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M12 2l1.6 4.6L18 8l-4.4 1.4L12 14l-1.6-4.6L6 8l4.4-1.4L12 2z" />
            </svg>
          </span>
          <div className="min-w-0">
            <p className="text-[12px] font-bold text-toss-blue">이렇게 해보세요</p>
            <p className="mt-0.5 text-[13px] leading-5 text-grey-800">{p.action}</p>
          </div>
        </div>
      )}
    </article>
  );
}
