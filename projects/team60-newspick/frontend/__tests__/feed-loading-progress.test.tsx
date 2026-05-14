import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { FeedLoadingProgress } from "../components/feed-loading-progress";
import { useRefreshStore } from "../lib/store/refresh";

function exactText(text: string) {
  return (_content: string, element: Element | null) => element?.textContent === text;
}

describe("FeedLoadingProgress", () => {
  beforeEach(() => {
    useRefreshStore.getState().reset();
  });

  it("renders_collect_and_summarize_progress", () => {
    useRefreshStore.getState().setStep("collect", 7, 12);
    useRefreshStore.getState().setStep("summarize", 3, 8);
    useRefreshStore.getState().setStep("prepare", 1, 4);

    render(<FeedLoadingProgress />);

    expect(screen.getByLabelText("뉴스 로딩 상태")).toBeTruthy();
    expect(screen.getByTestId("loading-orbit")).toBeTruthy();
    expect(screen.getByText("주요 뉴스 수집").className).toContain("font-[700]");
    expect(screen.getByText(exactText("7/12 매체"))).toBeTruthy();
    expect(screen.getByText("AI 요약 생성").className).toContain("font-[700]");
    expect(screen.getByText(exactText("3/8 기사"))).toBeTruthy();
    expect(screen.getByText("기사 준비 중").className).toContain("font-[700]");
    expect(screen.getByText("25%")).toBeTruthy();
    expect(screen.queryByText("기사 본문 확인")).toBeNull();
    expect(screen.queryByText("AI 검색 색인")).toBeNull();
    expect(screen.queryByLabelText("기사별 요약 진행")).toBeNull();
    expect(screen.getAllByTestId("news-skeleton")).toHaveLength(2);
  });

  it("renders_ready_state_before_totals_arrive", () => {
    render(<FeedLoadingProgress />);

    expect(screen.getAllByText("준비 중")).toHaveLength(3);
  });

  it("renders_finalizing_copy_after_summary_finishes", () => {
    useRefreshStore.getState().setFinalizing(true);

    render(<FeedLoadingProgress />);

    expect(screen.getByText("뉴스를 마무리 중이에요")).toBeTruthy();
    expect(screen.getByText("요약된 기사를 저장하고 리포트까지 준비하고 있어요.")).toBeTruthy();
  });
});
