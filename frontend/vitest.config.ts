import { defineConfig } from 'vitest/config';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import path from 'node:path';

export default defineConfig({
	plugins: [svelte({ compilerOptions: { generate: 'client' } })],
	resolve: {
		conditions: ['browser'],
		alias: {
			'$lib/auth.svelte.js': path.resolve(__dirname, 'src/test/mocks/auth.svelte.ts'),
			'$lib/auth.svelte': path.resolve(__dirname, 'src/test/mocks/auth.svelte.ts'),
			'$lib/config.js': path.resolve(__dirname, 'src/test/mocks/config.ts'),
			$lib: path.resolve(__dirname, 'src/lib'),
			'$app/navigation': path.resolve(__dirname, 'src/test/mocks/app-navigation.ts'),
			'$app/state': path.resolve(__dirname, 'src/test/mocks/app-state.ts'),
			'$env/static/public': path.resolve(__dirname, 'src/test/mocks/env-static-public.ts')
		}
	},
	ssr: {
		noExternal: ['svelte', '@testing-library/svelte', '@testing-library/svelte-core']
	},
	test: {
		environment: 'jsdom',
		globals: true,
		include: ['src/**/*.{test,spec}.{ts,svelte}'],
		server: {
			deps: {
				inline: ['svelte', '@testing-library/svelte', '@testing-library/svelte-core']
			}
		}
	}
});
