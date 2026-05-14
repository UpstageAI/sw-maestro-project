import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, render, screen } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { setupServer } from "msw/node";
import { Suspense, type ReactNode } from "react";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import ArticleDetailPage from "../../app/(app)/articles/[articleId]/page";
import { fetchArticle, type ArticleDetail } from "../../lib/api/articles";
import articleSchema from "../../../docs/contracts/json-schemas/article.json";
import { articleDetails } from "../../mocks/fixtures/articles";
import { handlers } from "../../mocks/handlers";

const server = setupServer(...handlers);
const requiredArticleFields = articleSchema.required;

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

function requiredFieldValues(article: ArticleDetail) {
  const articleRecord = article as Record<string, unknown>;

  return Object.fromEntries(requiredArticleFields.map((field) => [field, articleRecord[field]]));
}

function expectArticleMatchesContractSchema(article: ArticleDetail) {
  const articleRecord = article as Record<string, unknown>;

  for (const field of requiredArticleFields) {
    expect(articleRecord[field], `${field} is required`).not.toBeUndefined();
  }

  expect(typeof article.id).toBe("string");
  expect(typeof article.url).toBe("string");
  expect(typeof article.title).toBe("string");
  expect(typeof article.source).toBe("string");
  expect(["테크", "경제", "정책", "이슈"]).toContain(article.category);
  expect(Number.isNaN(Date.parse(article.publishedAt))).toBe(false);
  expect(["collected", "summarized", "review_required", "skip", "description_only"]).toContain(
    article.status,
  );

  if (article.summary !== undefined) {
    expect(Array.isArray(article.summary)).toBe(true);
  }

  if (article.keywords !== undefined) {
    expect(Array.isArray(article.keywords)).toBe(true);
  }

  if (article.rawTextStatus !== undefined) {
    expect(["full_text", "description_only", null]).toContain(article.rawTextStatus);
  }

  if (article.importanceScore !== undefined && article.importanceScore !== null) {
    expect(Number.isInteger(article.importanceScore)).toBe(true);
    expect(article.importanceScore).toBeGreaterThanOrEqual(1);
    expect(article.importanceScore).toBeLessThanOrEqual(10);
  }

  if (article.quiz !== undefined) {
    expect(Array.isArray(article.quiz)).toBe(true);
  }
}

async function expectLiveArticleContractIfEnabled() {
  if (process.env.RUN_LIVE_CONTRACT !== "true") {
    return;
  }

  const feBaseUrl = process.env.FE_BASE_URL ?? "http://localhost:3000";
  const beBaseUrl = process.env.BE_BASE_URL ?? "http://localhost:8080";
  const aiBaseUrl = process.env.AI_BASE_URL ?? "http://localhost:8000";

  expect(() => new URL(feBaseUrl)).not.toThrow();
  expect(() => new URL(beBaseUrl)).not.toThrow();
  expect(() => new URL(aiBaseUrl)).not.toThrow();

  server.close();
  try {
    const liveArticle = await fetchArticle("article_001", beBaseUrl);

    expectArticleMatchesContractSchema(liveArticle);
    expect(Object.keys(requiredFieldValues(liveArticle))).toEqual(requiredArticleFields);
  } finally {
    server.listen();
  }
}

beforeAll(() => server.listen());
afterEach(() => {
  cleanup();
  server.resetHandlers();
});
afterAll(() => server.close());

describe("article detail contract", () => {
  it("article_detail_contract_fixture_matches_rendered_page", async () => {
    const fixtureArticle = articleDetails.article_001;
    const contractEndpointArticle = {
      ...fixtureArticle,
      source: "Contract API",
    };
    const contractBaseUrl = "https://contract.newspick.test";
    const firstContentParagraph = fixtureArticle.content.split("\n\n")[0];

    server.use(
      http.get(`${contractBaseUrl}/api/articles/article_001`, () =>
        HttpResponse.json(contractEndpointArticle),
      ),
    );

    expectArticleMatchesContractSchema(fixtureArticle);

    const mswArticle = await fetchArticle("article_001", contractBaseUrl);

    expect(requiredFieldValues(mswArticle)).toEqual(requiredFieldValues(contractEndpointArticle));

    await act(async () => {
      renderWithQueryClient(
        <Suspense fallback={<div>상세 경로 준비 중</div>}>
          <ArticleDetailPage params={Promise.resolve({ articleId: "article_001" })} />
        </Suspense>,
      );
    });

    expect(
      await screen.findByRole("heading", {
        level: 2,
        name: fixtureArticle.title,
      }),
    ).toBeTruthy();
    expect(screen.getByText(fixtureArticle.source)).toBeTruthy();
    expect(screen.getAllByText(firstContentParagraph).length).toBeGreaterThan(0);

    await expectLiveArticleContractIfEnabled();
  });
});
