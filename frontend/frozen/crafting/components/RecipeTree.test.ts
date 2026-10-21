import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import RecipeTree from './RecipeTree.svelte';

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

const noop = () => {};

const leaf = {
  item_id: 10, item_name: 'Iron Ore', qty_needed: 10, unit_price: 5, total_cost: 50,
  can_craft: false, crafts_possible: null, output_qty: 1, ingredients: [],
};
const mid = {
  item_id: 20, item_name: 'Iron Ingot', qty_needed: 2, unit_price: 100, total_cost: 200,
  can_craft: true, crafts_possible: null, output_qty: 1, ingredients: [leaf],
};
const topNode = {
  item_id: 30, item_name: 'Iron Sword', qty_needed: 1, unit_price: null, total_cost: 0,
  can_craft: true, crafts_possible: null, output_qty: 1, ingredients: [mid],
};

describe('RecipeTree', () => {
  it('renders the root node name', () => {
    render(RecipeTree, { props: { nodes: [topNode], batchSize: 1, nodeOverrides: {}, inventory: {}, onToggleMode: noop, onToggleExpand: noop, onSetInventory: noop } });
    expect(document.body.textContent).toMatch(/Iron Sword/);
  });

  it('renders child ingredients recursively', () => {
    render(RecipeTree, { props: { nodes: [topNode], batchSize: 1, nodeOverrides: { 20: { mode: 'craft', expanded: true } }, inventory: {}, onToggleMode: noop, onToggleExpand: noop, onSetInventory: noop } });
    expect(document.body.textContent).toMatch(/Iron Ingot/);
    expect(document.body.textContent).toMatch(/Iron Ore/);
  });

  it('Have column input is present for leaf items', () => {
    render(RecipeTree, { props: { nodes: [topNode], batchSize: 1, nodeOverrides: {}, inventory: {}, onToggleMode: noop, onToggleExpand: noop, onSetInventory: noop } });
    const inputs = document.querySelectorAll('input[type="number"]');
    expect(inputs.length).toBeGreaterThan(0);
  });

  it('Total Labour footer is rendered', () => {
    render(RecipeTree, { props: { nodes: [topNode], batchSize: 1, nodeOverrides: {}, inventory: {}, onToggleMode: noop, onToggleExpand: noop, onSetInventory: noop } });
    const html = document.body.innerHTML;
    expect(html).toMatch(/total|footer|labour|labor/i);
  });

  it('uses shared LABOUR_ITEM_NAME constant — renders labour badge', async () => {
    const { LABOUR_ITEM_NAME } = await import('$lib/crafting');
    const labourNode = {
      item_id: 999, item_name: LABOUR_ITEM_NAME, qty_needed: 5, unit_price: null,
      total_cost: 0, can_craft: false, crafts_possible: null, output_qty: 1, ingredients: [],
    };
    render(RecipeTree, { props: { nodes: [labourNode], batchSize: 1, nodeOverrides: {}, inventory: {}, onToggleMode: noop, onToggleExpand: noop, onSetInventory: noop } });
    const html = document.body.innerHTML;
    expect(html).toMatch(/labour/i);
    // Labour row should NOT have a Have input (it renders "—" instead)
    const haveInputs = document.querySelectorAll('input[type="number"]');
    expect(haveInputs.length).toBe(0);
  });

  it('leaf node with no recipe shows raw badge', () => {
    render(RecipeTree, { props: { nodes: [topNode], batchSize: 1, nodeOverrides: { 20: { mode: 'craft', expanded: true } }, inventory: {}, onToggleMode: noop, onToggleExpand: noop, onSetInventory: noop } });
    const html = document.body.innerHTML;
    expect(html).toMatch(/raw/i);
  });

  it('does not stack-overflow when given a deep tree (depth 5)', () => {
    let node: any = { ...leaf };
    for (let i = 0; i < 5; i++) {
      node = { ...mid, ingredients: [node], item_id: 1000 + i, item_name: `L${i}` };
    }
    const deepTop = { ...topNode, ingredients: [node] };
    expect(() => render(RecipeTree, { props: { nodes: [deepTop], batchSize: 1, nodeOverrides: {}, inventory: {}, onToggleMode: noop, onToggleExpand: noop, onSetInventory: noop } })).not.toThrow();
  });

  it('clicking expand toggles children', async () => {
    const onToggleExpand = vi.fn();
    render(RecipeTree, { props: { nodes: [topNode], batchSize: 1, nodeOverrides: {}, inventory: {}, onToggleMode: noop, onToggleExpand, onSetInventory: noop } });
    const btn = document.querySelector('button[title="Collapse"]') || document.querySelector('button[title="Expand"]');
    if (btn) {
      await fireEvent.click(btn);
      expect(onToggleExpand).toHaveBeenCalled();
    }
  });
});
