import { describe, it, expect } from 'vitest';
import { ALL, changeDot, chestLabel, chestOwner, formatCount, pickTab, slotPosition, tileLabel } from './grid';
import type { SlotRead } from '$lib/core/types';

const slot = (over: Partial<SlotRead>): SlotRead => ({
	slot: 1, item: null, item_type: null, item_grade: null, count: 0, change: null, delta: null, ...over
});

describe('slotPosition', () => {
	it('fills 10 columns row by row from the top-left', () => {
		expect(slotPosition(1)).toEqual({ row: 1, col: 1 });
		expect(slotPosition(10)).toEqual({ row: 1, col: 10 });
		expect(slotPosition(11)).toEqual({ row: 2, col: 1 });
		expect(slotPosition(150)).toEqual({ row: 15, col: 10 });
	});
});

describe('tileLabel', () => {
	it('names the item, grade, count and change', () => {
		expect(tileLabel(slot({ item: 'Leather', item_grade: 0, count: 412, delta: 120, change: 'up' }))).toBe(
			'Leather · None (0) · ×412 · +120'
		);
		expect(tileLabel(slot({ item: 'Iron Ore', item_grade: 0, count: 5, delta: -3, change: 'down' }))).toBe(
			'Iron Ore · None (0) · ×5 · -3'
		);
		expect(tileLabel(slot({ item: 'Copper Ingot', item_grade: 1, count: 3, delta: 3, change: 'new' }))).toBe(
			'Copper Ingot · Basic (1) · ×3 · +3 · new'
		);
		expect(tileLabel(slot({ item: 'Leather', item_grade: 0, count: 1, delta: 0 }))).toBe('Leather · None (0) · ×1');
	});

	it('labels an empty slot by its number', () => {
		expect(tileLabel(slot({ slot: 7 }))).toBe('Empty slot 7');
	});
});

describe('changeDot', () => {
	it('maps change to a dot kind', () => {
		expect(changeDot('up')).toBe('up');
		expect(changeDot('down')).toBe('down');
		expect(changeDot('new')).toBe('new');
		expect(changeDot(null)).toBeNull();
	});
});

describe('pickTab', () => {
	it('keeps a known tab and falls back to All', () => {
		expect(pickTab('Alpha', ['Alpha'])).toBe('Alpha');
		expect(pickTab('Ghost', ['Alpha'])).toBe(ALL);
		expect(pickTab(null, [])).toBe(ALL);
		expect(pickTab('All', ['All'])).toBe('All');
	});
});

describe('chestLabel', () => {
	it('uses the name, or the number when never named', () => {
		expect(chestLabel({ chest: 1, name: 'Treehouse' })).toBe('Treehouse');
		expect(chestLabel({ chest: 2, name: null })).toBe('Chest 2');
	});
});

describe('chestOwner', () => {
	const bag = (...items: string[]) => ({
		character: 'Alpha',
		bank: null,
		bag: {
			captured_at: '2026-10-23T10:00:00',
			previous_captured_at: null,
			slot_count: items.length,
			filled: items.length,
			slots: items.map((item, i) => ({ slot: i + 1, item, item_type: 1, item_grade: 0, count: 1, change: null, delta: null }))
		}
	});
	const chars = [bag("Adventurer's Chest", '30-Slot Shard Collector\'s Chest', 'Copper Ingot'), { character: 'Bravo', bag: null, bank: null }];

	it("puts a chest under its saver when the saver's bag holds a chest item of that name", () => {
		expect(chestOwner({ name: "Adventurer's", saved_by: 'Alpha' }, chars)).toBe('Alpha');
		expect(chestOwner({ name: 'adventurers chest', saved_by: 'Alpha' }, chars)).toBe('Alpha');
		expect(chestOwner({ name: '30-Slot Shard', saved_by: 'Alpha' }, chars)).toBe('Alpha');
		// The addon's name box stops at 15 characters, so a typed item name may end mid-word.
		expect(chestOwner({ name: "Adventurer's Ch", saved_by: 'Alpha' }, chars)).toBe('Alpha');
		expect(chestOwner({ name: '30-Slot Shard C', saved_by: 'Alpha' }, chars)).toBe('Alpha');
	});

	it('leaves land chests, unnamed chests and other savers on the house side', () => {
		expect(chestOwner({ name: 'Treehouse 1', saved_by: 'Alpha' }, chars)).toBeNull();
		expect(chestOwner({ name: null, saved_by: 'Alpha' }, chars)).toBeNull();
		expect(chestOwner({ name: 'Chest', saved_by: 'Alpha' }, chars)).toBeNull();
		expect(chestOwner({ name: "Adventurer's", saved_by: 'Bravo' }, chars)).toBeNull();
		expect(chestOwner({ name: "Adventurer's", saved_by: 'Nobody' }, chars)).toBeNull();
		expect(chestOwner({ name: 'Adv', saved_by: 'Alpha' }, chars)).toBeNull();
	});
});

describe('formatCount', () => {
	it('keeps up to 4 digits and shortens bigger stacks so they fit a small tile', () => {
		expect(formatCount(9999)).toBe('9999');
		expect(formatCount(10000)).toBe('10k');
		expect(formatCount(12345)).toBe('12k');
	});
});
