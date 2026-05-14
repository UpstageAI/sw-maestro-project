import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { DailyReportNotReadyError, fetchDailyReport } from "../lib/api/reports";
import { handlers } from "../mocks/handlers";

const server = setupServer(...handlers);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("fetchDailyReport", () => {
  it("fetchDailyReport_returns_report_for_date", async () => {
    const report = await fetchDailyReport("2026-05-12");

    expect(report.date).toBe("2026-05-12");
    expect(report.briefing.headline).toBe("오늘의 핵심");
  });

  it("fetchDailyReport_throws_not_ready_error_for_404", async () => {
    await expect(fetchDailyReport("2026-05-13")).rejects.toBeInstanceOf(
      DailyReportNotReadyError,
    );
  });
});
