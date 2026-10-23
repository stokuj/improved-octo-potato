// Pure helpers for the item grids: slot position, tile label, change dot, tabs and times.
import type { SlotRead } from '$lib/core/types';
import { gradeName } from './grades';

export const COLUMNS = 10; // the in-game bag grid; slot 1 is top-left, rows fill left to right

export function slotPosition(slot: number): { row: number; col: number } {
	return { row: Math.floor((slot - 1) / COLUMNS) + 1, col: ((slot - 1) % COLUMNS) + 1 };
}

export function tileLabel(s: SlotRead): string {
	if (s.item == null) return `Empty slot ${s.slot}`;
	let label = `${s.item} · ${gradeName(s.item_grade)} (${s.item_grade ?? 0}) · ×${s.count}`;
	if (s.delta) label += ` · ${s.delta > 0 ? '+' : ''}${s.delta}`;
	if (s.change === 'new') label += ' · new';
	return label;
}

export function changeDot(change: SlotRead['change']): 'up' | 'down' | 'new' | null {
	return change ?? null;
}

export const ALL = 'All';

/** The tab named in the URL, or All when it is missing or unknown (renamed character, old link). */
export function pickTab(value: string | null, options: string[]): string {
	return value != null && options.includes(value) ? value : ALL;
}

export function chestLabel(c: { chest: number; name: string | null }): string {
	return c.name ?? `Chest ${c.chest}`;
}

export function snapshotTime(x: string | null | undefined): string {
	return x ? new Date(x + 'Z').toLocaleString('en-GB') : '—';
}
