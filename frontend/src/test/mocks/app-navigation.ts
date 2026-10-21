// Test stub for SvelteKit's $app/navigation module; goto only updates the stubbed page URL.
import { page } from './app-state.svelte';

export async function goto(url: string): Promise<void> {
    page.url = new URL(url, page.url);
}
