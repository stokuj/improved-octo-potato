import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, fireEvent, screen, waitFor } from '@testing-library/svelte';
import { mockFetch, restoreFetch } from '../mocks/fetch';
import Page from '../../routes/auth/+page.svelte';

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

beforeEach(() => {
  restoreFetch();
  vi.clearAllMocks();
});

describe('auth page', () => {
  it('submits login with credentials:include', async () => {
    const fetchSpy = mockFetch({
      '/api/auth/login': { status: 204 },
      '/api/users/me': { json: async () => ({ id: 'u1', email: 'a@b.c' }) },
      '/api/profiles/me': { json: async () => ({ display_name: 'Test', is_private: false }) },
    });
    render(Page);
    const email = document.querySelector('input[type="email"]') as HTMLInputElement;
    const password = document.querySelector('input[type="password"]') as HTMLInputElement;
    expect(email).toBeTruthy();
    expect(password).toBeTruthy();

    await fireEvent.input(email, { target: { value: 'a@b.c' } });
    await fireEvent.input(password, { target: { value: 'pwd123456' } });

    const submit = document.querySelector('button[type="submit"]') || document.querySelector('button');
    if (submit) await fireEvent.click(submit);

    // Wait for fetch
    await waitFor(() => expect(fetchSpy).toHaveBeenCalled());
    const loginCall = fetchSpy.mock.calls.find((c) => (c[0] as string).includes('/api/auth/login'));
    expect(loginCall).toBeDefined();
    const init = loginCall?.[1] as RequestInit | undefined;
    expect(init?.credentials).toBe('include');
  });

  it('shows error on bad credentials', async () => {
    mockFetch({
      '/api/auth/login': { status: 400, json: async () => ({ detail: 'LOGIN_BAD_CREDENTIALS' }) },
    });
    render(Page);
    const email = document.querySelector('input[type="email"]') as HTMLInputElement;
    const password = document.querySelector('input[type="password"]') as HTMLInputElement;
    await fireEvent.input(email, { target: { value: 'a@b.c' } });
    await fireEvent.input(password, { target: { value: 'wrong' } });

    const submit = document.querySelector('button[type="submit"]') || document.querySelector('button');
    if (submit) await fireEvent.click(submit);

    await waitFor(() => {
      expect(document.body.textContent).toMatch(/LOGIN_BAD_CREDENTIALS|error|błąd/i);
    });
  });
});
