import { describe, it, expect, beforeEach } from 'vitest';
import { render, waitFor, fireEvent } from '@testing-library/svelte';
import { mockFetch, restoreFetch } from '../mocks/fetch';
import { page } from '$app/state';
import Page from '../../routes/inventory/+page.svelte';

const characters = [
	{ character: 'Alpha', captured_at: '2026-10-23T10:00:00', previous_captured_at: null, slot_count: 90, filled: 1 },
	{ character: 'Bravo', captured_at: '2026-10-23T10:01:00', previous_captured_at: '2026-10-22T10:00:00', slot_count: 150, filled: 1 }
];

function bag(character: string, size: number) {
	return {
		character,
		captured_at: '2026-10-23T10:00:00',
		previous_captured_at: null,
		slots: Array.from({ length: size }, (_, i) =>
			i === 3
				? { slot: 4, item: 'Leather', item_type: 16327, item_grade: 0, count: 412, icon: 'icon_item_0352', change: 'up', delta: 120 }
				: { slot: i + 1, item: null, item_type: null, item_grade: null, count: 0, icon: null, change: null, delta: null }
		)
	};
}

beforeEach(() => restoreFetch());

describe('inventory page', () => {
	it('shows a tab per character and the selected bag', async () => {
		(page as { url: URL }).url = new URL('http://localhost/inventory');
		mockFetch({
			'/inventory/characters': { json: async () => characters },
			'/inventory/characters/Alpha': { json: async () => bag('Alpha', 90) },
			'/inventory/characters/Bravo': { json: async () => bag('Bravo', 150) }
		});
		render(Page);
		await waitFor(() => expect(document.body.textContent).toContain('Alpha · 90'));
		expect(document.body.textContent).toContain('Bravo · 150');
		await waitFor(() => expect(document.querySelectorAll('[data-testid="tile"]')).toHaveLength(90));

		await fireEvent.click([...document.querySelectorAll('[role="tab"]')].find((t) => t.textContent?.includes('Bravo'))!);
		await waitFor(() => expect(page.url.searchParams.get('character')).toBe('Bravo'));
		await waitFor(() => expect(document.querySelectorAll('[data-testid="tile"]')).toHaveLength(150));
	});

	it('shows the Codex icon and falls back to the grade colour when it fails', async () => {
		(page as { url: URL }).url = new URL('http://localhost/inventory?character=Alpha');
		mockFetch({
			'/inventory/characters': { json: async () => characters },
			'/inventory/characters/Alpha': { json: async () => bag('Alpha', 90) }
		});
		render(Page);
		const img = await waitFor(() => {
			const el = document.querySelector('img[src$="/inventory/icons/icon_item_0352.png"]');
			expect(el).not.toBeNull();
			return el!;
		});
		const tile = img.closest('[data-testid="tile"]')!;
		expect(tile.getAttribute('aria-label')).toBe('Leather · None (0) · ×412 · +120');
		await fireEvent.error(img);
		await waitFor(() => expect(tile.querySelector('img')).toBeNull());
	});

	it('points to /import when there are no characters yet', async () => {
		(page as { url: URL }).url = new URL('http://localhost/inventory');
		mockFetch({ '/inventory/characters': { json: async () => [] } });
		render(Page);
		await waitFor(() => expect(document.querySelector('a[href="/import"]')).not.toBeNull());
	});
});
