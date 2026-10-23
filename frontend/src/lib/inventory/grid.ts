// Pure helpers for the item grids: slot position, tile label, change dot, tabs and times.
import type { CharacterRead, SlotRead } from '$lib/core/types';
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

// The All tab's value; '' can't be a character name or a chest number, unlike 'All'.
export const ALL = '';

/** A stack count short enough for a ~28px tile (20 columns a side at 1280px); the tooltip keeps the exact number. */
export function formatCount(n: number): string {
	return n >= 10000 ? `${Math.floor(n / 1000)}k` : String(n);
}

/** The tab named in the URL, or All when it is missing or unknown (renamed character, old link). */
export function pickTab(value: string | null, options: string[]): string {
	return value != null && options.includes(value) ? value : ALL;
}

export function chestLabel(c: { chest: number; name: string | null }): string {
	return c.name ?? `Chest ${c.chest}`;
}

// Lowercase words without punctuation: "Farmer's Large Chest" gives "farmers large chest".
const words = (s: string) =>
	s.toLowerCase().replace(/['’]/g, '').replace(/[^\p{L}\p{N}]+/gu, ' ').trim();

/**
 * The character a chest belongs to, or null for a house (land) chest.
 * A bag chest opens only from its owner's bag, so it belongs to the character who saved it
 * when that character's bag holds an item whose name starts with the chest's name.
 * A 15-character name (the addon's limit) may end mid-word, so its last word only has to start an item word.
 * shortcut: matches typed names, not a game id; a land chest named after a bag item, or reusing the number
 * (and kept name) of a bag chest, lands under the character.
 */
export function chestOwner(
	c: { name: string | null; saved_by: string },
	characters: Pick<CharacterRead, 'character' | 'bag'>[]
): string | null {
	// The word "chest" is optional in the name: "Adventurer's" and "Adventurer's chest" both match "Adventurer's Chest".
	const name = words(c.name ?? '')
		.split(' ')
		.filter((w) => w !== 'chest')
		.join(' ');
	const cut = (c.name ?? '').length >= 15;
	if (!name) return null;
	const bag = characters.find((x) => x.character === c.saved_by)?.bag;
	const match = bag?.slots.some((s) => {
		const item = s.item == null ? '' : words(s.item);
		return item === name || item.startsWith(cut ? name : name + ' ');
	});
	return match ? c.saved_by : null;
}

export function snapshotTime(x: string | null | undefined): string {
	return x ? new Date(x + 'Z').toLocaleString('en-GB') : '—';
}
