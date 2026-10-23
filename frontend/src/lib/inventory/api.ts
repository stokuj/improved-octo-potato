// Fetch helpers for the /api/inventory endpoints (signed-in user's own data).
import { API_BASE_URL } from '$lib/core/config.js';
import type { BagRead, CharacterRead } from '$lib/core/types';
import { ApiError } from '$lib/market/api';

async function getJson<T>(path: string): Promise<T> {
	const r = await fetch(`${API_BASE_URL}${path}`, { credentials: 'include' });
	if (!r.ok) throw new ApiError(r.status, `GET ${path} failed (${r.status})`);
	return r.json();
}

export function fetchCharacters(): Promise<CharacterRead[]> {
	return getJson('/inventory/characters');
}

export function fetchBag(character: string): Promise<BagRead> {
	return getJson(`/inventory/characters/${encodeURIComponent(character)}`);
}

export function iconUrl(itemType: number): string {
	return `${API_BASE_URL}/inventory/icons/${itemType}.png`;
}
