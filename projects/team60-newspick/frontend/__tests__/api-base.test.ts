import { describe, expect, it } from "vitest";
import { defaultApiBaseForLocation } from "../lib/api/base";

describe("api base", () => {
  it("uses_current_browser_host_for_default_api_base", () => {
    expect(
      defaultApiBaseForLocation({
        protocol: "http:",
        hostname: "118.32.150.169",
      }),
    ).toBe("http://118.32.150.169:8080");
  });
});
