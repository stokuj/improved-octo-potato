import { test as setup, expect } from '@playwright/test';
import { AUTH_FILE, E2E_USER } from './fixtures';

setup('log in as the e2e admin', async ({ page }) => {
  await page.goto('/auth');
  await page.getByLabel(/email/i).fill(E2E_USER.email);
  await page.getByLabel(/password/i).fill(E2E_USER.password);
  await page.getByRole('button', { name: /sign in/i }).click();
  await page.waitForURL((u) => u.pathname.startsWith('/market'));
  await expect(page.getByRole('link', { name: 'Import' })).toBeVisible();
  await page.context().storageState({ path: AUTH_FILE });
});
