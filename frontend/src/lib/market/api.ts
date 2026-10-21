// Fetch helpers for the /api/market endpoints.
import { API_BASE_URL } from '$lib/core/config.js';
import type {
	ImportFileResult,
	ListingRead,
	MarketDayRead,
	MarketItemRead,
	SummaryRow
} from '$lib/core/types';

export class ApiError extends Error {
	constructor(
		public status: number,
		message: string
	) {
		super(message);
	}
}

async function getJson<T>(path: string): Promise<T> {
	const r = await fetch(`${API_BASE_URL}${path}`, { credentials: 'include' });
	if (!r.ok) throw new ApiError(r.status, `GET ${path} failed (${r.status})`);
	return r.json();
}

export function fetchItems(): Promise<MarketItemRead[]> {
	return getJson('/market/items');
}

export function fetchDays(itemId: number, days = 14): Promise<MarketDayRead[]> {
	return getJson(`/market/items/${itemId}/days?days=${days}`);
}

export function fetchListings(itemId: number): Promise<ListingRead[]> {
	return getJson(`/market/items/${itemId}/listings`);
}

export function fetchSummary(): Promise<SummaryRow[]> {
	return getJson('/market/summary');
}

export async function uploadFiles(files: File[]): Promise<ImportFileResult[]> {
	const body = new FormData();
	for (const f of files) body.append('files', f);
	const r = await fetch(`${API_BASE_URL}/market/import`, {
		method: 'POST',
		body,
		credentials: 'include'
	});
	if (!r.ok) throw new ApiError(r.status, `Upload failed (${r.status})`);
	return r.json();
}
