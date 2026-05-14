import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { NewsCard } from "../components/news-card";
import { feedArticles } from "../mocks/fixtures/articles";

const article = feedArticles[0];
const categoryBadgeCases = [
  { category: "테크", background: "bg-brand-50", text: "text-brand-500" },
  { category: "경제", background: "bg-[#eef4ff]", text: "text-economy" },
  { category: "정책", background: "bg-[#ecfdf5]", text: "text-policy" },
  { category: "이슈", background: "bg-[#f3eeff]", text: "text-issue" },
] as const;

describe("NewsCard", () => {
  it("renders_article_summary_card_like_the_m3_prototype", () => {
    render(<NewsCard article={article} />);

    expect(screen.getByText("테크")).toBeTruthy();
    expect(screen.getByText("ZDNet Korea")).toBeTruthy();
    expect(screen.getByText("09:20").className).toContain("font-[700]");
    expect(screen.queryByText("2026.05.12")).toBeNull();
    expect(screen.getByRole("heading", { level: 3, name: article.title })).toBeTruthy();
    const summary = screen.getByText(
      "오픈AI와 앤트로픽이 잇따라 에이전트 기능을 공개하며 단순 대화를 넘어 업무 자동화 시장에 진입하고 있어요. 이메일 작성, 코드 실행, 파일 관리 등 실제 작업을 AI가 직접 처리하는 서비스가 빠르게 확산되고 있습니다.",
    );
    expect(summary.className).toContain("max-w-none");
    expect(summary.className).toContain("text-[13px]");
    expect(summary.className).toContain("font-[600]");
    expect(summary.className).toContain("leading-[1.55]");
    expect(screen.getByText("AI 에이전트")).toBeTruthy();
    expect(screen.getByText("오픈AI")).toBeTruthy();
    expect(screen.getByText("자동화")).toBeTruthy();
    const titleLink = screen.getByRole("link", { name: article.title });
    expect(titleLink).toBeTruthy();
    expect(titleLink.getAttribute("href")).toBe("/articles/article_001");
    const detailLink = screen.getByRole("link", { name: `${article.title} 상세 보기` });
    expect(detailLink).toBeTruthy();
    expect(detailLink.getAttribute("href")).toBe("/articles/article_001");
    expect(detailLink.className).toContain("bg-brand-50");
    expect(detailLink.className).toContain("text-brand-500");
    expect(detailLink.className).toContain("font-[800]");
  });

  it("prefers_summary_preview_over_summary_array", () => {
    const friendlyPreview =
      "정부가 AI 반도체 지원책을 확대하고 있어요. 기업 투자가 늘면서 기술 경쟁도 더 빨라지고 있어요.";

    render(
      <NewsCard
        article={{
          ...article,
          summaryPreview: friendlyPreview,
          summary: ["Fallback summary"],
        }}
      />,
    );

    const summary = screen.getByText(friendlyPreview);
    expect(summary).toBeTruthy();
    expect(summary.className).not.toContain("line-clamp");
    expect(summary.className).not.toContain("truncate");
    expect(summary.className).toContain("break-keep");
    expect(screen.queryByText("Fallback summary")).toBeNull();
  });

  it("renders_utc_published_at_values_in_seoul_time", () => {
    render(<NewsCard article={{ ...article, publishedAt: "2026-05-13T06:36:47Z" }} />);

    expect(screen.getByText("15:36")).toBeTruthy();
    expect(screen.queryByText("06:36")).toBeNull();
  });

  it.each(categoryBadgeCases)(
    "uses_the_prototype_category_badge_color_for_$category",
    ({ category, background, text }) => {
      render(<NewsCard article={{ ...article, category }} />);

      const badge = screen.getByText(category);
      expect(badge.className).toContain(background);
      expect(badge.className).toContain(text);
    },
  );
});
