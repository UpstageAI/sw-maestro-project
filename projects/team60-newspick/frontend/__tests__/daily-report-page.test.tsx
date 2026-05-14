import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, render, screen } from "@testing-library/react";
import { setupServer } from "msw/node";
import { Suspense, type ReactNode } from "react";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import DailyReportPage from "../app/(app)/report/[date]/page";
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

describe("DailyReportPage", () => {
  it("daily_report_page_renders_briefing_headline", async () => {
    await act(async () => {
      renderWithQueryClient(
        <Suspense fallback={<div>리포트 경로 준비 중</div>}>
          <DailyReportPage params={Promise.resolve({ date: "2026-05-12" })} />
        </Suspense>,
      );
    });

    expect(
      await screen.findByRole("heading", { level: 1, name: "오늘의 리포트" }),
    ).toBeTruthy();
    expect(screen.getByText("5월 12일")).toBeTruthy();
    expect(screen.getByText("AI 자동화와 통상 압박, 인구 위기가 동시에 부상한 하루였습니다.")).toBeTruthy();
    expect(screen.getByText("오늘 따라잡기 끝 — 내일 09:30에 다시 만나요")).toBeTruthy();
  });

  it("daily_report_page_shows_not_ready_state_for_404", async () => {
    await act(async () => {
      renderWithQueryClient(
        <Suspense fallback={<div>리포트 경로 준비 중</div>}>
          <DailyReportPage params={Promise.resolve({ date: "2026-05-13" })} />
        </Suspense>,
      );
    });

    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(screen.getByText("아직 리포트가 준비되지 않았어요")).toBeTruthy();
    expect(screen.getByRole("link", { name: "피드로 돌아가기" })).toBeTruthy();
  });
});
