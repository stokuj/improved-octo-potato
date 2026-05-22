import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, waitFor } from '@testing-library/svelte';
import { mockFetch, restoreFetch } from '../mocks/fetch';
import Page from '../../routes/items/+page.svelte';

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));
vi.mock('$lib/config.js', () => ({ API_BASE_URL: '' }));
vi.mock('svelte', async () => {
  const actual = await vi.importActual('svelte');
  return { ...actual, onMount: vi.fn() };
});

beforeEach(() => {
  restoreFetch();
  vi.clearAllMocks();
});

const items = [
  { id: 1, name: 'Iron Ore', category: 'Crafting', grade: 'Basic', current_price: 100, updated_at: '2026-05-22T10:00:00' },
  { id: 2, name: 'Silver Ore', category: 'Crafting', grade: 'Basic', current_price: 200, updated_at: '2026-05-22T10:00:00' },
];

describe('items page', () => {
  it('renders ItemTable with fetched items', async () => {
    mockFetch({
      '/items/*': { json: async () => ({ items, total: 2 }) },
      '/user-items/ids': { status: 401 },
    });
    render(Page);
    await waitFor(() => {
      expect(document.body.textContent).toMatch(/Iron Ore/);
    });
  });
});
