import { test, expect } from './fixtures';
import { randomBytes } from 'node:crypto';

const newEmail = () => `e2e-${randomBytes(4).toString('hex')}@example.com`;

test.describe('auth flow', () => {
  test('register new user redirects away from /auth', async ({ page }) => {
    const email = newEmail();
    await page.goto('/auth');
    await page.getByLabel(/email/i).fill(email);
    await page.getByLabel(/password|hasło/i).fill('Password123!');
    const registerBtn = page.getByRole('button', { name: /register|zarejestruj|sign up/i });
    if (await registerBtn.isVisible().catch(() => false)) {
      await registerBtn.click();
    } else {
      await page.getByRole('button', { name: /log in|zaloguj/i }).click();
    }
    await page.waitForURL((u) => !u.pathname.startsWith('/auth'), { timeout: 5000 });
    expect(page.url()).not.toContain('/auth');
  });

  test('login existing seeded user', async ({ page }) => {
    await page.goto('/auth');
    await page.getByLabel(/email/i).fill('e2e-user@example.com');
    await page.getByLabel(/password|hasło/i).fill('E2EPassword123!');
    await page.getByRole('button', { name: /log in|zaloguj/i }).click();
    await page.waitForURL((u) => !u.pathname.startsWith('/auth'));
    expect(page.url()).not.toContain('/auth');
  });

  test('login with bad password shows error, no cookie', async ({ page, context }) => {
    await page.goto('/auth');
    await page.getByLabel(/email/i).fill('e2e-user@example.com');
    await page.getByLabel(/password|hasło/i).fill('WRONG');
    await page.getByRole('button', { name: /log in|zaloguj/i }).click();
    await page.waitForTimeout(1000);
    expect(page.url()).toContain('/auth');
    const cookies = await context.cookies();
    expect(cookies.find((c) => c.name.includes('auth') || c.name.includes('fastapiusersauth'))).toBeUndefined();
  });

  test('logout clears session', async ({ authedPage }) => {
    await authedPage.goto('/');
    const logoutBtn = authedPage.getByRole('button', { name: /logout|wyloguj/i });
    if (await logoutBtn.isVisible().catch(() => false)) {
      await logoutBtn.click();
    } else {
      const logoutLink = authedPage.getByRole('link', { name: /logout|wyloguj/i });
      await logoutLink.click();
    }
    await authedPage.waitForTimeout(500);
    await authedPage.goto('/saved-items');
    await expect(authedPage.locator('body')).toContainText(/log in|zaloguj|sign in/i, { timeout: 5000 });
  });

  test('settings page persists display_name', async ({ authedPage }) => {
    await authedPage.goto('/settings');
    const newName = `Name-${Date.now()}`;
    const input = authedPage.getByLabel(/display.?name|nazwa/i);
    await input.fill(newName);
    await authedPage.getByRole('button', { name: /save|zapisz/i }).click();
    await authedPage.waitForTimeout(500);
    await authedPage.reload();
    await expect(input).toHaveValue(newName);
  });
});
