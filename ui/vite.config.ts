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
                target: 'http://10.0.0.3:8000',
                changeOrigin: true,
                // Don't rewrite the path - keep the /api prefix
                // rewrite: (path) => path.replace(/^\/api/, '')
            }
        },
        hmr: {
            // Listen on all interfaces, but don't specify client connection address
            host: '0.0.0.0',
            port: 5173,
            // Don't force a specific host in the client connection
            clientPort: undefined,
            // Don't specify protocol in the client connection
            protocol: undefined,
            // Let Vite determine the correct connection URL
        }
    }
});