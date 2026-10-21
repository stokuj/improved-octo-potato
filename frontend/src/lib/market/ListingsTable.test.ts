import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import ListingsTable from './ListingsTable.svelte';
import { formatCurrency } from '$lib/core/currency';

const base = { scan_id: 1, captured_at: '2026-10-21T18:38:16', listing_price: null, stack: null };

describe('ListingsTable', () => {
	it('renders ok rows with formatted unit price', () => {
		render(ListingsTable, {
			listings: [{ ...base, status: 'ok', rank: 1, unit_price: 4650, listing_price: 2418000, stack: 520 }]
		});
		expect(screen.getByText(formatCurrency(4650))).toBeTruthy();
		expect(screen.getByText('520')).toBeTruthy();
	});

	it('shows a non-ok status as words', () => {
		render(ListingsTable, {
			listings: [{ ...base, status: 'no_result', rank: 0, unit_price: null }]
		});
		expect(screen.getByText('no result')).toBeTruthy();
	});

	it('says when there are no listings', () => {
		render(ListingsTable, { listings: [] });
		expect(document.body.textContent).toMatch(/no listings/i);
	});
});
