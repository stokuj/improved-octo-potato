// Test stub for SvelteKit's $app/state module; reactive so goto() in tests updates the page.
export const page = $state({
    params: {} as Record<string, string>,
    url: new URL('http://localhost/')
});
