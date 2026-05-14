import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { HttpResponse, delay, http } from "msw";
import { setupServer } from "msw/node";
import type { ReactNode } from "react";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import FeedPage from "../app/(app)/feed/page";
import { useCategoryStore } from "../lib/store/category";
import { useRefreshStore } from "../lib/store/refresh";
import { feedArticles } from "../mocks/fixtures/articles";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(window.location.search),
}));

type Listener = (event: MessageEvent<string>) => void;

class FakeEventSource {
  static instances: FakeEventSource[] = [];

  listeners = new Map<string, Listener[]>();
  onerror: ((event: Event) => void) | null = null;
  closed = false;
  url: string;

  constructor(url: string) {
    this.url = url;
    FakeEventSource.instances.push(this);
  }

  addEventListener(name: string, listener: Listener) {
    const listeners = this.listeners.get(name) ?? [];
    listeners.push(listener);
    this.listeners.set(name, listeners);
  }

  close() {
    this.closed = true;
  }

  emit(name: string, data: unknown) {
    this.emitRaw(name, JSON.stringify(data));
  }

  emitRaw(name: string, data: string) {
    const event = new MessageEvent(name, { data });
    this.listeners.get(name)?.forEach((listener) => listener(event));
  }
}

const server = setupServer();
let cancelCalls = 0;

function exactText(text: string) {
  return (_content: string, element: Element | null) => element?.textContent === text;
}

function renderWithQueryClient(children: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  const view = render(<QueryClientProvider client={queryClient}>{children}</QueryClientProvider>);
  return {
    ...view,
    rerenderWithQueryClient: (nextChildren: ReactNode) =>
      view.rerender(<QueryClientProvider client={queryClient}>{nextChildren}</QueryClientProvider>),
  };
}

beforeAll(() => server.listen());
beforeEach(() => {
  cancelCalls = 0;
  server.use(
    http.post("*/api/refresh-stream/:runId/cancel", () => {
      cancelCalls += 1;
      return new Response(null, { status: 204 });
    }),
  );
});
afterEach(() => {
  cleanup();
  window.history.pushState({}, "", "/");
  server.resetHandlers();
  useCategoryStore.getState().reset();
  useRefreshStore.getState().reset();
  FakeEventSource.instances = [];
  vi.unstubAllGlobals();
});
afterAll(() => server.close());

describe("FeedPage", () => {
  it("shows_query_skeleton_without_collection_progress_for_plain_feed_load", () => {
    server.use(
      http.get("*/api/feed", async () => {
        await delay("infinite");
        return HttpResponse.json({ articles: [] });
      }),
    );

    renderWithQueryClient(<FeedPage />);

    expect(screen.getByRole("status", { name: "뉴스 불러오는 중" })).toBeTruthy();
    expect(screen.queryByLabelText("뉴스 로딩 상태")).toBeNull();
  });

  it("shows_empty_state_when_feed_has_no_articles", async () => {
    server.use(http.get("*/api/feed", () => HttpResponse.json({ articles: [] })));

    renderWithQueryClient(<FeedPage />);

    expect(await screen.findByText("아직 보여줄 뉴스가 없어요")).toBeTruthy();
    expect(screen.getByRole("link", { name: "홈" }).getAttribute("aria-current")).toBe("page");
  });

  it("shows_news_cards_when_feed_has_articles", async () => {
    window.history.pushState({}, "", "/feed?categories=tech,economy");
    server.use(
      http.get("*/api/feed", ({ request }) => {
        expect(new URL(request.url).searchParams.get("categories")).toBe("tech,economy");
        return HttpResponse.json({ articles: feedArticles });
      }),
    );

    renderWithQueryClient(<FeedPage />);

    await waitFor(() => expect(screen.getAllByRole("article")).toHaveLength(3));
    const categoryFilters = screen.getByRole("group", { name: "카테고리 필터" });
    expect(within(categoryFilters).getAllByRole("button")).toHaveLength(4);
    const techFilter = within(categoryFilters).getByRole("button", { name: "테크" });
    const economyFilter = within(categoryFilters).getByRole("button", { name: "경제" });
    const policyFilter = within(categoryFilters).getByRole("button", { name: "정책" });
    const issueFilter = within(categoryFilters).getByRole("button", { name: "이슈" });
    expect(techFilter.getAttribute("aria-pressed")).toBe("true");
    expect(economyFilter.getAttribute("aria-pressed")).toBe("true");
    expect(policyFilter.getAttribute("aria-pressed")).toBe("false");
    expect(issueFilter.getAttribute("aria-pressed")).toBe("false");
    expect(techFilter.className).toContain("bg-brand-50");
    expect(economyFilter.className).toContain("bg-[#eef4ff]");
    expect(economyFilter.className).toContain("text-economy");
    expect(policyFilter.className).toContain("bg-chip");
    expect(screen.getByRole("heading", { level: 1, name: "오늘의 뉴스" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "다시 수집" }).getAttribute("href")).toBe(
      "/feed?refresh=1&reset=1&categories=tech%2Ceconomy",
    );
    expect(screen.getByRole("link", { name: "처음으로" }).getAttribute("href")).toBe("/");
  });

  it("keeps_feed_filtered_to_selected_issue_and_policy_categories", async () => {
    window.history.pushState({}, "", "/feed?categories=issue,policy");
    server.use(
      http.get("*/api/feed", ({ request }) => {
        expect(new URL(request.url).searchParams.get("categories")).toBe("issue,policy");
        return HttpResponse.json({
          articles: [
            { ...feedArticles[0], id: "issue-1", category: "이슈" },
            { ...feedArticles[1], id: "policy-1", category: "정책" },
          ],
        });
      }),
    );

    renderWithQueryClient(<FeedPage />);

    await waitFor(() => expect(screen.getAllByRole("article")).toHaveLength(2));
    const categoryFilters = screen.getByRole("group", { name: "카테고리 필터" });
    expect(within(categoryFilters).getByRole("button", { name: "테크" }).getAttribute("aria-pressed")).toBe("false");
    expect(within(categoryFilters).getByRole("button", { name: "경제" }).getAttribute("aria-pressed")).toBe("false");
    expect(within(categoryFilters).getByRole("button", { name: "정책" }).getAttribute("aria-pressed")).toBe("true");
    expect(within(categoryFilters).getByRole("button", { name: "이슈" }).getAttribute("aria-pressed")).toBe("true");
    const articles = screen.getAllByRole("article");
    expect(within(articles[0]).getByText("이슈")).toBeTruthy();
    expect(within(articles[1]).getByText("정책")).toBeTruthy();
  });

  it("adds_category_filter_from_top_chip_and_refetches_feed", async () => {
    window.history.pushState({}, "", "/feed?categories=tech,economy");
    const requests: Array<string | null> = [];
    server.use(
      http.get("*/api/feed", ({ request }) => {
        requests.push(new URL(request.url).searchParams.get("categories"));
        return HttpResponse.json({ articles: feedArticles });
      }),
    );

    renderWithQueryClient(<FeedPage />);

    await waitFor(() => expect(requests).toContain("tech,economy"));
    fireEvent.click(screen.getByRole("button", { name: "정책" }));

    await waitFor(() => expect(window.location.search).toBe("?categories=tech%2Ceconomy%2Cpolicy"));
    await waitFor(() => expect(requests).toContain("tech,economy,policy"));
    expect(screen.getByRole("button", { name: "정책" }).getAttribute("aria-pressed")).toBe("true");
    expect(screen.getByRole("link", { name: "다시 수집" }).getAttribute("href")).toBe(
      "/feed?refresh=1&reset=1&categories=tech%2Ceconomy%2Cpolicy",
    );
  });

  it("removes_selected_category_filter_from_top_chip_and_refetches_feed", async () => {
    window.history.pushState({}, "", "/feed?categories=tech,economy");
    const requests: Array<string | null> = [];
    server.use(
      http.get("*/api/feed", ({ request }) => {
        requests.push(new URL(request.url).searchParams.get("categories"));
        return HttpResponse.json({ articles: feedArticles });
      }),
    );

    renderWithQueryClient(<FeedPage />);

    await waitFor(() => expect(requests).toContain("tech,economy"));
    fireEvent.click(screen.getByRole("button", { name: "경제" }));

    await waitFor(() => expect(window.location.search).toBe("?categories=tech"));
    await waitFor(() => expect(requests).toContain("tech"));
    expect(screen.getByRole("button", { name: "경제" }).getAttribute("aria-pressed")).toBe("false");
    expect(screen.getByRole("link", { name: "다시 수집" }).getAttribute("href")).toBe(
      "/feed?refresh=1&reset=1&categories=tech",
    );
  });

  it("keeps_the_last_category_filter_selected", async () => {
    window.history.pushState({}, "", "/feed?categories=tech");
    server.use(http.get("*/api/feed", () => HttpResponse.json({ articles: feedArticles })));

    renderWithQueryClient(<FeedPage />);

    await waitFor(() => expect(screen.getAllByRole("article")).toHaveLength(3));
    fireEvent.click(screen.getByRole("button", { name: "테크" }));

    expect(window.location.search).toBe("?categories=tech");
    expect(screen.getByRole("button", { name: "테크" }).getAttribute("aria-pressed")).toBe("true");
    expect(screen.getByRole("link", { name: "다시 수집" }).getAttribute("href")).toBe(
      "/feed?refresh=1&reset=1&categories=tech",
    );
  });

  it("updates_loading_progress_from_sse_step_events", async () => {
    window.history.pushState({}, "", "/feed?categories=tech&refresh=1");
    vi.stubGlobal("EventSource", FakeEventSource);
    server.use(
      http.get("*/api/feed", async () => {
        await delay("infinite");
        return HttpResponse.json({ articles: [] });
      }),
    );

    renderWithQueryClient(<FeedPage />);

    await waitFor(() => expect(FakeEventSource.instances.length).toBe(1));
    const url = new URL(FakeEventSource.instances[0].url);
    expect(url.searchParams.get("categories")).toBe("tech");
    expect(url.searchParams.get("runId")).toBeTruthy();

    act(() => {
      FakeEventSource.instances[0].emit("step", { step: "collect", current: 7, total: 12 });
      FakeEventSource.instances[0].emit("step", { step: "extract", current: 6, total: 8 });
      FakeEventSource.instances[0].emit("step", { step: "summarize", current: 3, total: 8 });
      FakeEventSource.instances[0].emit("step", { step: "save", current: 0, total: 1 });
    });

    expect(await screen.findByText(exactText("7/12 매체"))).toBeTruthy();
    expect(screen.getByText(exactText("3/8 기사"))).toBeTruthy();
    expect(screen.getByText("0%")).toBeTruthy();
    expect(screen.getByText("기사 준비 중")).toBeTruthy();
    expect(screen.queryByText("기사 본문 확인")).toBeNull();
    expect(screen.queryByLabelText("기사별 요약 진행")).toBeNull();
    expect(screen.getByText("뉴스를 마무리 중이에요")).toBeTruthy();
  });

  it("shows_ai_summary_total_as_soon_as_extraction_finishes", async () => {
    window.history.pushState({}, "", "/feed?categories=tech&refresh=1");
    vi.stubGlobal("EventSource", FakeEventSource);
    server.use(http.get("*/api/feed", () => HttpResponse.json({ articles: [] })));

    renderWithQueryClient(<FeedPage />);

    await waitFor(() => expect(FakeEventSource.instances.length).toBe(1));

    act(() => {
      FakeEventSource.instances[0].emit("step", { step: "extract", current: 6, total: 8 });
    });

    expect(await screen.findByText(exactText("0/6 기사"))).toBeTruthy();
    expect(screen.getAllByText("준비 중").length).toBeGreaterThan(0);
  });

  it("shows_ai_summary_progress_incrementally_from_sse_events", async () => {
    window.history.pushState({}, "", "/feed?categories=tech&refresh=1");
    vi.stubGlobal("EventSource", FakeEventSource);
    server.use(http.get("*/api/feed", () => HttpResponse.json({ articles: [] })));

    renderWithQueryClient(<FeedPage />);

    await waitFor(() => expect(FakeEventSource.instances.length).toBe(1));

    act(() => {
      FakeEventSource.instances[0].emit("step", { step: "summarize", current: 0, total: 3 });
    });
    expect(await screen.findByText(exactText("0/3 기사"))).toBeTruthy();

    act(() => {
      FakeEventSource.instances[0].emit("step", { step: "summarize", current: 1, total: 3 });
    });
    expect(await screen.findByText(exactText("1/3 기사"))).toBeTruthy();

    act(() => {
      FakeEventSource.instances[0].emit("step", { step: "summarize", current: 2, total: 3 });
    });
    expect(await screen.findByText(exactText("2/3 기사"))).toBeTruthy();
  });

  it("shows_prepare_progress_as_percent_steps", async () => {
    window.history.pushState({}, "", "/feed?categories=tech&refresh=1");
    vi.stubGlobal("EventSource", FakeEventSource);
    server.use(http.get("*/api/feed", () => HttpResponse.json({ articles: [] })));

    renderWithQueryClient(<FeedPage />);

    await waitFor(() => expect(FakeEventSource.instances.length).toBe(1));

    act(() => {
      FakeEventSource.instances[0].emit("step", { step: "save", current: 0, total: 1 });
    });
    expect(await screen.findByText("0%")).toBeTruthy();

    act(() => {
      FakeEventSource.instances[0].emit("step", { step: "save", current: 1, total: 1 });
    });
    expect(await screen.findByText("25%")).toBeTruthy();

    act(() => {
      FakeEventSource.instances[0].emit("step", { step: "embed", current: 1, total: 1 });
    });
    expect(await screen.findByText("50%")).toBeTruthy();

    act(() => {
      FakeEventSource.instances[0].emit("step", { step: "quiz", current: 1, total: 1 });
    });
    expect(await screen.findByText("75%")).toBeTruthy();

    act(() => {
      FakeEventSource.instances[0].emit("step", { step: "report", current: 1, total: 1 });
    });
    expect(await screen.findByText("100%")).toBeTruthy();
  });

  it("passes_reset_query_to_refresh_stream", async () => {
    window.history.pushState({}, "", "/feed?categories=tech&refresh=1&reset=1");
    vi.stubGlobal("EventSource", FakeEventSource);
    server.use(http.get("*/api/feed", () => HttpResponse.json({ articles: [] })));

    renderWithQueryClient(<FeedPage />);

    await waitFor(() => expect(FakeEventSource.instances.length).toBe(1));
    const url = new URL(FakeEventSource.instances[0].url);
    expect(url.searchParams.get("categories")).toBe("tech");
    expect(url.searchParams.get("reset")).toBe("1");
  });

  it("hides_existing_cards_behind_loading_progress_during_reset_refresh", async () => {
    window.history.pushState({}, "", "/feed?categories=tech&refresh=1&reset=1");
    vi.stubGlobal("EventSource", FakeEventSource);
    server.use(http.get("*/api/feed", () => HttpResponse.json({ articles: feedArticles })));

    renderWithQueryClient(<FeedPage />);

    await waitFor(() => expect(FakeEventSource.instances.length).toBe(1));
    expect(screen.getByLabelText("뉴스 로딩 상태")).toBeTruthy();
    expect(
      screen.queryByRole("heading", { level: 3, name: feedArticles[0].title }),
    ).toBeNull();
  });

  it("shows_reset_error_instead_of_existing_cards_when_refresh_stream_fails", async () => {
    window.history.pushState({}, "", "/feed?categories=tech&refresh=1&reset=1");
    vi.stubGlobal("EventSource", FakeEventSource);
    server.use(http.get("*/api/feed", () => HttpResponse.json({ articles: feedArticles })));

    renderWithQueryClient(<FeedPage />);

    await waitFor(() => expect(FakeEventSource.instances.length).toBe(1));

    act(() => {
      FakeEventSource.instances[0].emit("error", {
        code: "missing_environment",
        message: "AI 설정을 읽지 못해 재수집을 완료하지 못했어요.",
      });
    });

    expect(
      await screen.findByText("AI 설정을 읽지 못해 재수집을 완료하지 못했어요."),
    ).toBeTruthy();
    expect(
      screen.queryByRole("heading", { level: 3, name: feedArticles[0].title }),
    ).toBeNull();
    expect(cancelCalls).toBe(0);
  });

  it("does_not_cancel_refresh_when_component_unmounts", async () => {
    window.history.pushState({}, "", "/feed?categories=tech&refresh=1&reset=1");
    vi.stubGlobal("EventSource", FakeEventSource);
    server.use(http.get("*/api/feed", () => HttpResponse.json({ articles: [] })));

    renderWithQueryClient(<FeedPage />);

    await waitFor(() => expect(FakeEventSource.instances.length).toBe(1));
    cleanup();

    expect(FakeEventSource.instances[0].closed).toBe(true);
    expect(cancelCalls).toBe(0);
  });

  it("keeps_refresh_loading_until_feed_refetch_finishes_after_done", async () => {
    window.history.pushState({}, "", "/feed?categories=tech&refresh=1");
    vi.stubGlobal("EventSource", FakeEventSource);
    let feedCalls = 0;
    server.use(
      http.get("*/api/feed", () => {
        feedCalls += 1;
        return HttpResponse.json({ articles: feedCalls === 1 ? [] : feedArticles });
      }),
    );

    renderWithQueryClient(<FeedPage />);

    await waitFor(() => expect(FakeEventSource.instances.length).toBe(1));

    act(() => {
      FakeEventSource.instances[0].emit("step", { step: "summarize", current: 2, total: 2 });
      FakeEventSource.instances[0].emit("done", { articleIds: ["article_001"] });
    });

    expect(screen.getByLabelText("뉴스 로딩 상태")).toBeTruthy();
    await waitFor(() => expect(screen.getAllByRole("article")).toHaveLength(3));
    expect(window.location.search).toBe("?categories=tech");
  });

  it("shows_error_state_for_raw_error_event", async () => {
    window.history.pushState({}, "", "/feed?categories=tech&refresh=1");
    vi.stubGlobal("EventSource", FakeEventSource);
    server.use(http.get("*/api/feed", () => HttpResponse.json({ articles: [] })));

    renderWithQueryClient(<FeedPage />);

    await waitFor(() => expect(FakeEventSource.instances.length).toBe(1));

    act(() => {
      FakeEventSource.instances[0].emitRaw("error", "timeout");
    });

    expect(await screen.findByText("뉴스를 불러오지 못했어요")).toBeTruthy();
    expect(window.location.search).toBe("?categories=tech");
  });

  it("does_not_cancel_when_malformed_stream_event_closes_transport", async () => {
    window.history.pushState({}, "", "/feed?categories=tech&refresh=1");
    vi.stubGlobal("EventSource", FakeEventSource);
    server.use(http.get("*/api/feed", () => HttpResponse.json({ articles: [] })));

    renderWithQueryClient(<FeedPage />);

    await waitFor(() => expect(FakeEventSource.instances.length).toBe(1));

    act(() => {
      FakeEventSource.instances[0].emitRaw("step", "not-json");
    });

    expect(await screen.findByText("뉴스를 불러오지 못했어요")).toBeTruthy();
    expect(cancelCalls).toBe(0);
  });

  it("does_not_cancel_when_start_over_confirmation_is_rejected", async () => {
    window.history.pushState({}, "", "/feed?categories=tech&refresh=1");
    vi.stubGlobal("EventSource", FakeEventSource);
    vi.stubGlobal("confirm", vi.fn(() => false));
    server.use(http.get("*/api/feed", () => HttpResponse.json({ articles: [] })));

    renderWithQueryClient(<FeedPage />);

    await waitFor(() => expect(FakeEventSource.instances.length).toBe(1));

    fireEvent.click(screen.getByRole("link", { name: "처음으로" }));

    expect(cancelCalls).toBe(0);
    expect(FakeEventSource.instances[0].closed).toBe(false);
    expect(window.location.pathname).toBe("/feed");
  });

  it("cancels_refresh_when_start_over_confirmation_is_accepted", async () => {
    window.history.pushState({}, "", "/feed?categories=tech&refresh=1");
    vi.stubGlobal("EventSource", FakeEventSource);
    vi.stubGlobal("confirm", vi.fn(() => true));
    server.use(http.get("*/api/feed", () => HttpResponse.json({ articles: [] })));

    renderWithQueryClient(<FeedPage />);

    await waitFor(() => expect(FakeEventSource.instances.length).toBe(1));

    fireEvent.click(screen.getByRole("link", { name: "처음으로" }));

    await waitFor(() => expect(cancelCalls).toBe(1));
    expect(FakeEventSource.instances[0].closed).toBe(true);
    expect(window.location.pathname).toBe("/");
  });
});
