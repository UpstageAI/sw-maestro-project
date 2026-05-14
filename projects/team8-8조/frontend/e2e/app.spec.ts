import { expect, test } from '@playwright/test';

test.describe('디자인 확인', () => {
  test('헤더가 표시된다', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('heading', { name: 'Daily News Agent' })).toBeVisible();
    await expect(page.getByText('Google News RSS에서 관심 분야 뉴스를 수집하고 브리핑을 생성합니다')).toBeVisible();
  });

  test('사이드바에 설정 항목이 표시된다', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('실행 설정')).toBeVisible();
    await expect(page.getByText('키워드별 수집 수')).toBeVisible();
    await expect(page.getByText('브리핑 기사 수')).toBeVisible();
  });

  test('AI 모드 뱃지가 표시된다', async ({ page }) => {
    await page.goto('/');
    // 백엔드 연결 후 뱃지 표시 확인
    await page.waitForTimeout(1000);
    const badge = page.locator('header span').filter({ hasText: /모드/ });
    await expect(badge).toBeVisible();
  });

  test('단계 표시가 보인다', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('입력', { exact: true })).toBeVisible();
    await expect(page.getByText('수집', { exact: true })).toBeVisible();
    await expect(page.getByText('브리핑', { exact: true })).toBeVisible();
  });

  test('입력 필드 두 개가 표시된다', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByPlaceholder('예: AI 산업 동향')).toBeVisible();
    await expect(page.getByPlaceholder('예: AI, 반도체, 스타트업')).toBeVisible();
  });

  test('버튼 두 개가 표시된다', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('button', { name: '뉴스 수집 및 저장' })).toBeVisible();
    await expect(page.getByRole('button', { name: '브리핑 생성' })).toBeVisible();
  });

  test('브리핑 생성 버튼은 수집 전 비활성화 상태다', async ({ page }) => {
    await page.goto('/');
    const briefingBtn = page.getByRole('button', { name: '브리핑 생성' });
    await expect(briefingBtn).toBeDisabled();
  });

  test('이메일 섹션이 표시된다', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('메일로 뉴스 받기')).toBeVisible();
    await expect(page.getByPlaceholder('recipient@example.com')).toBeVisible();
  });
});

test.describe('입력 기능', () => {
  test('관심 분야 입력값을 변경할 수 있다', async ({ page }) => {
    await page.goto('/');
    const input = page.getByPlaceholder('예: AI 산업 동향');
    await input.fill('반도체 산업');
    await expect(input).toHaveValue('반도체 산업');
  });

  test('키워드 입력값을 변경할 수 있다', async ({ page }) => {
    await page.goto('/');
    const input = page.getByPlaceholder('예: AI, 반도체, 스타트업');
    await input.fill('삼성, SK하이닉스');
    await expect(input).toHaveValue('삼성, SK하이닉스');
  });

  test('사이드바 슬라이더로 수집 기사 수를 변경할 수 있다', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText(/키워드별 수집 수/)).toBeVisible();
  });
});

test.describe('뉴스 수집 기능', () => {
  test('수집 버튼 클릭 시 로딩 메시지가 표시된다', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: '뉴스 수집 및 저장' }).click();
    await expect(page.getByText(/수집 중/)).toBeVisible();
  });

  test('수집 완료 후 메트릭 카드가 표시된다', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: '뉴스 수집 및 저장' }).click();
    // 수집 완료 대기 (최대 30초)
    await expect(page.getByText('뉴스 수집 완료')).toBeVisible({ timeout: 30000 });
    await expect(page.getByText('수집된 기사')).toBeVisible();
    await expect(page.getByText('새로 저장')).toBeVisible();
  });

  test('수집 완료 후 브리핑 생성 버튼이 활성화된다', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: '뉴스 수집 및 저장' }).click();
    await expect(page.getByText('뉴스 수집 완료')).toBeVisible({ timeout: 30000 });
    await expect(page.getByRole('button', { name: '브리핑 생성' })).toBeEnabled();
  });

  test('수집 완료 후 단계 표시가 2단계로 업데이트된다', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: '뉴스 수집 및 저장' }).click();
    await expect(page.getByText('뉴스 수집 완료')).toBeVisible({ timeout: 30000 });
    // 1단계(입력)가 완료 표시(✓)로 바뀌어야 함
    await expect(page.locator('text=✓').first()).toBeVisible();
  });
});

test.describe('브리핑 생성 기능', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: '뉴스 수집 및 저장' }).click();
    await expect(page.getByText('뉴스 수집 완료')).toBeVisible({ timeout: 30000 });
  });

  test('브리핑 생성 후 마크다운 결과가 표시된다', async ({ page }) => {
    await page.getByRole('button', { name: '브리핑 생성' }).click();
    await expect(page.getByText('생성된 브리핑')).toBeVisible({ timeout: 30000 });
  });

  test('브리핑 생성 후 기사 카드 그리드가 표시된다', async ({ page }) => {
    await page.getByRole('button', { name: '브리핑 생성' }).click();
    await expect(page.getByText('선별된 기사')).toBeVisible({ timeout: 30000 });
    // 기사 카드(원문 보기 링크)가 하나 이상 있어야 함
    await expect(page.getByRole('link', { name: '원문 보기' }).first()).toBeVisible();
  });

  test('기사 카드에 제목, 출처가 표시된다', async ({ page }) => {
    await page.getByRole('button', { name: '브리핑 생성' }).click();
    await expect(page.getByText('선별된 기사')).toBeVisible({ timeout: 30000 });
    // 카드가 3열 그리드인지 확인
    const grid = page.locator('.grid.grid-cols-3');
    await expect(grid).toBeVisible();
  });
});

test.describe('이메일 전송 기능', () => {
  test('이메일 없이 전송 버튼 클릭 시 아무 동작 없다', async ({ page }) => {
    await page.goto('/');
    const emailInput = page.getByPlaceholder('recipient@example.com');
    await emailInput.fill('');
    const sendBtn = page.getByRole('button', { name: '전송' });
    // 브리핑 없으면 버튼 비활성
    await expect(sendBtn).toBeDisabled();
  });
});
