import { test, expect, E2E_USER } from './fixtures';

test.describe('auth flow', () => {
  test('login as the seeded admin lands on /market', async ({ page }) => {
    await page.goto('/auth');
    await page.getByLabel(/email/i).fill(E2E_USER.email);
    await page.getByLabel(/password/i).fill(E2E_USER.password);
    await page.getByRole('button', { name: /sign in/i }).click();
    await page.waitForURL((u) => u.pathname.startsWith('/market'));
  });

  test('login with bad password shows error, no cookie', async ({ page, context }) => {
    await page.goto('/auth');
    await page.getByLabel(/email/i).fill(E2E_USER.email);
    await page.getByLabel(/password/i).fill('WRONG');
    await page.getByRole('button', { name: /sign in/i }).click();
    await expect(page.getByRole('alert')).toBeVisible();
    expect(page.url()).toContain('/auth');
    const cookies = await context.cookies();
    expect(cookies.find((c) => c.name.includes('fastapiusersauth'))).toBeUndefined();
  });

  test('there is no register option', async ({ page }) => {
    await page.goto('/auth');
    await expect(page.getByRole('button', { name: /register/i })).toHaveCount(0);
  });

  test('logout clears session', async ({ authedPage }) => {
    await authedPage.goto('/market');
    await authedPage.getByRole('button', { name: E2E_USER.email[0].toUpperCase(), exact: true }).click();
    await authedPage.getByRole('button', { name: /sign out/i }).click();
    await authedPage.waitForURL((u) => u.pathname.startsWith('/auth'));
    await authedPage.goto('/import');
    await expect(authedPage.locator('body')).toContainText('Only the admin can import files.');
  });
});
