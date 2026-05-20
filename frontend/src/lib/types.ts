import type { components } from './api'

// Items
export type ItemRead       = components['schemas']['ItemRead']
export type ItemListItem   = components['schemas']['ItemListItem']
export type PaginatedItems = components['schemas']['PaginatedItems']

// Prices
export type PricePointRead  = components['schemas']['PricePointRead']
export type PriceBucketRead = components['schemas']['PriceBucketRead']

// Crafting
export type CraftResult  = components['schemas']['CraftResult']
export type CraftNode    = components['schemas']['CraftNode']
export type CraftSummary = components['schemas']['CraftSummary']

// Inventory
export type InventoryItem = components['schemas']['InventoryItem']

// Auth
export type UserRead    = components['schemas']['UserRead']
export type ProfileRead = components['schemas']['ProfileRead']

// Local types (not from API)
export interface ChartPoint {
    t: string
    price: number
}

export interface NodeOverride {
    mode: 'craft' | 'buy'
    expanded: boolean
}
