import { test as base, expect, Page, BrowserContext } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const E2E_USER = {
  email: 'e2e-admin@example.com',
  password: 'E2EPassword123!',
};

// Written once by auth.setup.ts; login is rate-limited (5/min), so tests reuse it.
export const AUTH_FILE = path.join(path.dirname(fileURLToPath(import.meta.url)), '.auth/admin.json');

export type AuthFixtures = {
  authedContext: BrowserContext;
  authedPage: Page;
};

export const test = base.extend<AuthFixtures>({
  authedContext: async ({ browser }, use) => {
    const ctx = await browser.newContext({ storageState: AUTH_FILE });
    await use(ctx);
    await ctx.close();
  },
  authedPage: async ({ authedContext }, use) => {
    const page = await authedContext.newPage();
    await use(page);
  },
});

export { expect };
