import { HttpResponse, http } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { fetchArticle } from "../lib/api/articles";
import { handlers } from "../mocks/handlers";

const server = setupServer(...handlers);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("fetchArticle", () => {
  it("fetchArticle_returns_article_detail_contract", async () => {
    const article = await fetchArticle("article_001");

    expect(article.id).toBe("article_001");
    expect(article.content).toContain("AI 에이전트 기능을 공개");
  });

  it("fetchArticle_throws_not_found_error_with_server_message", async () => {
    const message = "기사를 찾을 수 없습니다";

    server.use(
      http.get("*/api/articles/missing-id", () =>
        HttpResponse.json({ code: "ARTICLE_NOT_FOUND", message }, { status: 404 }),
      ),
    );

    await expect(fetchArticle("missing-id")).rejects.toMatchObject({
      articleId: "missing-id",
      message,
      name: "ArticleNotFoundError",
    });
  });
});
