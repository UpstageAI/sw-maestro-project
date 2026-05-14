import { useQuery } from "@tanstack/react-query";
import { apiBase as defaultApiBase } from "./base";
import type { ArticleSummary } from "./feed";

export type ArticleDetail = ArticleSummary & {
  content: string;
  url?: string;
  rawText?: string | null;
  rawTextStatus?: "full_text" | "description_only" | null;
  importance?: string | null;
  context?: string | null;
  contextItems?: {
    label: string;
    text: string;
  }[];
  quiz?: {
    id: string;
    question: string;
    answer: boolean;
    correctTitle: string;
    wrongTitle: string;
    explanation: string;
  }[];
  importanceScore?: number | null;
};

type ArticleErrorResponse = {
  code?: string;
  error?: string;
  message?: string;
};

export class ArticleNotFoundError extends Error {
  constructor(
    readonly articleId: string,
    message = "기사를 찾을 수 없습니다",
  ) {
    super(message);
    this.name = "ArticleNotFoundError";
  }
}

export function articleQueryKey(articleId: string) {
  return ["article", articleId] as const;
}

function articleApiUrl(apiBase: string, articleId: string) {
  return `${apiBase.replace(/\/$/, "")}/api/articles/${articleId}`;
}

export async function fetchArticle(
  articleId: string,
  apiBase = defaultApiBase(),
): Promise<ArticleDetail> {
  const response = await fetch(articleApiUrl(apiBase, articleId));

  if (response.status === 404) {
    const body = (await response.json().catch(() => null)) as ArticleErrorResponse | null;
    throw new ArticleNotFoundError(articleId, body?.message);
  }

  if (!response.ok) {
    throw new Error("Failed to fetch article");
  }

  return response.json() as Promise<ArticleDetail>;
}

export function useArticle(articleId: string) {
  return useQuery({
    queryKey: articleQueryKey(articleId),
    queryFn: () => fetchArticle(articleId),
  });
}
