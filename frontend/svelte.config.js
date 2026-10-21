import adapter from '@sveltejs/adapter-node';

// The API may live on another origin (dev 5173→8000, e2e 5174→8001); allow it for fetch.
const apiOrigin = new URL(process.env.PUBLIC_API_URL || 'http://localhost:8000/api').origin;

/** @type {import('@sveltejs/kit').Config} */
const config = {
	compilerOptions: {
		// Force runes mode for the project, except for libraries. Can be removed in svelte 6.
		runes: ({ filename }) => (filename.split(/[/\\]/).includes('node_modules') ? undefined : true)
	},
	kit: {
		adapter: adapter(),
		csp: {
			mode: 'auto',
			directives: {
				'default-src': ['self'],
				'img-src': ['self', 'data:'],
				'script-src': ['self', 'strict-dynamic'],
				'style-src': ['self', 'unsafe-inline'],
				'connect-src': ['self', apiOrigin],
				'frame-ancestors': ['none']
			}
		}
	}
};

export default config;
