import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import CategoryTree from './CategoryTree.svelte';
import { buildTree } from './tree';
import type { MarketItemRead } from '$lib/core/types';

const item = (id: number, name: string, item_type: number, item_grade: number, category: string | null): MarketItemRead => ({
	id, name, item_type, item_grade, category, last_day: null, min_stack: 10, cheapest_real: 4965, scan_at: null
});
const tree = buildTree([item(1, 'Leather', 1, 0, 'Hide'), item(2, 'Leather', 1, 2, 'Hide'), item(3, 'Iron', 2, 0, 'Metal')], '');

describe('CategoryTree', () => {
	it('folds a category and selects a node', async () => {
		const onSelect = vi.fn();
		render(CategoryTree, { tree, selectedId: 2, onSelect });
		const leather = screen.getByRole('button', { name: /Leather/ });
		expect(leather.getAttribute('aria-current')).toBe('true');
		expect(leather.textContent).toContain('49s');
		await fireEvent.click(screen.getByRole('button', { name: /Iron/ }));
		expect(onSelect).toHaveBeenCalledWith(3);
		await fireEvent.click(screen.getByRole('button', { name: /Hide/ }));
		expect(screen.queryByRole('button', { name: /Leather/ })).toBeNull();
		await fireEvent.click(screen.getByRole('button', { name: /Hide/ }));
		expect(screen.getByRole('button', { name: /Leather/ })).toBeTruthy();
	});

	it('says No items match for an empty tree', () => {
		render(CategoryTree, { tree: [], selectedId: null, onSelect: () => {} });
		expect(document.body.textContent).toContain('No items match');
	});
});
