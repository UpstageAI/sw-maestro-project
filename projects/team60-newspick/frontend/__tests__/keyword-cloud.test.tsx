import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { KeywordCloud } from "../components/report/keyword-cloud";
import type { DailyReportKeyword } from "../lib/api/reports";

const keywords: DailyReportKeyword[] = [
  { text: "AI", weight: 5 },
  { text: "반도체", weight: 3 },
  { text: "환율", weight: 1 },
];

describe("KeywordCloud", () => {
  it("keyword_cloud_renders_keywords_with_weight_labels", () => {
    render(<KeywordCloud keywords={keywords} />);

    const list = screen.getByRole("list", { name: "핵심 키워드" });

    expect(within(list).getByText("AI")).toBeTruthy();
    expect(within(list).getByText("반도체")).toBeTruthy();
    expect(within(list).getByText("환율")).toBeTruthy();
    expect(within(list).getByLabelText("AI 중요도 5")).toBeTruthy();
  });
});
