// Shared crafting constants and helpers
import type { CraftNode, NodeOverride } from './types';

export const LABOUR_ITEM_NAME = 'labour';

// Maximum recursion depth to guard against cycles in the recipe tree.
// Real recipes are at most a handful of levels deep; 32 is plenty of head-room
// while still throwing fast if the backend ever returns a cyclic graph.
export const MAX_RECIPE_DEPTH = 32;

export interface ComputeNodeCostContext {
    inventory: Record<number, number>;
    nodeOverrides: Record<number, NodeOverride>;
}

/**
 * Recursively compute the gold cost of fulfilling `node` at the given `scale`
 * (i.e. how many times the parent recipe is being produced). Honours per-node
 * buy/craft overrides and subtracts inventory already on-hand.
 *
 * Throws if recursion exceeds MAX_RECIPE_DEPTH (cycle protection).
 */
export function computeNodeCost(
    node: CraftNode,
    scale: number,
    ctx: ComputeNodeCostContext,
    depth = 0,
): number {
    if (depth > MAX_RECIPE_DEPTH) {
        throw new Error(
            `computeNodeCost: recipe depth exceeded ${MAX_RECIPE_DEPTH} (cycle?)`,
        );
    }
    const qty = node.qty_needed * scale;
    const have = ctx.inventory[node.item_id] ?? 0;
    const stillNeed = Math.max(0, qty - have);
    const override = ctx.nodeOverrides[node.item_id];
    if (override?.mode === 'buy' || !node.can_craft || node.ingredients.length === 0) {
        return (node.unit_price ?? 0) * stillNeed;
    }
    if (stillNeed === 0) return 0;
    // Use output_qty to correctly scale children when batchSize produces a different
    // ceiling than linear multiplication (e.g. qty_needed=11, output_qty=10, batch=2
    // needs 3 crafts, not 2*2=4).
    const outputQty = node.output_qty ?? 1;
    const storedCrafts = Math.ceil(node.qty_needed / outputQty);
    const desiredCrafts = Math.ceil(stillNeed / outputQty);
    const childScale = storedCrafts > 0 ? desiredCrafts / storedCrafts : 0;
    return node.ingredients.reduce(
        (s, c) => s + computeNodeCost(c, childScale, ctx, depth + 1),
        0,
    );
}
