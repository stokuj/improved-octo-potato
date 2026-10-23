import { describe, it, expect } from 'vitest';
import { changeDot, slotPosition, tileLabel } from './grid';
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
