import { test } from '@playwright/test';
test('브리핑 화면 스크린샷', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto('/');
  await page.click('button:has-text("뉴스 수집 및 저장")');
  await page.waitForSelector('text=뉴스 수집 완료', { timeout: 30000 });
  await page.click('button:has-text("브리핑 생성")');
  await page.waitForSelector('text=생성된 브리핑', { timeout: 30000 });
  await page.screenshot({ path: '/tmp/briefing2.png', fullPage: true });
});
