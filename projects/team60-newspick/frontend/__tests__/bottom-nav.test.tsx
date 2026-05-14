import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { BottomNav } from "../components/bottom-nav";

afterEach(() => {
  vi.useRealTimers();
});

describe("BottomNav", () => {
  it("renders_navigation_items_with_active_page", () => {
    render(<BottomNav active="home" today={new Date("2026-05-12T09:00:00+09:00")} />);

    const home = screen.getByRole("link", { name: "홈" });
    const chat = screen.getByRole("link", { name: "챗" });
    const report = screen.getByRole("link", { name: "오늘 리포트" });

    expect(home.getAttribute("href")).toBe("/feed");
    expect(chat.getAttribute("href")).toBe("/chat");
    expect(report.getAttribute("href")).toBe("/report/2026-05-12");
    expect(home.getAttribute("aria-current")).toBe("page");
    expect(chat.getAttribute("aria-current")).toBeNull();
    expect(report.getAttribute("aria-current")).toBeNull();
    expect(chat.className).toContain("transition-[transform,box-shadow,background-color]");
    expect(chat.className).toContain("active:translate-y-[2px]");
    expect(home.className).toContain("text-[12px]");
    expect(home.className).toContain("font-[750]");
    expect(screen.getByText("홈")).toBeTruthy();
    expect(screen.getByText("리포트")).toBeTruthy();
  });

  it("bottom_navigation_has_today_report_link", () => {
    render(<BottomNav active="report" today={new Date("2026-05-12T09:00:00+09:00")} />);

    const report = screen.getByRole("link", { name: "오늘 리포트" });

    expect(report.getAttribute("href")).toBe("/report/2026-05-12");
    expect(report.getAttribute("aria-current")).toBe("page");
  });

  it("defaults_today_report_link_to_the_current_seoul_date", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-05-13T12:00:00+09:00"));

    render(<BottomNav active="home" />);

    expect(screen.getByRole("link", { name: "오늘 리포트" }).getAttribute("href")).toBe(
      "/report/2026-05-13",
    );
  });
});
