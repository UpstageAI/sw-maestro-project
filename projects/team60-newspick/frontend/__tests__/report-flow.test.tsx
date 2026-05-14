import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ReportFlow } from "../components/report/report-flow";
import type { DailyReportFlowItem } from "../lib/api/reports";

const flow: DailyReportFlowItem[] = [
  { category: "원인", description: "첫 설명" },
  { category: "전개", description: "두 번째 설명" },
  { category: "전망", description: "세 번째 설명" },
];

describe("ReportFlow", () => {
  it("report_flow_renders_three_named_steps", () => {
    render(<ReportFlow items={flow} />);

    const section = screen.getByRole("region", { name: "오늘의 흐름" });

    expect(within(section).getByRole("heading", { name: "오늘의 흐름" })).toBeTruthy();
    expect(within(section).getByText("원인")).toBeTruthy();
    expect(within(section).getByText("전개")).toBeTruthy();
    expect(within(section).getByText("전망")).toBeTruthy();
    expect(within(section).getByText("첫 설명")).toBeTruthy();
    expect(within(section).getByText("두 번째 설명")).toBeTruthy();
    expect(within(section).getByText("세 번째 설명")).toBeTruthy();
  });
});
