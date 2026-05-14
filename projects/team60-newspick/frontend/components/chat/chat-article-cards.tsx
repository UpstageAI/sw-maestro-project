import Link from "next/link";
import { formatSeoulDate } from "../../lib/datetime";
import type { ChatArticleSummary } from "./chat-stream";

type ChatArticleCardsProps = {
  articles: ChatArticleSummary[];
};

function hasRequiredFields(article: ChatArticleSummary) {
  return Boolean(article.id && article.title && article.source && article.publishedAt);
}

export function ChatArticleCards({ articles }: ChatArticleCardsProps) {
  const validArticles = articles.filter((article) => {
    const isValid = hasRequiredFields(article);

    if (!isValid) {
      console.error("Invalid chat article summary", article);
    }

    return isValid;
  });

  if (validArticles.length === 0) {
    return null;
  }

  return (
    <ul aria-label="참고 기사" className="mt-1 flex list-none flex-col gap-2 p-0" role="list">
      {validArticles.map((article) => (
        <li key={article.id}>
          <Link
            className="block w-full rounded-xl border border-line bg-bg px-3 py-2.5 text-left no-underline active:border-brand-500/25 active:bg-brand-50"
            href={`/articles/${article.id}`}
          >
            <span className="mb-1 block text-[11px] font-[700] text-brand-500">참고 기사</span>
            <span className="m-0 block text-[13px] font-[600] leading-[1.45] text-ink break-keep">
              {article.title}
            </span>
            <span className="mt-1 flex items-center gap-1 text-[11px] text-hint">
              <span>{article.source}</span>
              <span aria-hidden="true">·</span>
              <span>{formatSeoulDate(article.publishedAt)}</span>
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
