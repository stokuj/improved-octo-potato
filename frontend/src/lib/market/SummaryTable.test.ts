import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent, screen } from '@testing-library/svelte';
import SummaryTable from './SummaryTable.svelte';

const row = (item_id: number, name: string, change_pct: number | null) => ({
	item_id,
	name,
	day: '2026-10-21',
	today_avg: 100,
	avg_7d: 100,
	change_pct,
	sold_today: 10,
	avg_daily_volume: 12.5
});
const rows = [row(1, 'Alpha', 0.05), row(2, 'Beta', -0.1), row(3, 'Gamma', null)];

const names = () =>
	[...document.querySelectorAll('tbody tr')].map((tr) => tr.querySelector('td')?.textContent?.trim());

describe('SummaryTable', () => {
	it('sorts by name by default', () => {
		render(SummaryTable, { rows: [rows[2], rows[0], rows[1]], selectedId: null, onSelect: () => {} });
		expect(names()).toEqual(['Alpha', 'Beta', 'Gamma']);
	});

	it('clicking Change sorts descending, then ascending, nulls last', async () => {
		render(SummaryTable, { rows, selectedId: null, onSelect: () => {} });
		await fireEvent.click(screen.getByRole('button', { name: /change/i }));
		expect(names()).toEqual(['Alpha', 'Beta', 'Gamma']);
		await fireEvent.click(screen.getByRole('button', { name: /change/i }));
		expect(names()).toEqual(['Beta', 'Alpha', 'Gamma']);
	});

	it('formats change and shows a dash for null', () => {
		render(SummaryTable, { rows, selectedId: null, onSelect: () => {} });
		expect(screen.getByText('+5.0%')).toBeTruthy();
		expect(screen.getByText('-10.0%')).toBeTruthy();
		expect(screen.getByText('—')).toBeTruthy();
	});

	it('row click selects the item', async () => {
		const onSelect = vi.fn();
		render(SummaryTable, { rows, selectedId: null, onSelect });
		await fireEvent.click(screen.getByText('Beta'));
		expect(onSelect).toHaveBeenCalledWith(2);
	});
});
