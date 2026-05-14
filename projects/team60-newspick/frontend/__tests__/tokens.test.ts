import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, test } from "vitest";

const globalsCss = readFileSync(join(process.cwd(), "app", "globals.css"), "utf8");

function extractCssVariables(css: string) {
  return new Map(
    Array.from(css.matchAll(/(--(?:color|font|radius)-[\w-]+)\s*:\s*([^;]+);/g)).map(
      ([, name, value]) => [name, value.trim()],
    ),
  );
}

describe("Tailwind tokens", () => {
  test("globals_css_defines_all_prototype_tokens", () => {
    const tokens = extractCssVariables(globalsCss);

    expect(Object.fromEntries(tokens)).toMatchObject({
      "--color-bg": "#f2f4f6",
      "--color-surface": "#ffffff",
      "--color-ink": "#191f28",
      "--color-muted": "#6b7684",
      "--color-hint": "#8b95a1",
      "--color-line": "#e5e8eb",
      "--color-chip": "#f2f4f6",
      "--color-brand-50": "#fff0e7",
      "--color-brand-500": "#ff8a3d",
      "--color-brand-600": "#f97821",
      "--color-economy": "#4f9cf9",
      "--color-policy": "#10b981",
      "--color-issue": "#9b7cf8",
      "--color-social": "#9b7cf8",
    });
  });
});
