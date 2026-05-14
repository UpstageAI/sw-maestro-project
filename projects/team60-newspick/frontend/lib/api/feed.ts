import { categoryQuery, type CategoryId } from "../categories";
import { apiUrl } from "./base";

export type ArticleSummary = {
  id: string;
  title: string;
  source: string;
  category: "테크" | "경제" | "정책" | "이슈";
  publishedAt: string;
  summaryPreview?: string | null;
  summary?: string[];
  keywords?: string[];
  status: "collected" | "summarized" | "review_required" | "skip" | "description_only";
};

export type FeedResponse = {
  articles: ArticleSummary[];
};

export function feedUrl(categories: readonly CategoryId[] = []) {
  const url = new URL(apiUrl("/api/feed"));
  if (categories.length > 0) {
    url.searchParams.set("categories", categoryQuery(categories));
  }

  return url.toString();
}

export async function fetchFeed(categories: readonly CategoryId[] = []): Promise<FeedResponse> {
  const response = await fetch(feedUrl(categories));

  if (!response.ok) {
    throw new Error("Failed to fetch feed");
  }

  return response.json() as Promise<FeedResponse>;
}
