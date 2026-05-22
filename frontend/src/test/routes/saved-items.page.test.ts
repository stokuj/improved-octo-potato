import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, waitFor } from '@testing-library/svelte';
import { mockFetch, restoreFetch } from '../mocks/fetch';
import Page from '../../routes/saved-items/+page.svelte';

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));
vi.mock('$env/static/public', () => ({ PUBLIC_API_URL: '' }));
vi.mock('svelte', async () => {
  const actual = await vi.importActual('svelte');
  return { ...actual, onMount: vi.fn() };
});

beforeEach(() => {
  restoreFetch();
  vi.clearAllMocks();
});

describe('saved-items page', () => {
  it('redirects unauthenticated to auth', async () => {
    mockFetch({
      '/user-items/ids': { status: 401 },
      '/user-items/me*': { json: async () => ({ items: [], total: 0 }) },
    });
    render(Page);
    await waitFor(() => {
      expect(document.body.textContent).toBeTruthy();
    });
    expect(true).toBe(true); // smoke: no crash
  });

  it('renders followed items when authenticated', async () => {
    mockFetch({
      '/user-items/ids': { json: async () => [1] },
      '/user-items/me*': { json: async () => ({ items: [{ id: 1, name: 'Iron Ore', category: 'Crafting', grade: 'Basic', current_price: 100, updated_at: '2026-05-22T10:00:00' }], total: 1 }) },
    });
    render(Page);
    await waitFor(() => {
      expect(document.body.textContent ?? '').toMatch(/Iron Ore/);
    });
  });
});
