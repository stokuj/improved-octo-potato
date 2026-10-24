import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import OffersTable from './OffersTable.svelte';
import { formatCurrency } from '$lib/core/currency';
import type { ListingRead, ListingsRead, MarketItemRead } from '$lib/core/types';

const item: MarketItemRead = {
	id: 2, name: 'Leather', item_type: 16327, item_grade: 0, category: 'Hide', last_day: null,
	min_stack: 200, cheapest_real: 4965, scan_at: null
};
const row = (rank: number, unit_price: number, stack: number, tiny: boolean): ListingRead => ({
	scan_id: 1, captured_at: '2026-10-21T18:38:16', status: 'ok', rank, unit_price, listing_price: unit_price * stack, stack, tiny
});
const data = (listings: ListingRead[]): ListingsRead => ({
	scan_id: listings.length ? 1 : null, captured_at: listings.length ? '2026-10-21T18:38:16' : null, min_stack: 200, listings
});

describe('OffersTable', () => {
	it('shows a tiny stack badge only on tiny rows', () => {
		render(OffersTable, { data: data([row(1, 2165, 2, true), row(2, 4965, 520, false)]), item, sort: 'unit-asc' });
		const badges = screen.getAllByText('tiny stack');
		expect(badges).toHaveLength(1);
		expect(badges[0].getAttribute('title')).toBe('Smaller than a useful amount: likely bait');
		expect(badges[0].closest('tr')?.textContent).toContain(formatCurrency(2165));
	});

	it('sorts by the given key and shows the scan line with top N', () => {
		render(OffersTable, { data: data([row(1, 300, 5, false), row(2, 100, 50, false), row(3, 200, 20, false)]), item, sort: 'stack-desc' });
		const stacks = [...document.querySelectorAll('tbody tr')].map((tr) => tr.querySelectorAll('td')[1].textContent?.trim());
		expect(stacks).toEqual(['50', '20', '5']);
		expect(document.body.textContent).toMatch(/Scan .+ · page 1 \(top 3\)/);
	});

	it('shows status words and the empty message', () => {
		const status: ListingRead = { ...row(0, 0, 0, false), status: 'no_result', unit_price: null, listing_price: null, stack: null };
		const { unmount } = render(OffersTable, { data: data([status]), item, sort: 'unit-asc' });
		expect(screen.getByText('no result')).toBeTruthy();
		unmount();
		render(OffersTable, { data: data([]), item, sort: 'unit-asc' });
		expect(document.body.textContent).toContain('No listings imported for this item yet.');
	});
});
