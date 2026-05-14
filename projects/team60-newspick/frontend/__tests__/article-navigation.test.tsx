import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, render, screen } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { setupServer } from "msw/node";
import { Suspense, type ReactNode } from "react";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import ArticleDetailPage from "../app/(app)/articles/[articleId]/page";
import FeedPage from "../app/(app)/feed/page";
import { feedArticles } from "../mocks/fixtures/articles";
import { handlers } from "../mocks/handlers";

const server = setupServer(...handlers);

function renderWithQueryClient(children: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(<QueryClientProvider client={queryClient}>{children}</QueryClientProvider>);
}

beforeAll(() => server.listen());
afterEach(() => {
  cleanup();
  server.resetHandlers();
});
afterAll(() => server.close());

describe("article navigation", () => {
  it("clicking_article_card_navigates_to_detail_route", async () => {
    const article = feedArticles[0];
    server.use(http.get("*/api/feed", () => HttpResponse.json({ articles: feedArticles })));

    const { unmount } = renderWithQueryClient(<FeedPage />);

    const titleLink = await screen.findByRole("link", { name: article.title });
    let clicked = false;
    const clickEvent = new MouseEvent("click", { bubbles: true, cancelable: true, button: 0 });
    titleLink.addEventListener(
      "click",
      (event) => {
        clicked = true;
        event.preventDefault();
      },
      { once: true },
    );

    expect(titleLink.getAttribute("href")).toBe(`/articles/${article.id}`);
    expect(titleLink.dispatchEvent(clickEvent)).toBe(false);
    expect(clicked).toBe(true);

    unmount();

    await act(async () => {
      renderWithQueryClient(
        <Suspense fallback={<div>Loading article route</div>}>
          <ArticleDetailPage params={Promise.resolve({ articleId: article.id })} />
        </Suspense>,
      );
    });

    expect(await screen.findByRole("heading", { level: 2, name: article.title })).toBeTruthy();
    expect(screen.getByTestId("article-detail-page").className).toContain("page-enter-detail");
    expect(screen.getByRole("link", { name: "뉴스 목록으로 돌아가기" }).getAttribute("href")).toBe(
      "/feed",
    );
  });
});
