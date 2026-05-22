import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, fireEvent, waitFor } from '@testing-library/svelte';
import { mockFetch, restoreFetch } from '../mocks/fetch';
import Page from '../../routes/inventory/+page.svelte';

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));
vi.mock('$env/static/public', () => ({ PUBLIC_API_URL: '' }));

beforeEach(() => {
  restoreFetch();
  vi.clearAllMocks();
});

describe('inventory page', () => {
  it('sends PUT when quantity is edited', async () => {
    const fetchSpy = mockFetch({
      '/items/*': {
        json: async () => ({
          items: [{ id: 1, name: 'Iron Ore', category: 'Other', grade: 'Basic', current_price: 100, updated_at: '2026-05-22T10:00:00' }],
          total: 1,
        }),
      },
      '/inventory/': {
        json: async () => [{ item_id: 1, quantity: 5 }],
      },
      '/inventory/1': { status: 204 },
    });
    render(Page);
    await waitFor(() => {
      expect(document.body.textContent).toMatch(/Iron Ore/);
    });

    const input = document.querySelector('input[type="number"]') as HTMLInputElement;
    if (input) {
      await fireEvent.input(input, { target: { value: '10' } });
      // debounce 400ms, so wait a bit
      await new Promise((r) => setTimeout(r, 500));
    }

    const putCall = fetchSpy.mock.calls.find(
      (c) => (c[0] as string).includes('/inventory/1') && (c[1] as RequestInit)?.method === 'PUT'
    );
    expect(putCall).toBeDefined();
  });
});
