import { test, expect } from './fixtures';

test.describe('items', () => {
  test('items list loads and displays seeded items', async ({ page }) => {
    await page.goto('/items');
    await expect(page.locator('body')).toContainText(/E2E/, { timeout: 5000 });
    const itemLinks = page.locator('a[href^="/items/"]');
    await expect(itemLinks.first()).toBeVisible({ timeout: 5000 });
    const count = await itemLinks.count();
    expect(count).toBeGreaterThan(0);
  });

  test('search filters case-insensitively', async ({ page }) => {
    await page.goto('/items');
    const search = page.getByPlaceholder(/search|szukaj/i).or(page.getByRole('searchbox'));
    await search.fill('leaf');
    await page.waitForTimeout(300);
    await expect(page.locator('body')).toContainText(/E2E Leaf Item/i);
  });

  test('item detail page renders chart container', async ({ page }) => {
    await page.goto('/items/9001');
    await page.waitForTimeout(500);
    const chart = page.locator('canvas, [data-testid="price-chart"], .echarts');
    await expect(chart.first()).toBeVisible({ timeout: 5000 });
  });
});
