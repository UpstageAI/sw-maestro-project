import { expect, test } from "@playwright/test";
import fs from "fs";
import path from "path";

const DEMO_INPUTS = [
  "방구로 가는 자동차",
  "기억을 USB처럼 꽂아서 옮기는 헬멧",
  "잠을 대신 자주는 베개",
];

test.describe("Brainrot Patent demo flow", () => {
  for (const demoInput of DEMO_INPUTS) {
    test(`renders a patent-style result and exports PDF: ${demoInput}`, async ({ page }) => {
      await page.goto("/");

      await page.getByLabel("발명 아이디어").fill(demoInput);
      await page.getByRole("button", { name: "명세서 생성" }).click();

      await expect(page.getByText("창작형 특허 명세서")).toBeVisible();
      await expect(page.getByRole("heading", { name: "청구항" })).toBeVisible();

      const outputDir = path.join(process.cwd(), "artifacts");
      fs.mkdirSync(outputDir, { recursive: true });

      const safeFileName = demoInput
        .replace(/\s+/g, "-")
        .replace(/[^\p{L}\p{N}-]/gu, "");

<<<<<<< ours
=======
      await page.waitForTimeout(15000);

>>>>>>> theirs
      await page.pdf({
        path: path.join(outputDir, `demo-result-${safeFileName}.pdf`),
        format: "A4",
        printBackground: true,
      });
    });
  }

  test("shows fallback result when API generation fails", async ({ page }) => {
    await page.route("**/api/generate", async route => {
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ error: "forced error" }),
      });
    });

    await page.goto("/");

    await page.getByLabel("발명 아이디어").fill(DEMO_INPUTS[0]);
    await page.getByRole("button", { name: "명세서 생성" }).click();

    await expect(page.getByText(/API 연결에 실패해 샘플 결과를 표시합니다/)).toBeVisible();
    await expect(page.getByRole("heading", { name: "청구항" })).toBeVisible();
  });
});