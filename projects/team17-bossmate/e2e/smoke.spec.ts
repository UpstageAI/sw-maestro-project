import { test, expect } from "@playwright/test";

test("landing CTA opens the studio wizard", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { level: 2, name: /오늘 한 끼/ }).first(),
  ).toBeVisible();

  await page
    .getByRole("link", { name: /지금 시작하기/ })
    .first()
    .click();

  await expect(page).toHaveURL(/\/studio$/);
  await expect(
    page.getByRole("heading", { level: 1, name: /가게 정보를 알려주세요/ }),
  ).toBeVisible();
});

test("API job submission returns 202 with id", async ({ request }) => {
  const gen = await request.post("/api/cards/generate", {
    data: {
      store: {
        storeName: "행복국밥",
        category: "음식점",
        vibe: "따뜻한",
        description: "30년 전통 한식당",
      },
      purpose: "new-menu",
      detail: "점심 든든한 국밥 9,000원, 정성 가득한 한 끼",
      platform: "instagram",
    },
  });
  expect(gen.status()).toBe(202);
  const body = await gen.json();
  expect(body.id).toBeTruthy();
  expect(body.status).toBe("pending");

  const status = await request.get(`/api/cards/${body.id}`);
  expect(status.ok()).toBeTruthy();
  const job = await status.json();
  expect(job.id).toBe(body.id);
  expect(["pending", "processing", "done", "error"]).toContain(job.status);
});
