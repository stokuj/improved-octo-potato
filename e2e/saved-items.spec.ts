import { test, expect } from './fixtures';

test.describe('saved items', () => {
  test('follow item appears on /saved-items', async ({ authedPage }) => {
    await authedPage.goto('/items/9001');
    const followBtn = authedPage.getByRole('button', { name: /follow|śledź|save/i });
    if (await followBtn.isVisible().catch(() => false)) {
      await followBtn.click();
      await authedPage.waitForTimeout(300);
    }

    await authedPage.goto('/saved-items');
    await expect(authedPage.locator('body')).toContainText(/E2E Leaf Item/, { timeout: 5000 });
  });

  test('unfollow from saved-items removes item', async ({ authedPage }) => {
    await authedPage.goto('/saved-items');
    await expect(authedPage.locator('body')).toContainText(/E2E Leaf Item/, { timeout: 5000 });
    const saveBtn = authedPage.locator('button[aria-label="Save item"]').first();
    if (await saveBtn.isVisible().catch(() => false)) {
      await saveBtn.click();
      await authedPage.waitForTimeout(500);
      // After unfollow on saved-items page, the table reloads via loadItems(true)
      await expect(authedPage.locator('body')).not.toContainText(/E2E Leaf Item/, { timeout: 5000 });
    }
  });
});
