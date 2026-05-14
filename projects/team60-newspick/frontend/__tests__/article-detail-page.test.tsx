import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitForElementToBeRemoved,
} from "@testing-library/react";
import { HttpResponse, delay, http } from "msw";
import { setupServer } from "msw/node";
import { Suspense, type ReactNode } from "react";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import ArticleDetailPage from "../app/(app)/articles/[articleId]/page";
import { articleDetails } from "../mocks/fixtures/articles";
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

describe("ArticleDetailPage", () => {
  it("article_detail_page_shows_loading_skeleton_before_content", async () => {
    server.use(
      http.get("*/api/articles/:articleId", async () => {
        await delay(500);
        return HttpResponse.json(articleDetails.article_001);
      }),
    );

    await act(async () => {
      renderWithQueryClient(
        <Suspense fallback={<div>상세 경로 준비 중</div>}>
          <ArticleDetailPage params={Promise.resolve({ articleId: "article_001" })} />
        </Suspense>,
      );
    });

    const contentRegion = screen.getByRole("region", { name: "기사 상세 본문" });
    const loadingStatus = screen.getByRole("status", { name: "기사 불러오는 중" });

    expect(contentRegion.getAttribute("aria-busy")).toBe("true");
    expect(loadingStatus).toBeTruthy();
    expect(screen.getAllByTestId("article-detail-skeleton").length).toBeGreaterThanOrEqual(12);

    await waitForElementToBeRemoved(() =>
      screen.queryByRole("status", { name: "기사 불러오는 중" }),
    );

    expect(contentRegion.getAttribute("aria-busy")).toBe("false");
    expect(
      await screen.findByRole("heading", {
        level: 2,
        name: articleDetails.article_001.title,
      }),
    ).toBeTruthy();
  });

  it("article_detail_page_shows_not_found_message_for_404", async () => {
    const message = "기사를 찾을 수 없습니다";
    server.use(
      http.get("*/api/articles/missing-id", () =>
        HttpResponse.json({ code: "ARTICLE_NOT_FOUND", message }, { status: 404 }),
      ),
    );

    await act(async () => {
      renderWithQueryClient(
        <Suspense fallback={<div>상세 경로 준비 중</div>}>
          <ArticleDetailPage params={Promise.resolve({ articleId: "missing-id" })} />
        </Suspense>,
      );
    });

    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(screen.getByText(message)).toBeTruthy();
    expect(screen.getByRole("link", { name: "뉴스 목록으로 돌아가기" }).getAttribute("href")).toBe(
      "/feed",
    );
  });

  it("article_detail_page_matches_the_m3_prototype_information_sections", async () => {
    await act(async () => {
      renderWithQueryClient(
        <Suspense fallback={<div>loading detail route</div>}>
          <ArticleDetailPage params={Promise.resolve({ articleId: "article_001" })} />
        </Suspense>,
      );
    });

    expect(await screen.findByText("ZDNet Korea")).toBeTruthy();
    expect(screen.getByText("테크")).toBeTruthy();
    expect(screen.getByText("오늘 09:20")).toBeTruthy();
    expect(screen.queryByText("2026.05.10")).toBeNull();

    expect(
      screen.getByRole("heading", {
        level: 2,
        name: "오픈AI·앤트로픽, AI 에이전트 경쟁 본격화... 작업 자동화 시대 가시화",
      }),
    ).toBeTruthy();
    expect(screen.getByText("AI 에이전트")).toBeTruthy();
    expect(screen.getByText("오픈AI")).toBeTruthy();
    expect(screen.getByText("자동화")).toBeTruthy();
    expect(screen.getByText("AI가 원문을 읽고 핵심만 정리했어요")).toBeTruthy();
    expect(screen.getByRole("link", { name: "원문 보기" }).getAttribute("href")).toBe(
      "https://example.com/articles/ai-agent-automation",
    );

    expect(screen.getByText("핵심만 보기")).toBeTruthy();
    expect(screen.getByText("왜 중요해?")).toBeTruthy();
    expect(screen.getByText("조금 더 알기")).toBeTruthy();
    expect(screen.getByText("배경")).toBeTruthy();
    expect(screen.getByText("영향")).toBeTruthy();
    expect(screen.getByRole("link", { name: "홈" }).getAttribute("aria-current")).toBe("page");
    expect(screen.getByRole("link", { name: "챗" }).getAttribute("aria-current")).toBeNull();
    expect(screen.queryByRole("button", { name: "퀴즈로 이해도 확인하기" })).toBeNull();
    expect(screen.getByRole("link", { name: "오늘 리포트" }).getAttribute("href")).toMatch(
      /^\/report\/\d{4}-\d{2}-\d{2}$/,
    );
  });

  it("article_detail_page_embeds_inline_quiz_when_quizzes_exist", async () => {
    await act(async () => {
      renderWithQueryClient(
        <Suspense fallback={<div>loading detail route</div>}>
          <ArticleDetailPage params={Promise.resolve({ articleId: "article_001" })} />
        </Suspense>,
      );
    });

    expect(await screen.findByRole("region", { name: /OX 퀴즈/ })).toBeTruthy();
    expect(
      screen.getByRole("heading", {
        name: "오픈AI와 앤트로픽의 에이전트 기능 공개는 단순 챗봇 경쟁을 업무 자동화 경쟁으로 넓히는 변화다.",
      }),
    ).toBeTruthy();
    expect(screen.getByRole("button", { name: "O" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "X" })).toBeTruthy();
  });

  it("article_detail_page_uses_feed_category_badge_colors", async () => {
    server.use(
      http.get("*/api/articles/article_001", () =>
        HttpResponse.json({ ...articleDetails.article_001, category: "경제" }),
      ),
    );

    await act(async () => {
      renderWithQueryClient(
        <Suspense fallback={<div>loading detail route</div>}>
          <ArticleDetailPage params={Promise.resolve({ articleId: "article_001" })} />
        </Suspense>,
      );
    });

    const badge = await screen.findByText("경제");

    expect(badge.className).toContain("bg-[#eef4ff]");
    expect(badge.className).toContain("text-economy");
  });

  it("article_detail_page_replaces_raw_context_with_friendly_background", async () => {
    const rawContext = '{"content":"<div>본문 첫 문단</div>","rawText":"본문 둘째 문단"}';
    server.use(
      http.get("*/api/articles/article_001", () =>
        HttpResponse.json({
          ...articleDetails.article_001,
          context: rawContext,
          contextItems: [],
        }),
      ),
    );

    await act(async () => {
      renderWithQueryClient(
        <Suspense fallback={<div>loading detail route</div>}>
          <ArticleDetailPage params={Promise.resolve({ articleId: "article_001" })} />
        </Suspense>,
      );
    });

    expect(await screen.findByRole("heading", { level: 2 })).toBeTruthy();
    expect(screen.getByText("조금 더 알기")).toBeTruthy();
    expect(screen.getByText("배경")).toBeTruthy();
    expect(
      screen.getByText(
        "AI 에이전트·오픈AI는 이 기사를 이해하는 핵심 배경이에요. 오픈AI와 앤트로픽이 AI 에이전트 기능을 공개하며 단순 대화를 넘어 실제 업무 처리로 영역을 넓히고 있어요.",
      ),
    ).toBeTruthy();
    expect(screen.queryByText(rawContext)).toBeNull();
  });

  it("article_detail_page_renders_clean_context_fallback", async () => {
    const context = "AI 에이전트는 여러 앱과 도구를 이어서 실행하는 자동화 기능이에요.";
    server.use(
      http.get("*/api/articles/article_001", () =>
        HttpResponse.json({
          ...articleDetails.article_001,
          context,
          contextItems: [],
        }),
      ),
    );

    await act(async () => {
      renderWithQueryClient(
        <Suspense fallback={<div>loading detail route</div>}>
          <ArticleDetailPage params={Promise.resolve({ articleId: "article_001" })} />
        </Suspense>,
      );
    });

    expect(await screen.findByText("조금 더 알기")).toBeTruthy();
    expect(screen.getByText("배경")).toBeTruthy();
    expect(screen.getByText(context)).toBeTruthy();
  });

  it("article_detail_page_shows_inline_quiz_answer_feedback", async () => {
    await act(async () => {
      renderWithQueryClient(
        <Suspense fallback={<div>상세 경로 준비 중</div>}>
          <ArticleDetailPage params={Promise.resolve({ articleId: "article_001" })} />
        </Suspense>,
      );
    });

    expect(await screen.findByRole("region", { name: "기사 이해도 OX 퀴즈" })).toBeTruthy();
    expect(screen.getByText("읽은 내용 확인하기")).toBeTruthy();
    expect(screen.queryByText("Q1")).toBeNull();
    expect(screen.queryByText("1 / 3")).toBeNull();
    expect(
      screen.getByRole("heading", {
        name: "오픈AI와 앤트로픽의 에이전트 기능 공개는 단순 챗봇 경쟁을 업무 자동화 경쟁으로 넓히는 변화다.",
      }),
    ).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "O" }));
    expect(screen.getByText("정답입니다")).toBeTruthy();
    expect(
      screen.getByText(
        "기사에서 두 회사가 에이전트 기능을 공개하며 반복 업무 자동화 시장으로 경쟁을 넓히고 있다고 설명했어요.",
      ),
    ).toBeTruthy();
    expect(screen.queryByRole("button", { name: "다음 문항" })).toBeNull();
    expect(screen.queryByRole("button", { name: "결과 보기" })).toBeNull();
    expect(screen.queryByRole("button", { name: "다시 풀기" })).toBeNull();
  });
});
