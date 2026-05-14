import { describe, expect, it } from "vitest";
import { formatSeoulDate, formatSeoulTime } from "../lib/datetime";

describe("datetime formatting", () => {
  it("formatSeoulTime_converts_utc_iso_values_to_seoul_time", () => {
    expect(formatSeoulTime("2026-05-13T06:36:47Z")).toBe("15:36");
  });

  it("formatSeoulTime_preserves_already_offset_seoul_values", () => {
    expect(formatSeoulTime("2026-05-13T15:36:47+09:00")).toBe("15:36");
  });

  it("formatSeoulDate_uses_the_seoul_calendar_day", () => {
    expect(formatSeoulDate("2026-05-12T15:20:00Z")).toBe("2026.05.13");
  });

  it("datetime_formatters_return_the_original_value_for_invalid_dates", () => {
    expect(formatSeoulTime("not-a-date")).toBe("not-a-date");
    expect(formatSeoulDate("not-a-date")).toBe("not-a-date");
  });
});
