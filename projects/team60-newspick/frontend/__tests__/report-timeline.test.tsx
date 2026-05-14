import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ReportTimeline } from "../components/report/report-timeline";
import type { DailyReportTimelineItem } from "../lib/api/reports";

const timeline: DailyReportTimelineItem[] = [
  {
    articleId: "article_001",
    category: "테크",
    timeLabel: "09:00",
    title: "첫 기사",
    sourceCount: 4,
    summary: "첫 기사 요약",
  },
  {
    articleId: "article_002",
    category: "경제",
    timeLabel: "12:00",
    title: "두 번째 기사",
    sourceCount: 3,
  },
  {
    articleId: "article_003",
    category: "정책",
    timeLabel: "18:00",
    title: "세 번째 기사",
    sourceCount: 2,
  },
];

describe("ReportTimeline", () => {
  it("report_timeline_renders_items_in_order", () => {
    render(<ReportTimeline items={timeline} />);

    const list = screen.getByRole("list", { name: "주요 흐름" });
    const items = within(list).getAllByRole("listitem");

    expect(items).toHaveLength(3);
    expect(within(items[0]).getByText("09:00")).toBeTruthy();
    expect(within(items[0]).getByText("첫 기사")).toBeTruthy();
    expect(within(items[2]).getByText("● 정책")).toBeTruthy();
  });
});
