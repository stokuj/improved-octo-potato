import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/svelte';
import ItemTable from './ItemTable.svelte';
import { mockFetch, restoreFetch } from '../../test/mocks/fetch';

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));
vi.mock('$lib/config.js', () => ({ API_BASE_URL: '' }));
vi.mock('svelte', async () => {
  const actual = await vi.importActual('svelte');
  return { ...actual, onMount: vi.fn() };
});

const sampleItems = [
  { id: 1, name: 'Iron Ore', category: 'Crafting', grade: 'Basic', current_price: 1234, updated_at: '2026-05-22T10:00:00' },
  { id: 2, name: 'Silver Ore', category: 'Crafting', grade: 'Basic', current_price: 5600, updated_at: '2026-05-22T10:00:00' },
];

beforeEach(() => {
  restoreFetch();
  vi.clearAllMocks();
});

describe('ItemTable', () => {
  it('renders rows from fetched data', async () => {
    mockFetch({
      '/items/*': { json: async () => ({ items: sampleItems, total: 2 }) },
      '/user-items/ids': { status: 401 },
    });
    render(ItemTable, { props: { apiEndpoint: '/items/' } });
    await waitFor(() => {
      expect(document.body.textContent).toContain('Iron Ore');
    });
    expect(document.body.textContent).toContain('Silver Ore');
  });

  it('formats price using splitCurrency', async () => {
    mockFetch({
      '/items/*': { json: async () => ({ items: sampleItems, total: 1 }) },
      '/user-items/ids': { status: 401 },
    });
    render(ItemTable, { props: { apiEndpoint: '/items/' } });
    await waitFor(() => {
      const html = document.body.innerHTML;
      expect(html).toMatch(/12/);
      expect(html).toMatch(/34/);
    });
  });

  it('renders empty state when no items returned', async () => {
    mockFetch({
      '/items/*': { json: async () => ({ items: [], total: 0 }) },
      '/user-items/ids': { status: 401 },
    });
    render(ItemTable, { props: { apiEndpoint: '/items/' } });
    await waitFor(() => {
      expect(document.body.textContent).toContain('No items found');
    });
    expect(document.body.textContent).not.toContain('Iron Ore');
  });

  it('clicking item name is a link to detail page', async () => {
    mockFetch({
      '/items/*': { json: async () => ({ items: sampleItems, total: 1 }) },
      '/user-items/ids': { status: 401 },
    });
    render(ItemTable, { props: { apiEndpoint: '/items/' } });
    await waitFor(() => {
      const link = document.querySelector('a[href="/items/1"]');
      expect(link).toBeTruthy();
    });
  });

  it('displays grade pill for each row', async () => {
    mockFetch({
      '/items/*': { json: async () => ({ items: sampleItems, total: 1 }) },
      '/user-items/ids': { status: 401 },
    });
    render(ItemTable, { props: { apiEndpoint: '/items/' } });
    await waitFor(() => {
      const html = document.body.innerHTML;
      expect(html).toMatch(/Basic/i);
    });
  });

  it('handles null current_price gracefully (no NaN)', async () => {
    mockFetch({
      '/items/*': {
        json: async () => ({
          items: [{ id: 99, name: 'Unpriced', category: 'Other', grade: 'Basic', current_price: null, updated_at: '2026-05-22T10:00:00' }],
          total: 1,
        }),
      },
      '/user-items/ids': { status: 401 },
    });
    render(ItemTable, { props: { apiEndpoint: '/items/' } });
    await waitFor(() => {
      expect(document.body.textContent).toContain('Unpriced');
    });
    expect(document.body.textContent).not.toContain('NaN');
  });
});
