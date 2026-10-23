import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, fireEvent, waitFor } from '@testing-library/svelte';
import { mockFetch, restoreFetch } from '../mocks/fetch';

const state = vi.hoisted(() => ({ user: { data: null as unknown, isLoggedIn: false, loading: false } }));
vi.mock('$lib/core/auth.svelte.js', () => ({ getUserState: () => state.user }));

import Page from '../../routes/import/+page.svelte';

beforeEach(() => restoreFetch());

function asSuperuser() {
	state.user = { data: { id: 'u1', email: 'a@b.c', is_superuser: true }, isLoggedIn: true, loading: false };
}

describe('import page', () => {
	it('asks signed-out visitors to sign in', () => {
		state.user = { data: null, isLoggedIn: false, loading: false };
		render(Page);
		expect(document.body.textContent).toContain('Sign in to import files.');
		expect(document.querySelector('[data-testid="dropzone"]')).toBeNull();
	});

	it('lets any signed-in user drop files and says market files are admin only', () => {
		state.user = { data: { id: 'u2', email: 'x@y.z', is_superuser: false }, isLoggedIn: true, loading: false };
		render(Page);
		expect(document.querySelector('[data-testid="dropzone"]')).not.toBeNull();
		expect(document.body.textContent).toContain('inventory.csv');
		expect(document.body.textContent).toContain('admin only');
	});

	it('renders one result row per file and the capped error list', async () => {
		asSuperuser();
		const errors = Array.from({ length: 100 }, (_, i) => ({ line: i + 2, reason: 'bad row' }));
		mockFetch({
			'/import': {
				json: async () => [
					{ filename: 'market.csv', kind: 'market', rows: 406, inserted: 140, updated: 0, skipped: 266, error_count: 0, errors: [] },
					{ filename: 'bad.csv', kind: 'listings', rows: 150, inserted: 0, updated: 0, skipped: 0, error_count: 150, errors }
				]
			}
		});
		render(Page);
		const files = [new File(['x'], 'market.csv'), new File(['y'], 'bad.csv')];
		await fireEvent.drop(document.querySelector('[data-testid="dropzone"]')!, { dataTransfer: { files } });
		await waitFor(() => expect(document.querySelectorAll('[data-testid="result-row"]')).toHaveLength(2));
		expect(document.body.textContent).toContain('…and 50 more');
		expect(document.body.textContent).toContain('140');
	});
});
