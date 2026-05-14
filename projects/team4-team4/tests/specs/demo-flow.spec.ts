import { expect, test } from "@playwright/test";

test("demo input renders a patent-style result", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("발명 아이디어").fill("방구로 가는 자동차");
  await page.getByRole("button", { name: "명세서 생성" }).click();

  await expect(page.getByText("창작형 특허 명세서")).toBeVisible();
  await expect(page.getByText("생체 가스 배출 압력을 이용한 친환경 추진 차량")).toBeVisible();
  await expect(page.getByText("청구항")).toBeVisible();
});

