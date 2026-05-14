import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ChatArticleCards } from "../components/chat/chat-article-cards";

const articleSummaries = [
  {
    id: "article_001",
    title: "AI가 바꿀 뉴스 서비스",
    source: "Example News",
    publishedAt: "2026-05-12T09:00:00+09:00",
  },
  {
    id: "article_002",
    title: "검색 경험의 다음 장면",
    source: "Second News",
    publishedAt: "2026-05-12T15:20:00Z",
  },
];

describe("ChatArticleCards", () => {
  it("chat_article_cards_render_article_summary_links", () => {
    render(<ChatArticleCards articles={articleSummaries} />);

    const list = screen.getByRole("list", { name: "참고 기사" });
    expect(within(list).getAllByRole("listitem")).toHaveLength(2);

    const link = screen.getByRole("link", { name: /AI가 바꿀 뉴스 서비스/ });
    expect(link.getAttribute("href")).toBe("/articles/article_001");
    expect(screen.getByText("Example News")).toBeTruthy();
    expect(screen.getByText("2026.05.12")).toBeTruthy();
    expect(screen.getByText("2026.05.13")).toBeTruthy();
  });
});
