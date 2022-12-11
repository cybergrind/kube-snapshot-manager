import { sveltekit } from '@sveltejs/kit/vite';

/** @type {import('vite').UserConfig} */
const config = {
	plugins: [sveltekit()],
	test: {
		include: ['src/**/*.{test,spec}.{js,ts}']
	},
  server: {
    proxy: {
      '/api': 'http://localhost:8006',
      '/api/ws': {
        target: 'ws://localhost:8006/',
        ws: true
      }
    }
  }

};

export default config;
