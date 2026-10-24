import { describe, it, expect, beforeEach } from 'vitest';
import { render, waitFor, fireEvent, screen } from '@testing-library/svelte';
import { mockFetch, restoreFetch } from '../mocks/fetch';
import { page } from '$app/state';
import { formatCurrency } from '$lib/core/currency';
import Page from '../../routes/market/+page.svelte';

// jsdom has no ResizeObserver; MarketChart only needs observe/disconnect.
globalThis.ResizeObserver ??= class {
	observe() {}
	unobserve() {}
	disconnect() {}
} as unknown as typeof ResizeObserver;

const base = { last_day: null, min_stack: 10, cheapest_real: null, scan_at: null };
const items = [
	{ ...base, id: 2, name: 'Leather', item_type: 16327, item_grade: 0, category: 'Hide', last_day: '2026-10-21', cheapest_real: 4965 },
	{ ...base, id: 5, name: 'Leather', item_type: 16327, item_grade: 2, category: null },
	{ ...base, id: 3, name: 'Nothing', item_type: null, item_grade: null, category: null, cheapest_real: 300 }
];
const day = { day: '2026-10-21', daily_avg: 4702, weekly_avg: 4877, min: 2100, max: 19999, volume: 171924 };
const listings = (rows: unknown[]) => ({ scan_id: rows.length ? 1 : null, captured_at: rows.length ? '2026-10-21T18:38:16' : null, min_stack: 10, listings: rows });
const noResult = { scan_id: 1, captured_at: '2026-10-21T18:38:16', status: 'no_result', rank: 0, unit_price: null, listing_price: null, stack: null, tiny: false };

function routes(daysFor: Record<number, unknown[]>) {
	return mockFetch({
		'/market/items': { json: async () => items },
		'/market/items/2/days*': { json: async () => daysFor[2] ?? [] },
		'/market/items/5/days*': { json: async () => daysFor[5] ?? [] },
		'/market/items/3/days*': { json: async () => daysFor[3] ?? [] },
		'/market/items/2/listings': { json: async () => listings([]) },
		'/market/items/5/listings': { json: async () => listings([]) },
		'/market/items/3/listings': { json: async () => listings([noResult]) }
	});
}

const header = () => document.querySelector('[data-testid="market-header"]')?.textContent ?? '';

beforeEach(() => restoreFetch());

describe('market page', () => {
	it('selects the item from ?item= and loads its days', async () => {
		(page as { url: URL }).url = new URL('http://localhost/market?item=2');
		const fetchSpy = routes({ 2: [day] });
		render(Page);
		await waitFor(() => expect(header()).toContain('Leather'));
		await waitFor(() =>
			expect(fetchSpy.mock.calls.some((c) => String(c[0]).includes('/market/items/2/days'))).toBe(true)
		);
		await waitFor(() => expect(header()).toContain(formatCurrency(4702)));
		expect(header()).toContain(formatCurrency(4965));
		expect(header()).toContain('None · Hide');
	});

	it('shows "No market data" for an item without days', async () => {
		(page as { url: URL }).url = new URL('http://localhost/market?item=3');
		routes({});
		render(Page);
		await waitFor(() => expect(document.body.textContent).toMatch(/no market data/i));
		await waitFor(() => expect(document.body.textContent).toContain('no result'));
	});

	it('listing-only item shows No market data and its cheapest real offer', async () => {
		(page as { url: URL }).url = new URL('http://localhost/market?item=3');
		routes({});
		render(Page);
		await waitFor(() => expect(document.body.textContent).toContain('No market data for this item.'));
		expect(header()).toContain(formatCurrency(300));
		expect(header()).toContain('Other');
	});

	it('falls back to the first item without ?item=', async () => {
		(page as { url: URL }).url = new URL('http://localhost/market');
		routes({ 2: [day] });
		render(Page);
		await waitFor(() => expect(header()).toContain('Leather'));
		expect(screen.getByRole('button', { name: /Leather/ }).getAttribute('aria-current')).toBe('true');
	});

	it('search filters the tree but keeps the selected item on screen', async () => {
		(page as { url: URL }).url = new URL('http://localhost/market?item=2');
		routes({ 2: [day] });
		render(Page);
		await waitFor(() => expect(document.querySelector('[data-testid="market-chart"]')).toBeTruthy());
		await fireEvent.input(screen.getByPlaceholderText('Search items…'), { target: { value: 'noth' } });
		expect(screen.queryByRole('button', { name: /Leather/ })).toBeNull();
		expect(screen.getByRole('button', { name: /Nothing/ })).toBeTruthy();
		await fireEvent.input(screen.getByPlaceholderText('Search items…'), { target: { value: 'zzz' } });
		expect(document.body.textContent).toContain('No items match');
		expect(header()).toContain('Leather');
		expect(document.body.textContent).toContain('Offers now');
		expect(document.querySelector('[data-testid="market-chart"]')).toBeTruthy();
	});

	it('Grade select lists sibling grades and switches ?item=', async () => {
		(page as { url: URL }).url = new URL('http://localhost/market?item=2');
		routes({ 2: [day] });
		render(Page);
		const grade = () => screen.getByLabelText('Grade') as HTMLSelectElement;
		await waitFor(() => expect(grade().value).toBe('2'));
		expect([...grade().options].map((o) => o.textContent?.trim())).toEqual(['None', 'Grand']);
		await fireEvent.change(grade(), { target: { value: '5' } });
		await waitFor(() => expect(page.url.searchParams.get('item')).toBe('5'));
		await waitFor(() => expect(header()).toContain('Grand'));
	});

	it('switching items clears the old chart and a stale error', async () => {
		(page as { url: URL }).url = new URL('http://localhost/market?item=2');
		mockFetch({
			'/market/items': { json: async () => items },
			'/market/items/2/days*': { json: async () => [day] },
			'/market/items/2/listings': { json: async () => listings([]) },
			'/market/items/3/days*': { status: 500 },
			'/market/items/3/listings': { status: 500 }
		});
		render(Page);
		await waitFor(() => expect(document.querySelector('[data-testid="market-chart"]')).toBeTruthy());

		await fireEvent.click(screen.getByRole('button', { name: /Nothing/ }));
		await waitFor(() => expect(document.body.textContent).toContain('Could not load this item.'));
		expect(document.querySelector('[data-testid="market-chart"]')).toBeNull();

		await fireEvent.click(screen.getByRole('button', { name: /Leather/ }));
		await waitFor(() => expect(document.querySelector('[data-testid="market-chart"]')).toBeTruthy());
		expect(document.body.textContent).not.toContain('Could not load this item.');
	});
});
