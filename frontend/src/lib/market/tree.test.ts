import { describe, expect, it } from 'vitest';
import type { ListingRead, MarketDayRead, MarketItemRead } from '$lib/core/types';
import { buildTree, gradeSiblings, nodePrice, shortPrice, sortOffers, tileStats } from './tree';

function item(id: number, name: string, item_type: number | null, item_grade: number | null, category: string | null, cheapest_real: number | null = null): MarketItemRead {
	return { id, name, item_type, item_grade, category, last_day: null, min_stack: 10, cheapest_real, scan_at: null };
}

const a2 = item(1, 'Arrow G2', 1, 2, 'Hide', 500);
const a0 = item(2, 'Arrow', 1, 0, null, 300);
const b = item(3, 'Bronze', 2, 0, 'Metal');
const c = item(4, 'Cloth', null, null, null);

describe('buildTree', () => {
	it('groups by category, Other last, one node per item type with grades sorted', () => {
		const tree = buildTree([c, b, a2, a0], '');
		expect(tree.map((t) => t.name)).toEqual(['Hide', 'Metal', 'Other']);
		expect(tree[0].nodes).toHaveLength(1);
		expect(tree[0].nodes[0].name).toBe('Arrow');
		expect(tree[0].nodes[0].items.map((i) => i.id)).toEqual([2, 1]);
		expect(tree[2].nodes[0].items).toEqual([c]);
		expect(nodePrice(tree[0].nodes[0])).toBe(300);
		expect(nodePrice(tree[1].nodes[0])).toBeNull();
	});

	it('search keeps matching nodes and drops empty categories; no match gives []', () => {
		const tree = buildTree([c, b, a2, a0], '  g2 ');
		expect(tree.map((t) => t.name)).toEqual(['Hide']);
		expect(tree[0].nodes[0].items).toHaveLength(2);
		expect(buildTree([c, b, a2, a0], 'zzz')).toEqual([]);
	});
});

it('shortPrice drops bronze only when gold or silver is shown', () =>
	expect([4965, 21650, 65, null].map(shortPrice)).toEqual(['49s', '2g 16s', '65b', '—']));

it('gradeSiblings returns same-type items by grade, or the item alone without a type', () => {
	expect(gradeSiblings([a2, b, a0, c], a2)).toEqual([a0, a2]);
	expect(gradeSiblings([a2, b, a0, c], c)).toEqual([c]);
});

it('tileStats uses the last day and the mean of up to 7 days before it', () => {
	const days = [10, 20, 30, 40, 50, 60, 70, 80, 9].map(
		(volume, i): MarketDayRead => ({ day: `2026-10-${10 + i}`, daily_avg: 100 + i, weekly_avg: 1, min: 0, max: 0, volume })
	);
	expect(tileStats(days)).toEqual({ avgToday: 108, soldToday: 9, avgVolume: 50 });
	expect(tileStats(days.slice(-1))).toEqual({ avgToday: 108, soldToday: 9, avgVolume: null });
	expect(tileStats([])).toEqual({ avgToday: null, soldToday: null, avgVolume: null });
});

it('sortOffers keeps ok rows and sorts by the chosen key', () => {
	const row = (rank: number, status: string, unit_price: number | null, stack: number | null): ListingRead => ({
		scan_id: 1, captured_at: '2026-10-21T10:00:00', status, rank, unit_price, listing_price: null, stack, tiny: false
	});
	const rows = [row(1, 'ok', 200, 5), row(2, 'ok', 100, 50), row(0, 'no_buyout', null, null), row(3, 'ok', 300, 20)];
	const copy = [...rows];
	expect(sortOffers(rows, 'unit-asc').map((r) => r.rank)).toEqual([2, 1, 3]);
	expect(sortOffers(rows, 'unit-desc').map((r) => r.rank)).toEqual([3, 1, 2]);
	expect(sortOffers(rows, 'stack-desc').map((r) => r.rank)).toEqual([2, 3, 1]);
	expect(rows).toEqual(copy);
});
