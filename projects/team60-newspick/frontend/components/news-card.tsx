import Link from "next/link";
import type { ArticleSummary } from "../lib/api/feed";
import { categoryBadgeClass } from "../lib/categories";
import { formatSeoulTime } from "../lib/datetime";

type NewsCardProps = {
  article: ArticleSummary;
};

export function NewsCard({ article }: NewsCardProps) {
  const summary = article.summaryPreview?.trim() || article.summary?.filter(Boolean).join(" ");
  const keywords = article.keywords?.filter(Boolean).slice(0, 3) ?? [];
  const detailHref = `/articles/${article.id}`;
  const badgeClass = categoryBadgeClass(article.category);

  return (
    <article className="grid gap-3 rounded-[20px] border border-line bg-surface p-[18px] shadow-[0_10px_24px_rgba(25,31,40,0.05)]">
      <div className="grid grid-cols-[auto_1fr_auto] items-center gap-2">
        <span
          className={`inline-flex min-h-6 items-center rounded-full px-[9px] text-[12px] font-[850] ${badgeClass}`}
        >
          {article.category}
        </span>
        <span className="min-w-0 truncate text-[12px] font-[750] leading-[1.2] text-hint">
          {article.source}
        </span>
        <time
          dateTime={article.publishedAt}
          className="text-[12px] font-[700] leading-normal text-hint"
        >
          {formatSeoulTime(article.publishedAt)}
        </time>
      </div>

      <h3 className="text-[18px] font-[850] leading-[1.38] text-ink break-keep">
        <Link
          href={detailHref}
          className="rounded-sm hover:text-brand-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
        >
          {article.title}
        </Link>
      </h3>

      {summary ? (
        <p className="m-0 max-w-none text-[13px] font-[600] leading-[1.55] text-muted break-keep">
          {summary}
        </p>
      ) : null}

      {keywords.length > 0 ? (
        <div aria-label="핵심 키워드" className="flex flex-wrap gap-1.5">
          {keywords.map((keyword) => (
            <span
              key={keyword}
              className="inline-flex min-h-6 items-center rounded-full bg-chip px-2 text-[11px] font-[750] text-muted"
            >
              {keyword}
            </span>
          ))}
        </div>
      ) : null}

      <div className="grid grid-cols-2 gap-2">
        <Link
          href={detailHref}
          aria-label={`${article.title} 상세 보기`}
          className="col-span-2 flex min-h-[38px] items-center justify-center rounded-xl border border-transparent bg-brand-50 text-[13px] font-[800] text-brand-500 active:scale-[0.98]"
        >
          상세 보기
        </Link>
      </div>
    </article>
  );
}
