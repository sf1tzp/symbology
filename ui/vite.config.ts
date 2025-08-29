import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	define: {
		// Inject environment variables at build time
		'import.meta.env.ENVIRONMENT': JSON.stringify(process.env.ENVIRONMENT || 'development'),
		'import.meta.env.SYMBOLOGY_API_HOST': JSON.stringify(
			process.env.SYMBOLOGY_API_HOST || 'localhost'
		),
		'import.meta.env.SYMBOLOGY_API_PORT': JSON.stringify(process.env.SYMBOLOGY_API_PORT || '8000'),
		'import.meta.env.LOG_LEVEL': JSON.stringify(process.env.LOG_LEVEL || 'info')
	}
});
