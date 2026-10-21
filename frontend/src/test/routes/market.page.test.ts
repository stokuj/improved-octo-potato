import { describe, it, expect, beforeEach } from 'vitest';
import { render, waitFor, fireEvent } from '@testing-library/svelte';
import { mockFetch, restoreFetch } from '../mocks/fetch';
import { page } from '$app/state';
import Page from '../../routes/market/+page.svelte';

const items = [
	{ id: 2, name: 'Leather', item_type: 16327, item_grade: 0, last_day: '2026-10-21' },
	{ id: 3, name: 'Nothing', item_type: null, item_grade: null, last_day: null }
];
const day = { day: '2026-10-21', daily_avg: 4702, weekly_avg: 4877, min: 2100, max: 19999, volume: 171924 };
const summary = [
	{ item_id: 2, name: 'Leather', day: '2026-10-21', today_avg: 4702, avg_7d: 4902, change_pct: -0.0408, sold_today: 171924, avg_daily_volume: 94566.6 }
];

function routes(daysFor: Record<number, unknown[]>) {
	return mockFetch({
		'/market/items': { json: async () => items },
		'/market/items/2/days*': { json: async () => daysFor[2] ?? [] },
		'/market/items/3/days*': { json: async () => daysFor[3] ?? [] },
		'/market/items/2/listings': { json: async () => [] },
		'/market/items/3/listings': { json: async () => [{ scan_id: 1, captured_at: '2026-10-21T18:38:16', status: 'no_result', rank: 0, unit_price: null, listing_price: null, stack: null }] },
		'/market/summary': { json: async () => summary }
	});
}

beforeEach(() => restoreFetch());

describe('market page', () => {
	it('selects the item from ?item= and loads its days', async () => {
		(page as { url: URL }).url = new URL('http://localhost/market?item=2');
		const fetchSpy = routes({ 2: [day] });
		render(Page);
		await waitFor(() => {
			const select = document.querySelector('select') as HTMLSelectElement;
			expect(select.value).toBe('2');
		});
		await waitFor(() =>
			expect(fetchSpy.mock.calls.some((c) => String(c[0]).includes('/market/items/2/days'))).toBe(true)
		);
		await waitFor(() => expect(document.body.textContent).toContain('Leather'));
		await waitFor(() => expect(document.body.textContent).toContain('-4.1%'));
	});

	it('shows "No market data" for an item without days', async () => {
		(page as { url: URL }).url = new URL('http://localhost/market?item=3');
		routes({});
		render(Page);
		await waitFor(() => expect(document.body.textContent).toMatch(/no market data/i));
		await waitFor(() => expect(document.body.textContent).toContain('no result'));
	});

	it('falls back to the first item without ?item=', async () => {
		(page as { url: URL }).url = new URL('http://localhost/market');
		routes({ 2: [day] });
		render(Page);
		await waitFor(() => expect((document.querySelector('select') as HTMLSelectElement).value).toBe('2'));
	});

	it('switching items clears the old chart and a stale error', async () => {
		(page as { url: URL }).url = new URL('http://localhost/market?item=2');
		mockFetch({
			'/market/items': { json: async () => items },
			'/market/items/2/days*': { json: async () => [day] },
			'/market/items/2/listings': { json: async () => [] },
			'/market/items/3/days*': { status: 500 },
			'/market/items/3/listings': { status: 500 },
			'/market/summary': { json: async () => summary }
		});
		render(Page);
		await waitFor(() => expect(document.querySelector('[data-testid="market-chart"]')).toBeTruthy());
		const select = () => document.querySelector('select') as HTMLSelectElement;

		await fireEvent.change(select(), { target: { value: '3' } });
		await waitFor(() => expect(document.body.textContent).toContain('Could not load this item.'));
		expect(document.querySelector('[data-testid="market-chart"]')).toBeNull();

		await fireEvent.change(select(), { target: { value: '2' } });
		await waitFor(() => expect(document.querySelector('[data-testid="market-chart"]')).toBeTruthy());
		expect(document.body.textContent).not.toContain('Could not load this item.');
	});
});
