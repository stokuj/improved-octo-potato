import { defineConfig } from 'vitest/config';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import path from 'node:path';

export default defineConfig({
	plugins: [svelte()],
	resolve: {
		alias: {
			$lib: path.resolve(__dirname, 'src/lib'),
			'$app/navigation': path.resolve(__dirname, 'src/test/mocks/app-navigation.ts'),
			'$app/state': path.resolve(__dirname, 'src/test/mocks/app-state.ts'),
			'$env/static/public': path.resolve(__dirname, 'src/test/mocks/env-static-public.ts')
		}
	},
	test: {
		environment: 'jsdom',
		globals: true,
		include: ['src/**/*.{test,spec}.{ts,svelte}']
	}
});
