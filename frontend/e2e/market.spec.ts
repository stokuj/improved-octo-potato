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

  test('/market shows the tree, the offers and the chart', async ({ authedPage }) => {
    await authedPage.goto('/market');
    await expect(authedPage.getByTestId('category-tree').locator('button[aria-current="true"]')).toHaveCount(1);
    await expect(authedPage.getByText('Offers now')).toBeVisible();
    await expect(authedPage.getByTestId('market-chart').locator('svg')).toBeVisible();
  });

  test('clicking another leaf updates the URL and the header', async ({ authedPage }) => {
    await authedPage.goto('/market');
    const other = authedPage
      .getByTestId('category-tree')
      .locator('button:not([aria-expanded]):not([aria-current])')
      .first();
    const name = (await other.locator('span').first().textContent())!.trim();
    const before = new URL(authedPage.url()).searchParams.get('item');
    await other.click();
    await authedPage.waitForURL((u) => u.searchParams.get('item') !== before && u.searchParams.has('item'));
    await expect(authedPage.getByTestId('market-header')).toContainText(name);
  });

  test('anonymous visitors can read /market but not import', async ({ browser }) => {
    const ctx = await browser.newContext();
    const page = await ctx.newPage();
    await page.goto('/market');
    await expect(page.getByPlaceholder('Search items…')).toBeVisible();
    await page.goto('/import');
    await expect(page.locator('body')).toContainText('Sign in to import files.');
    await ctx.close();
  });
});
