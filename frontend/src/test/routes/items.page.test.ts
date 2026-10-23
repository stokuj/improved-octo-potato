import { describe, it, expect, beforeEach } from 'vitest';
import { render, waitFor, fireEvent } from '@testing-library/svelte';
import { mockFetch, restoreFetch } from '../mocks/fetch';
import { page } from '$app/state';
import type { CharacterRead, ChestRead, GridRead } from '$lib/core/types';
import Page from '../../routes/items/+page.svelte';

function grid(size: number): GridRead {
	return {
		captured_at: '2026-10-23T10:00:00',
		previous_captured_at: null,
		slot_count: size,
		filled: 1,
		slots: Array.from({ length: size }, (_, i) =>
			i === 3
				? { slot: 4, item: 'Leather', item_type: 16327, item_grade: 0, count: 412, change: 'up', delta: 120 }
				: { slot: i + 1, item: null, item_type: null, item_grade: null, count: 0, change: null, delta: null }
		)
	};
}

const characters: CharacterRead[] = [
	{ character: 'Alpha', bag: grid(90), bank: grid(30) },
	{ character: 'Bravo', bag: grid(150), bank: null },
	{ character: 'Charlie', bag: null, bank: grid(10) }
];
const chests: ChestRead[] = [
	{ ...grid(30), chest: 1, name: 'Treehouse', saved_by: 'Alpha' },
	{ ...grid(50), chest: 2, name: null, saved_by: 'Bravo' }
];

function open(url: string, data: { characters?: CharacterRead[]; chests?: ChestRead[] } = {}) {
	(page as { url: URL }).url = new URL(`http://localhost/items${url}`);
	const spy = mockFetch({
		'/inventory/characters': { json: async () => data.characters ?? characters },
		'/inventory/chests': { json: async () => data.chests ?? chests }
	});
	render(Page);
	return spy;
}

const section = (label: string) => document.querySelector<HTMLElement>(`section[aria-label="${label}"]`)!;
const panels = (label: string) => [...section(label).querySelectorAll('[data-testid="grid-panel"]')];
const titles = (label: string) => panels(label).map((p) => p.querySelector('h3')!.textContent!.trim());
const tab = (label: string, name: string) =>
	[...section(label).querySelectorAll<HTMLElement>('[role="tab"]')].find((t) => t.textContent!.trim() === name)!;

beforeEach(() => restoreFetch());

describe('items page', () => {
	it('shows All on both sides by default', async () => {
		open('');
		await waitFor(() => expect(panels('Characters')).toHaveLength(4));
		expect(titles('Characters')).toEqual(['Bag', 'Warehouse', 'Bag', 'Warehouse'].map((t) => expect.stringContaining(t)));
		expect(panels('House chests')).toHaveLength(2);
		expect(tab('Characters', 'All').getAttribute('aria-selected')).toBe('true');
		expect(tab('House chests', 'All').getAttribute('aria-selected')).toBe('true');
	});

	it('switching the character keeps the chest side', async () => {
		open('');
		await waitFor(() => expect(panels('Characters')).toHaveLength(4));
		await fireEvent.click(tab('Characters', 'Alpha'));
		await waitFor(() => expect(page.url.searchParams.get('character')).toBe('Alpha'));
		await waitFor(() => expect(panels('Characters')).toHaveLength(2));
		expect(titles('Characters')).toEqual([expect.stringContaining('Bag'), expect.stringContaining('Warehouse')]);
		expect(panels('House chests')).toHaveLength(2);
	});

	it('switching the chest keeps the character side', async () => {
		open('');
		await waitFor(() => expect(panels('House chests')).toHaveLength(2));
		await fireEvent.click(tab('House chests', 'Treehouse'));
		await waitFor(() => expect(page.url.searchParams.get('chest')).toBe('1'));
		await waitFor(() => expect(panels('House chests')).toHaveLength(1));
		expect(panels('House chests')[0].textContent).toContain('saved by Alpha');
		expect(panels('Characters')).toHaveLength(4);
	});

	it('falls back to All for unknown tabs', async () => {
		const spy = open('?character=Ghost&chest=x');
		await waitFor(() => expect(panels('Characters')).toHaveLength(4));
		expect(panels('House chests')).toHaveLength(2);
		expect(spy.mock.calls.some((c) => String(c[0]).includes('Ghost'))).toBe(false);
	});

	it('labels an unnamed chest by number', async () => {
		open('');
		await waitFor(() => expect(tab('House chests', 'Chest 2')).toBeDefined());
	});

	it('shows only the warehouse when a character has no bag', async () => {
		open('?character=Charlie');
		await waitFor(() => expect(panels('Characters')).toHaveLength(1));
		expect(titles('Characters')).toEqual([expect.stringContaining('Warehouse')]);
	});

	it('shows the Codex icon and falls back to the grade colour when it fails', async () => {
		open('?character=Alpha&chest=1');
		const img = await waitFor(() => {
			const el = section('Characters').querySelector('img[src$="/inventory/icons/16327.png"]');
			expect(el).not.toBeNull();
			return el!;
		});
		const tile = img.closest('[data-testid="tile"]')!;
		expect(tile.getAttribute('aria-label')).toBe('Leather · None (0) · ×412 · +120');
		await fireEvent.error(img);
		await waitFor(() => expect(tile.querySelector('img')).toBeNull());
		expect((tile as HTMLElement).style.background).not.toBe('');
	});

	it('draws empty slots dashed and keeps the tooltip wrapper', async () => {
		open('?character=Alpha&chest=1');
		const tiles = await waitFor(() => {
			const t = section('Characters').querySelectorAll<HTMLElement>('[data-testid="tile"]');
			expect(t).toHaveLength(120);
			return t;
		});
		expect(tiles[0].className).toContain('border-dashed');
		expect(tiles[3].parentElement!.classList.contains('tooltip')).toBe(true);
		expect(tiles[3].parentElement!.getAttribute('data-tip')).toBe(tiles[3].getAttribute('aria-label'));
	});

	it('opens tooltips of the right half to the left and shortens big counts', async () => {
		const big = grid(10);
		big.slots[9] = { slot: 10, item: 'Leather', item_type: 16327, item_grade: 0, count: 12345, change: null, delta: null };
		open('?character=Bravo', { characters: [{ character: 'Bravo', bag: big, bank: null }] });
		const tiles = await waitFor(() => {
			const t = section('Characters').querySelectorAll<HTMLElement>('[data-testid="tile"]');
			expect(t).toHaveLength(10);
			return t;
		});
		expect(tiles[0].parentElement!.classList.contains('tooltip-left')).toBe(false);
		expect(tiles[9].parentElement!.classList.contains('tooltip-left')).toBe(true);
		expect(tiles[9].textContent!.trim()).toBe('12k');
		expect(tiles[9].getAttribute('aria-label')).toContain('×12345');
	});

	it('explains how to get data', async () => {
		open('', { characters: [], chests: [] });
		await waitFor(() => expect(document.querySelector('a[href="/import"]')).not.toBeNull());
		const text = document.body.textContent!;
		for (const s of ['inventory.csv', 'chests.csv', 'Bag', 'Chest']) expect(text).toContain(s);
	});

	it('lets a character named All be picked', async () => {
		open('', { characters: [...characters, { character: 'All', bag: grid(20), bank: null }] });
		await waitFor(() => expect(panels('Characters')).toHaveLength(5));
		const named = [...section('Characters').querySelectorAll<HTMLElement>('[role="tab"]')].filter((t) => t.textContent!.trim() === 'All');
		expect(named).toHaveLength(2);
		await fireEvent.click(named[1]);
		await waitFor(() => expect(page.url.searchParams.get('character')).toBe('All'));
		await waitFor(() => expect(panels('Characters')).toHaveLength(1));
	});

	it('asks to sign in on 401', async () => {
		(page as { url: URL }).url = new URL('http://localhost/items');
		mockFetch({
			'/inventory/characters': { status: 401 },
			'/inventory/chests': { status: 401 }
		});
		render(Page);
		await waitFor(() => expect(document.body.textContent).toContain('Sign in to see your items.'));
	});
});
