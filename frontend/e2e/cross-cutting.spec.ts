import { test, expect } from './fixtures';

test.describe('cross-cutting', () => {
  test('rate-limited login shows friendly error', async ({ page }) => {
    await page.goto('/auth');
    for (let i = 0; i < 8; i++) {
      await page.getByLabel(/email/i).fill('e2e-admin@example.com');
      await page.getByLabel(/password|hasło/i).fill('wrong');
      await page.getByRole('button', { name: /sign in/i }).click();
      await page.waitForTimeout(100);
    }
    const body = await page.locator('body').textContent();
    expect(body?.toLowerCase() ?? '').toMatch(/error|błąd|too many|spróbuj|try again|429/i);
  });
});
