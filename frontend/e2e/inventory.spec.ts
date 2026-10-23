import { test, expect } from './fixtures';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// Anonymised: made-up character names, never real ones.
const INVENTORY = path.resolve(path.dirname(fileURLToPath(import.meta.url)), 'fixtures/inventory.csv');

test.describe.configure({ mode: 'serial' });

test.describe('inventory journey', () => {
  test('upload inventory.csv on /import', async ({ authedPage }) => {
    await authedPage.goto('/import');
    await authedPage.locator('input[type="file"]').setInputFiles([INVENTORY]);
    const row = authedPage.getByTestId('result-row');
    await expect(row).toHaveCount(1);
    await expect(row.locator('td').nth(1)).toHaveText('inventory');
  });

  test('/inventory shows a tab per character and switches bags', async ({ authedPage }) => {
    await authedPage.goto('/inventory');
    await expect(authedPage.getByRole('tab', { name: 'Alpha · 20' })).toHaveAttribute('aria-selected', 'true');
    await expect(authedPage.getByTestId('tile')).toHaveCount(20);

    await authedPage.getByRole('tab', { name: 'Bravo · 20' }).click();
    await expect(authedPage).toHaveURL(/character=Bravo/);
    const tile = authedPage.getByRole('img', { name: /Copper Ingot/ });
    await tile.focus();
    await expect(tile).toHaveAttribute('aria-label', /×3/);
  });
});
