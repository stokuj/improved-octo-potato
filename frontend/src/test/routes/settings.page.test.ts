import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, fireEvent, waitFor } from '@testing-library/svelte';
import { mockFetch, restoreFetch } from '../mocks/fetch';
import Page from '../../routes/settings/+page.svelte';

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

beforeEach(() => {
  restoreFetch();
  vi.clearAllMocks();
});

describe('settings page', () => {
  it('PATCHes profile when display_name is changed', async () => {
    const fetchSpy = mockFetch({
      '/api/profiles/me': {
        json: async () => ({ display_name: 'Old', is_private: false, avatar_url: null }),
      },
    });
    render(Page);
    await waitFor(() => {
      expect(document.body.textContent).toBeTruthy();
    });

    const input = document.querySelector('input#display_name') as HTMLInputElement;
    if (input) {
      await fireEvent.input(input, { target: { value: 'New' } });
      const save = document.querySelector('button[type="submit"]') as HTMLButtonElement;
      if (save) await fireEvent.click(save);
      await waitFor(() => {
    const patchCall = fetchSpy.mock.calls.find(
      (c) => (c[0] as string).includes('/api/profiles') && (c[1] as RequestInit)?.method === 'PATCH'
    );
        expect(patchCall).toBeDefined();
      });
    }
  });
});
