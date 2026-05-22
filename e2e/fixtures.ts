import { test as base, expect, Page, BrowserContext } from '@playwright/test';

export const E2E_USER = {
  email: 'e2e-user@example.com',
  password: 'E2EPassword123!',
};

export type AuthFixtures = {
  authedContext: BrowserContext;
  authedPage: Page;
};

export const test = base.extend<AuthFixtures>({
  authedContext: async ({ browser }, use) => {
    const ctx = await browser.newContext();
    const page = await ctx.newPage();
    try {
      await page.goto('/auth', { timeout: 10000 });
      await page.getByLabel(/email/i).fill(E2E_USER.email);
      await page.getByLabel(/password/i).fill(E2E_USER.password);
      await page.getByRole('button', { name: /log in|zaloguj/i }).click();
      await page.waitForURL((u) => !u.pathname.startsWith('/auth'), { timeout: 10000 });
    } catch (e) {
      const body = await page.locator('body').textContent().catch(() => 'unavailable');
      throw new Error(
        `authedContext: login failed for ${E2E_USER.email}. ` +
        `Is the E2E stack running (make e2e-up)? Page body: ${body?.slice(0, 200)}`
      );
    }
    await use(ctx);
    await ctx.close();
  },
  authedPage: async ({ authedContext }, use) => {
    const page = await authedContext.newPage();
    await use(page);
  },
});

export { expect };
