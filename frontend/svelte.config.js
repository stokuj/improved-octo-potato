import adapter from '@sveltejs/adapter-node';

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
				'connect-src': ['self'],
				'frame-ancestors': ['none']
			}
		}
	}
};

export default config;
