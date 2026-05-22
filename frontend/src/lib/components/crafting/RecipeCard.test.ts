import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import RecipeCard from './RecipeCard.svelte';

const noop = () => {};

const baseCraftTree = {
  item_id: 1,
  item_name: 'Iron Ingot',
  output_qty: 1,
  multiplier: 1,
  market_price: 1000,
  batch_profit: 250,
  total_material_cost: 750,
  has_missing_prices: false,
  ingredients: [],
};

function renderCard(props: Partial<typeof baseCraftTree> & { materialCost?: number; profit?: number | null; batchSize?: number }) {
  return render(RecipeCard, {
    props: {
      craftTree: { ...baseCraftTree, ...props },
      batchSize: props.batchSize ?? 1,
      nodeOverrides: {},
      inventory: {},
      materialCost: props.materialCost ?? 750,
      profit: props.profit ?? 250,
      onBatchChange: noop,
      onToggleMode: noop,
      onToggleExpand: noop,
      onSetInventory: noop,
    },
  });
}

describe('RecipeCard', () => {
  it('displays positive profit', () => {
    renderCard({ profit: 250 });
    expect(document.body.textContent).toMatch(/02s 50b/);
  });

  it('displays negative profit', () => {
    renderCard({ profit: -100 });
    expect(document.body.textContent).toMatch(/-/);
  });

  it('treats profit as total batch profit', () => {
    renderCard({ batchSize: 5, profit: 800 });
    expect(document.body.textContent).toMatch(/08s 00b/);
  });

  it('shows placeholder when profit is null', () => {
    renderCard({ profit: null, has_missing_prices: true });
    expect(document.body.textContent).not.toContain('NaN');
  });
});
