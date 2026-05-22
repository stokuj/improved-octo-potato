import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, waitFor } from '@testing-library/svelte';
import { mockFetch, restoreFetch } from '../mocks/fetch';
import Page from '../../routes/items/[id]/+page.svelte';

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));
vi.mock('$app/state', () => ({ page: { params: { id: '1' } } }));
vi.mock('$env/static/public', () => ({ PUBLIC_API_URL: '' }));
vi.mock('echarts', () => ({
  default: { init: vi.fn(() => ({ setOption: vi.fn(), dispose: vi.fn(), resize: vi.fn() })) },
  init: vi.fn(() => ({ setOption: vi.fn(), dispose: vi.fn(), resize: vi.fn() })),
}));

beforeEach(() => {
  restoreFetch();
  vi.clearAllMocks();
});

describe('items detail page', () => {
  it('renders item detail without crashing', async () => {
    mockFetch({
      '/items/1': {
        json: async () => ({
          id: 1, name: 'Iron Ore', category: 'Crafting', grade: 'Basic', current_price: 100, updated_at: '2026-05-22T10:00:00',
        }),
      },
      '/items/1/price-history': { json: async () => [] },
      '/crafting/1/calculate': { status: 404 },
      '/inventory/for-recipe/1': { status: 401 },
    });
    expect(() => render(Page)).not.toThrow();
    await waitFor(() => {
      expect(document.body.textContent).toMatch(/Iron Ore/);
    });
  });
});
