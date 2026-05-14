"use client";

import Link from "next/link";
import { use } from "react";
import { BottomNav } from "../../../../components/bottom-nav";
import { InlineQuiz } from "../../../../components/inline-quiz";
import { PhoneFrame } from "../../../../components/phone-frame";
import {
  ArticleNotFoundError,
  useArticle,
  type ArticleDetail,
} from "../../../../lib/api/articles";
import { categoryBadgeClass } from "../../../../lib/categories";
import { formatSeoulTime } from "../../../../lib/datetime";

type ArticleDetailPageProps = {
  params: Promise<{ articleId: string }>;
};

const SOURCE_SUMMARY_COPY = "AI가 원문을 읽고 핵심만 정리했어요";
const DETAIL_TEXT_MAX_LENGTH = 280;
const IMPORTANCE_TEXT_MAX_LENGTH = 220;

function formatPublishedLabel(publishedAt: string) {
  const time = formatSeoulTime(publishedAt);

  if (time === publishedAt) {
    return publishedAt;
  }

  return `오늘 ${time}`;
}

function BackToFeedLink() {
  return (
    <Link
      href="/feed"
      aria-label="뉴스 목록으로 돌아가기"
      className="absolute left-0 top-0 z-10 grid h-[38px] w-[38px] place-items-center rounded-[14px] bg-chip text-[32px] leading-none text-ink transition-colors active:bg-line"
    >
      ‹
    </Link>
  );
}

function SectionLabel({ children }: { children: string }) {
  return (
    <p className="m-0 inline-flex items-center gap-[7px] text-[13px] font-[950] leading-[1.2] text-brand-500">
      <span className="h-1.5 w-1.5 rounded-full bg-brand-500" aria-hidden="true" />
      {children}
    </p>
  );
}

function ArticleDetailLoading() {
  return (
    <article role="status" aria-label="기사 불러오는 중" className="grid gap-[18px] pb-7">
      <header className="grid gap-3 pb-1">
        <div className="grid grid-cols-[auto_1fr_auto] items-center gap-2">
          <span
            data-testid="article-detail-skeleton"
            className="skeleton-shimmer h-6 w-10 rounded-full"
          />
          <span
            data-testid="article-detail-skeleton"
            className="skeleton-shimmer h-3 w-24 rounded-full"
          />
          <span
            data-testid="article-detail-skeleton"
            className="skeleton-shimmer h-3 w-16 rounded-full"
          />
        </div>

        <div className="grid gap-2">
          <span
            data-testid="article-detail-skeleton"
            className="skeleton-shimmer h-8 w-[92%] rounded-full"
          />
          <span
            data-testid="article-detail-skeleton"
            className="skeleton-shimmer h-8 w-[78%] rounded-full"
          />
        </div>

        <div className="flex flex-wrap gap-1.5">
          <span
            data-testid="article-detail-skeleton"
            className="skeleton-shimmer h-6 w-[70px] rounded-full"
          />
          <span
            data-testid="article-detail-skeleton"
            className="skeleton-shimmer h-6 w-[52px] rounded-full"
          />
          <span
            data-testid="article-detail-skeleton"
            className="skeleton-shimmer h-6 w-[58px] rounded-full"
          />
        </div>

        <div className="flex min-h-[42px] items-center justify-between gap-2.5 rounded-[14px] border border-line bg-white px-[13px]">
          <span
            data-testid="article-detail-skeleton"
            className="skeleton-shimmer h-3 w-28 rounded-full"
          />
          <span
            data-testid="article-detail-skeleton"
            className="skeleton-shimmer h-3 w-14 rounded-full"
          />
        </div>
      </header>

      <section className="grid gap-3">
        <div className="inline-flex items-center gap-[7px]">
          <span className="h-1.5 w-1.5 rounded-full bg-brand-500" />
          <span
            data-testid="article-detail-skeleton"
            className="skeleton-shimmer h-3 w-20 rounded-full"
          />
        </div>
        <ol className="m-0 grid list-none gap-3.5 p-0">
          {[0, 1, 2].map((item) => (
            <li key={item} className="grid grid-cols-[28px_1fr] items-start gap-[11px]">
              <span className="grid h-7 w-7 place-items-center rounded-full bg-brand-50">
                <span
                  data-testid="article-detail-skeleton"
                  className="skeleton-shimmer h-2.5 w-2.5 rounded-full"
                />
              </span>
              <div className="mt-0.5 grid gap-2">
                <span
                  data-testid="article-detail-skeleton"
                  className="skeleton-shimmer h-3 w-full rounded-full"
                />
                <span
                  data-testid="article-detail-skeleton"
                  className="skeleton-shimmer h-3 w-[86%] rounded-full"
                />
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="grid gap-3 border-l-[3px] border-brand-500 bg-[linear-gradient(90deg,rgba(255,138,61,0.09),rgba(255,255,255,0))] py-[15px] pl-[15px]">
        <div className="inline-flex items-center gap-[7px]">
          <span className="h-1.5 w-1.5 rounded-full bg-brand-500" />
          <span
            data-testid="article-detail-skeleton"
            className="skeleton-shimmer h-3 w-16 rounded-full"
          />
        </div>
        <span
          data-testid="article-detail-skeleton"
          className="skeleton-shimmer h-3 w-[92%] rounded-full"
        />
        <span
          data-testid="article-detail-skeleton"
          className="skeleton-shimmer h-3 w-[74%] rounded-full"
        />
      </section>
    </article>
  );
}

function getArticleErrorCopy(error: unknown) {
  if (error instanceof ArticleNotFoundError) {
    return {
      title: "요청한 기사를 찾을 수 없어요",
      message: error.message,
    };
  }

  return {
    title: "기사를 불러오지 못했어요",
    message: "잠시 후 다시 시도해주세요.",
  };
}

function ArticleDetailError({ error }: { error: unknown }) {
  const copy = getArticleErrorCopy(error);

  return (
    <section role="alert" className="rounded-card border border-line bg-surface p-5">
      <p className="text-[15px] font-extrabold text-ink">{copy.title}</p>
      <p className="mt-2 text-[13px] font-semibold leading-[1.5] text-muted">
        {copy.message}
      </p>
    </section>
  );
}

function normalizeDetailCopy(value: string | null | undefined, maxLength = DETAIL_TEXT_MAX_LENGTH) {
  const text = value?.replace(/\s+/g, " ").trim() ?? "";

  if (!text || looksLikeRawDetailText(text)) {
    return "";
  }

  return trimDetailText(text, maxLength);
}

function looksLikeRawDetailText(text: string) {
  if (text.length > 500) {
    return true;
  }
  if (/```|<\/?[a-zA-Z][^>]*>|https?:\/\//.test(text)) {
    return true;
  }
  if (/^\s*[\[{]/.test(text) || /"(content|rawText|raw_text|html|body)"\s*:/.test(text)) {
    return true;
  }
  return /\b(function|const|let|var)\b/.test(text);
}

function trimDetailText(text: string, maxLength: number) {
  if (text.length <= maxLength) {
    return text;
  }

  const sentences = text.match(/[^.!?。！？]+[.!?。！？]/g)?.map((sentence) => sentence.trim());
  const trimmed = sentences?.slice(0, 2).join(" ").trim();
  if (trimmed && trimmed.length <= maxLength) {
    return trimmed;
  }

  return text.slice(0, maxLength).trimEnd();
}

function normalizeContextLabel(value: string) {
  const label = value.replace(/\s+/g, " ").trim();
  if (!label || label.length > 8 || looksLikeRawDetailText(label)) {
    return "배경";
  }
  return label;
}

function buildContextItems(article: ArticleDetail) {
  const fallbackItems = article.context ? [{ label: "배경", text: article.context }] : [];
  const sourceItems =
    article.contextItems && article.contextItems.length > 0
      ? article.contextItems
      : fallbackItems;

  const normalizedItems = sourceItems
    .map((item) => ({
      label: normalizeContextLabel(item.label),
      text: normalizeDetailCopy(item.text),
    }))
    .filter((item) => item.text);

  if (normalizedItems.length > 0) {
    return normalizedItems;
  }

  const fallback = buildFriendlyBackground(article);
  return fallback ? [{ label: "배경", text: fallback }] : [];
}

function buildFriendlyBackground(article: ArticleDetail) {
  const background =
    normalizeDetailCopy(article.summary?.[0], 140) ||
    normalizeDetailCopy(article.content, 140);

  if (!background) {
    return "";
  }

  const topics = article.keywords?.filter(Boolean).slice(0, 2) ?? [];
  const prefix =
    topics.length > 0
      ? `${topics.join("·")}는 이 기사를 이해하는 핵심 배경이에요.`
      : `${article.title}을 이해하려면 기사에서 다룬 배경을 함께 보면 좋아요.`;

  return trimDetailText(`${prefix} ${background}`, DETAIL_TEXT_MAX_LENGTH);
}

function ArticleDetail({ article }: { article: ArticleDetail }) {
  const categoryClass = categoryBadgeClass(article.category);
  const importance = normalizeDetailCopy(article.importance, IMPORTANCE_TEXT_MAX_LENGTH);
  const keywords = article.keywords?.filter(Boolean).slice(0, 3) ?? [];
  const contextItems = buildContextItems(article);

  return (
    <article className="grid gap-[18px] pb-7">
      <header className="grid gap-3 pb-1">
        <div
          role="group"
          aria-label="기사 메타데이터"
          className="grid grid-cols-[auto_1fr_auto] items-center gap-2 text-[12px] font-[750] text-hint"
        >
          <span
            className={`inline-flex min-h-6 items-center rounded-full px-[9px] font-[850] ${categoryClass}`}
          >
            {article.category}
          </span>
          <span className="min-w-0 truncate">{article.source}</span>
          <time className="whitespace-nowrap" dateTime={article.publishedAt}>
            {formatPublishedLabel(article.publishedAt)}
          </time>
        </div>
        <h2 className="m-0 text-[26px] font-[900] leading-[1.28] text-ink break-keep">
          {article.title}
        </h2>

        {keywords.length > 0 ? (
          <div aria-label="핵심 키워드" className="-mt-0.5 flex flex-wrap gap-1.5">
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

        <div className="flex min-h-[42px] items-center justify-between gap-2.5 rounded-[14px] border border-line bg-white px-[13px] text-[12px] font-[750] text-hint">
          <span>{SOURCE_SUMMARY_COPY}</span>
          <a
            href={article.url ?? "#"}
            className="whitespace-nowrap font-[850] text-brand-500 no-underline"
          >
            원문 보기
          </a>
        </div>
      </header>

      {article.summary?.length ? (
        <section className="grid gap-3">
          <SectionLabel>핵심만 보기</SectionLabel>
          <ol className="m-0 grid list-none gap-3.5 p-0 break-keep">
            {article.summary.map((summary, index) => (
              <li key={summary} className="grid grid-cols-[28px_1fr] items-start gap-[11px]">
                <span className="grid h-7 w-7 place-items-center rounded-full bg-brand-50 text-[13px] font-[900] leading-none text-brand-500">
                  {index + 1}
                </span>
                <p className="m-0 mt-0.5 max-w-none text-[13px] font-[650] leading-[1.55] text-muted break-keep">
                  {summary}
                </p>
              </li>
            ))}
          </ol>
        </section>
      ) : null}

      {importance ? (
        <section className="grid gap-3 border-l-[3px] border-brand-500 bg-[linear-gradient(90deg,rgba(255,138,61,0.09),rgba(255,255,255,0))] py-[15px] pl-[15px]">
          <SectionLabel>왜 중요해?</SectionLabel>
          <p className="m-0 max-w-none text-[14px] font-[600] leading-[1.6] text-muted break-keep">
            {importance}
          </p>
        </section>
      ) : null}

      {contextItems.length > 0 ? (
        <section className="grid gap-3">
          <SectionLabel>조금 더 알기</SectionLabel>
          <div className="grid border-t border-line">
            {contextItems.map((item) => (
              <div
                key={item.label}
                className="grid grid-cols-[42px_1fr] gap-[11px] border-b border-line py-[13px]"
              >
                <strong className="text-[13px] font-[900] leading-[1.25] text-ink">
                  {item.label}
                </strong>
                <span className="text-[13px] font-[650] leading-[1.5] text-muted break-keep">
                  {item.text}
                </span>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {article.quiz?.length ? <InlineQuiz quiz={article.quiz} /> : null}
    </article>
  );
}

function ArticleDetailContent({ articleId }: { articleId: string }) {
  const { data, error, isLoading } = useArticle(articleId);

  return (
    <div
      role="region"
      aria-label="기사 상세 본문"
      aria-busy={isLoading}
      className="min-h-[360px]"
    >
      {isLoading ? <ArticleDetailLoading /> : null}
      {!isLoading && (error || !data) ? <ArticleDetailError error={error} /> : null}
      {!isLoading && data ? <ArticleDetail article={data} /> : null}
    </div>
  );
}

export default function ArticleDetailPage({ params }: ArticleDetailPageProps) {
  const { articleId } = use(params);

  return (
    <main className="flex min-h-dvh items-center justify-center bg-bg px-5 py-6 text-ink">
      <PhoneFrame>
        <div className="min-h-0 flex-1 overflow-y-auto px-[22px] pb-[18px] pt-[18px]">
          <div data-testid="article-detail-page" className="page-enter-detail relative pt-[46px]">
            <BackToFeedLink />
            <ArticleDetailContent articleId={articleId} />
          </div>
        </div>
        <BottomNav active="home" />
      </PhoneFrame>
    </main>
  );
}
