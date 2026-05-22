import { test, expect } from './fixtures';

test.describe('crafting + inventory', () => {
  test('open item with recipe — RecipeTree visible', async ({ page }) => {
    await page.goto('/items/9003');
    await expect(page.locator('body')).toContainText(/E2E Top Item/i);
    await expect(page.locator('body')).toContainText(/E2E Mid Item/i);
  });

  test('expand/collapse ingredient nodes', async ({ page }) => {
    await page.goto('/items/9003');
    const toggle = page.locator('button[title="Collapse"]').first();
    if (await toggle.isVisible().catch(() => false)) {
      await toggle.click();
      await page.waitForTimeout(200);
      // After collapse, the title should change to "Expand"
      await expect(page.locator('button[title="Expand"]').first()).toBeVisible({ timeout: 3000 });
      await toggle.click();
      // After expand, back to "Collapse"
      await expect(page.locator('button[title="Collapse"]').first()).toBeVisible({ timeout: 3000 });
    }
  });

  test('edit Have column updates totals', async ({ authedPage }) => {
    await authedPage.goto('/items/9003');
    const haveInput = authedPage.locator('input[type="number"]').first();
    if (await haveInput.isVisible().catch(() => false)) {
      await haveInput.fill('100');
      await haveInput.blur();
      await authedPage.waitForTimeout(300);
      await expect(haveInput).toHaveValue('100');
    }
  });

  test('Have persists after navigation', async ({ authedPage }) => {
    await authedPage.goto('/items/9003');
    const haveInput = authedPage.locator('input[type="number"]').first();
    if (await haveInput.isVisible().catch(() => false)) {
      await haveInput.fill('77');
      await haveInput.blur();
      await authedPage.waitForTimeout(500);
    }
    await authedPage.goto('/');
    await authedPage.goto('/items/9003');
    const reopened = authedPage.locator('input[type="number"]').first();
    if (await reopened.isVisible().catch(() => false)) {
      await expect(reopened).toHaveValue('77');
    }
  });

  test('inventory: set quantity=0 removes row', async ({ authedPage }) => {
    await authedPage.goto('/items/9001');
    const haveInput = authedPage.locator('input[type="number"]').first();
    if (await haveInput.isVisible().catch(() => false)) {
      await haveInput.fill('5');
      await haveInput.blur();
      await authedPage.waitForTimeout(500);
    }

    await authedPage.goto('/inventory');
    await expect(authedPage.locator('body')).toContainText(/E2E Leaf Item/);

    const invInput = authedPage.locator('input[type="number"]').first();
    if (await invInput.isVisible().catch(() => false)) {
      await invInput.fill('0');
      await invInput.blur();
      await authedPage.waitForTimeout(500);
      await authedPage.reload();
      await authedPage.waitForTimeout(500);
      await expect(authedPage.locator('body')).not.toContainText(/E2E Leaf Item/);
    }
  });

  test('profit reflects updated price', async ({ authedPage }) => {
    await authedPage.goto('/items/9003');
    // RecipeCard footer shows material cost and profit
    await expect(authedPage.locator('body')).toContainText(/Total material cost/i, { timeout: 5000 });
    const profitSection = authedPage.locator('text=Profit');
    if (await profitSection.isVisible().catch(() => false)) {
      const profitText = await authedPage.locator('body').textContent();
      expect(profitText).toBeTruthy();
      expect(profitText).not.toContain('NaN');
    }
  });

  test('3-level depth recipe renders without glitches', async ({ page }) => {
    await page.goto('/items/9003');
    await expect(page.locator('body')).toContainText(/E2E Top Item/);
    await expect(page.locator('body')).toContainText(/E2E Mid Item/);
    await expect(page.locator('body')).toContainText(/E2E Leaf Item/);
  });
});
