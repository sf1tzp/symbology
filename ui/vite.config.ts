import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { resolve } from 'path';

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [svelte()],
    resolve: {
        alias: {
            '$src': resolve('./src'),
            '$components': resolve('./src/components'),
            '$utils': resolve('./src/utils')
        }
    },
    server: {
        proxy: {
            // Proxy API requests to backend during development
            '/api': {
                target: 'http://localhost:8000',
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/api/, '')
            }
        }
    }
});