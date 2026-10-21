import { test, expect } from './fixtures';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const FIXTURES = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../backend/tests/market/fixtures');
const files = [path.join(FIXTURES, 'market.csv'), path.join(FIXTURES, 'listings.csv')];

test.describe.configure({ mode: 'serial' });

async function uploadAndReadRows(page: import('@playwright/test').Page) {
  await page.goto('/import');
  await page.locator('input[type="file"]').setInputFiles(files);
  const rows = page.getByTestId('result-row');
  await expect(rows).toHaveCount(2);
  return Promise.all(
    [0, 1].map(async (i) =>
      (await rows.nth(i).locator('td').allTextContents()).slice(2).map((v) => Number(v.trim()))
    )
  );
}

test.describe('market journey', () => {
  test('admin imports the sample CSVs; re-upload adds nothing', async ({ authedPage }) => {
    for (const [rows, inserted, updated, skipped, errors] of await uploadAndReadRows(authedPage)) {
      expect(inserted + updated + skipped + errors).toBe(rows);
    }
    for (const [, inserted, updated] of await uploadAndReadRows(authedPage)) {
      expect([inserted, updated]).toEqual([0, 0]);
    }
  });

  test('/market shows chart, offers and the summary table', async ({ authedPage }) => {
    await authedPage.goto('/market');
    await expect(authedPage.getByTestId('market-chart').locator('svg')).toBeVisible();
    await expect(authedPage.getByText('Cheapest offers now')).toBeVisible();
    await expect(authedPage.locator('section:has-text("Today vs last 7 days") tbody tr')).toHaveCount(10);
  });

  test('choosing another item updates the URL and the offers', async ({ authedPage }) => {
    await authedPage.goto('/market');
    const select = authedPage.locator('select');
    const before = await select.inputValue();
    const other = await select.locator('option').nth(1).getAttribute('value');
    expect(other).not.toBe(before);
    await select.selectOption(other!);
    await authedPage.waitForURL((u) => u.searchParams.get('item') === other);
    await expect(authedPage.locator('h2', { hasText: '— last 14 days' })).toContainText(
      (await select.locator(`option[value="${other}"]`).textContent())!.trim()
    );
  });

  test('anonymous visitors can read /market but not import', async ({ browser }) => {
    const ctx = await browser.newContext();
    const page = await ctx.newPage();
    await page.goto('/market');
    await expect(page.locator('select')).toBeVisible();
    await page.goto('/import');
    await expect(page.locator('body')).toContainText('Only the admin can import files.');
    await ctx.close();
  });
});
