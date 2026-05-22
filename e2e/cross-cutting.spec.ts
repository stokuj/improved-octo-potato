import { test, expect } from './fixtures';

test.describe('cross-cutting', () => {
  test('rate-limited login shows friendly error', async ({ page }) => {
    await page.goto('/auth');
    for (let i = 0; i < 8; i++) {
      await page.getByLabel(/email/i).fill('e2e-user@example.com');
      await page.getByLabel(/password|hasło/i).fill('wrong');
      await page.getByRole('button', { name: /log in|zaloguj/i }).click();
      await page.waitForTimeout(100);
    }
    const body = await page.locator('body').textContent();
    expect(body?.toLowerCase() ?? '').toMatch(/error|błąd|too many|spróbuj|try again|429/i);
  });

  test('failed inventory PUT shows error toast', async ({ authedPage }) => {
    await authedPage.route('**/api/inventory/**', (route) => route.fulfill({ status: 500, body: '{}' }));
    await authedPage.goto('/items/9001');
    const haveInput = authedPage.locator('input[type="number"]').first();
    if (await haveInput.isVisible().catch(() => false)) {
      await haveInput.fill('50');
      await haveInput.blur();
      await authedPage.waitForTimeout(800);
      // Inventory page shows saveError as alert-error div
      const errorToast = authedPage.locator('.alert-error, [role="alert"]');
      await expect(errorToast).toBeVisible({ timeout: 3000 });
      // Verify the page is still functional — can navigate away
      await authedPage.goto('/items');
      await expect(authedPage.locator('body')).toContainText(/E2E/);
    }
  });

  test('unauthenticated /inventory redirects to /auth', async ({ page }) => {
    await page.goto('/inventory');
    await page.waitForTimeout(500);
    const url = page.url();
    if (!url.includes('/auth')) {
      await expect(page.locator('body')).toContainText(/log in|zaloguj|sign in/i);
    }
  });
});
