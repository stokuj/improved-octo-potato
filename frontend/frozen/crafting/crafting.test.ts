import { describe, it, expect } from 'vitest';
import { computeNodeCost, MAX_RECIPE_DEPTH, LABOUR_ITEM_NAME } from './crafting';
import type { CraftNode } from './types';

function leaf(id: number, qty: number, price: number | null): CraftNode {
    return {
        item_id: id,
        item_name: `item-${id}`,
        qty_needed: qty,
        unit_price: price,
        total_cost: 0,
        can_craft: false,
        crafts_possible: null,
        output_qty: 1,
        ingredients: [],
    };
}

function craftable(id: number, qty: number, outputQty: number, ingredients: CraftNode[]): CraftNode {
    return {
        item_id: id,
        item_name: `craft-${id}`,
        qty_needed: qty,
        unit_price: null,
        total_cost: 0,
        can_craft: true,
        crafts_possible: null,
        output_qty: outputQty,
        ingredients,
    };
}

const EMPTY_CTX = { inventory: {}, nodeOverrides: {} };

describe('LABOUR_ITEM_NAME', () => {
    it('is the lower-case "labour" sentinel', () => {
        expect(LABOUR_ITEM_NAME).toBe('labour');
    });
});

describe('computeNodeCost', () => {
    it('returns unit_price * qty for a priced leaf', () => {
        // qty_needed=2 at scale=3 => 6 units * 5g = 30
        expect(computeNodeCost(leaf(1, 2, 5), 3, EMPTY_CTX)).toBe(30);
    });

    it('returns 0 for a leaf with no unit_price', () => {
        expect(computeNodeCost(leaf(1, 2, null), 3, EMPTY_CTX)).toBe(0);
    });

    it('subtracts inventory on-hand from required quantity', () => {
        // need 6, have 4 => buy 2 at 5g = 10
        const ctx = { inventory: { 1: 4 }, nodeOverrides: {} };
        expect(computeNodeCost(leaf(1, 2, 5), 3, ctx)).toBe(10);
    });

    it('returns 0 when inventory covers the requirement', () => {
        const ctx = { inventory: { 1: 100 }, nodeOverrides: {} };
        expect(computeNodeCost(leaf(1, 2, 5), 3, ctx)).toBe(0);
    });

    it('sums craftable node ingredients scaled by output_qty', () => {
        // craftable: qty_needed=1, output_qty=1, ingredients=[leaf(price=10, qty=2)]
        // at scale=1 => 1 craft => 2 * 10 = 20
        const tree = craftable(2, 1, 1, [leaf(1, 2, 10)]);
        expect(computeNodeCost(tree, 1, EMPTY_CTX)).toBe(20);
    });

    it('respects buy override on a craftable node', () => {
        // craftable has no unit_price (null) so buying yields 0
        const tree = craftable(2, 1, 1, [leaf(1, 2, 10)]);
        const ctx = { inventory: {}, nodeOverrides: { 2: { mode: 'buy' as const, expanded: true } } };
        expect(computeNodeCost(tree, 1, ctx)).toBe(0);
    });

    it('throws when depth exceeds MAX_RECIPE_DEPTH (cycle protection)', () => {
        const node: CraftNode = craftable(1, 1, 1, []);
        // create a cycle
        node.ingredients.push(node);
        expect(() => computeNodeCost(node, 1, EMPTY_CTX)).toThrowError(/depth/i);
    });

    it('MAX_RECIPE_DEPTH is a positive integer', () => {
        expect(MAX_RECIPE_DEPTH).toBeGreaterThan(0);
        expect(Number.isInteger(MAX_RECIPE_DEPTH)).toBe(true);
    });
});

describe('crafting constants and edge cases', () => {
    it('LABOUR_ITEM_NAME is a non-empty string constant', () => {
        expect(typeof LABOUR_ITEM_NAME).toBe('string');
        expect(LABOUR_ITEM_NAME.length).toBeGreaterThan(0);
    });

    it('multiplier=0 does not crash computeNodeCost', () => {
        const tree = leaf(1, 2, 5);
        expect(() => computeNodeCost(tree, 0, EMPTY_CTX)).not.toThrow();
        expect(computeNodeCost(tree, 0, EMPTY_CTX)).toBe(0);
    });

    it('fractional multiplier handled without infinite loop', () => {
        const tree = leaf(1, 2, 5);
        expect(() => computeNodeCost(tree, 1.5, EMPTY_CTX)).not.toThrow();
    });
});
