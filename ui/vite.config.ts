import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import tailwindcss from '@tailwindcss/vite'
import { resolve } from 'path';

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [
        svelte(),
        tailwindcss(),
    ],
    resolve: {
        alias: {
            '$src': resolve('./src'),
            '$components': resolve('./src/components'),
            '$utils': resolve('./src/utils')
        }
    },
    build: {
        // Optimize for production
        minify: 'terser',
        sourcemap: true,
        rollupOptions: {
            output: {
                manualChunks: {
                    vendor: ['svelte'],
                    utils: ['marked', 'dompurify']
                }
            }
        }
    },
    server: {
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