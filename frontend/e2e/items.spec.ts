import { test, expect } from './fixtures';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// Anonymised: made-up character names, never real ones.
const dir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), 'fixtures');
const INVENTORY = path.join(dir, 'inventory.csv');
const CHESTS = path.join(dir, 'chests.csv');

test.describe.configure({ mode: 'serial' });

test.describe('items journey', () => {
  test('upload inventory.csv and chests.csv on /import', async ({ authedPage }) => {
    await authedPage.goto('/import');
    await authedPage.locator('input[type="file"]').setInputFiles([INVENTORY, CHESTS]);
    const kinds = authedPage.getByTestId('result-row').locator('td:nth-child(2)');
    await expect(kinds).toHaveText(['inventory', 'chests']);
  });

  test('/items shows characters and chests, each side switches on its own', async ({ authedPage }) => {
    await authedPage.goto('/items');
    const characters = authedPage.getByRole('region', { name: 'Characters' });
    const chests = authedPage.getByRole('region', { name: 'House chests' });
    await expect(characters.getByRole('heading', { name: 'Alpha' })).toBeVisible();
    await expect(characters.getByRole('heading', { name: 'Bravo' })).toBeVisible();
    await expect(chests.getByTestId('grid-panel')).toHaveCount(1);

    await characters.getByRole('tab', { name: 'Bravo' }).click();
    await expect(authedPage).toHaveURL(/character=Bravo/);
    const tile = characters.getByRole('img', { name: /Copper Ingot/ });
    await tile.focus();
    await expect(tile).toHaveAttribute('aria-label', /×3/);

    await chests.getByRole('tab', { name: 'Treehouse' }).click();
    await expect(authedPage).toHaveURL(/character=Bravo&chest=1/);
    await expect(chests.getByTestId('grid-panel')).toContainText('saved by Alpha');
  });

  test('/inventory redirects to /items', async ({ authedPage }) => {
    await authedPage.goto('/inventory?character=Bravo');
    await expect(authedPage).toHaveURL(/\/items\?character=Bravo$/);
  });
});
