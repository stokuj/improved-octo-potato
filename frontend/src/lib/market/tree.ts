// Pure helpers for the Auction House page: category tree, short prices, grades, tiles, offer sort.
import { formatCurrency } from '$lib/core/currency';
import type { ListingRead, MarketDayRead, MarketItemRead } from '$lib/core/types';

export type TreeNode = { key: string; name: string; items: MarketItemRead[] };
export type TreeCategory = { name: string; nodes: TreeNode[] };

const OTHER = 'Other';
const byGrade = (a: MarketItemRead, b: MarketItemRead) => (a.item_grade ?? 0) - (b.item_grade ?? 0);

export function buildTree(items: MarketItemRead[], query: string): TreeCategory[] {
	const nodes = new Map<string, MarketItemRead[]>();
	for (const i of items) {
		const key = i.item_type == null ? `id:${i.id}` : `type:${i.item_type}`;
		nodes.set(key, [...(nodes.get(key) ?? []), i]);
	}
	const q = query.trim().toLowerCase();
	const cats = new Map<string, TreeNode[]>();
	for (const [key, group] of nodes) {
		if (q && !group.some((i) => i.name.toLowerCase().includes(q))) continue;
		const sorted = [...group].sort(byGrade);
		const cat = sorted.find((i) => i.category != null)?.category ?? OTHER;
		cats.set(cat, [...(cats.get(cat) ?? []), { key, name: sorted[0].name, items: sorted }]);
	}
	return [...cats]
		.map(([name, ns]) => ({ name, nodes: ns.sort((a, b) => a.name.localeCompare(b.name)) }))
		.sort((a, b) => (a.name === OTHER ? 1 : b.name === OTHER ? -1 : a.name.localeCompare(b.name)));
}

export function shortPrice(copper: number | null): string {
	if (copper == null) return '—';
	const full = formatCurrency(copper);
	return /[gs]/.test(full) ? full.replace(/ \d+b$/, '') : full;
}

export function nodePrice(node: TreeNode): number | null {
	const prices = node.items.map((i) => i.cheapest_real).filter((p): p is number => p != null);
	return prices.length ? Math.min(...prices) : null;
}

export function gradeSiblings(items: MarketItemRead[], item: MarketItemRead): MarketItemRead[] {
	if (item.item_type == null) return [item];
	return items.filter((i) => i.item_type === item.item_type).sort(byGrade);
}

export function tileStats(days: MarketDayRead[]): {
	avgToday: number | null;
	soldToday: number | null;
	avgVolume: number | null;
} {
	const last = days.at(-1);
	const before = days.slice(-8, -1);
	return {
		avgToday: last?.daily_avg ?? null,
		soldToday: last?.volume ?? null,
		avgVolume: before.length ? before.reduce((s, d) => s + d.volume, 0) / before.length : null
	};
}

export type OfferSort = 'unit-asc' | 'unit-desc' | 'stack-desc';

export const OFFER_SORTS: { value: OfferSort; label: string }[] = [
	{ value: 'unit-asc', label: 'Unit price ↑' },
	{ value: 'unit-desc', label: 'Unit price ↓' },
	{ value: 'stack-desc', label: 'Stack size ↓' }
];

export function sortOffers(listings: ListingRead[], sort: OfferSort): ListingRead[] {
	const ok = listings.filter((l) => l.status === 'ok');
	const unit = (l: ListingRead) => l.unit_price ?? 0;
	const cmp = {
		'unit-asc': (a: ListingRead, b: ListingRead) => unit(a) - unit(b),
		'unit-desc': (a: ListingRead, b: ListingRead) => unit(b) - unit(a),
		'stack-desc': (a: ListingRead, b: ListingRead) => (b.stack ?? 0) - (a.stack ?? 0)
	}[sort];
	return ok.sort(cmp);
}
