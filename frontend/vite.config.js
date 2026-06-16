import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [svelte()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq) => {
            // Django's CSRF origin check sees forwarded Origin headers.
            // In local dev, the browser can run on random localhost ports
            // (for example Conductor workspaces), so normalize proxied API
            // requests to the backend origin.
            proxyReq.setHeader('Origin', 'http://localhost:8000');
          });
        },
      }
    }
  },
  // Explicitly include markdown files as assets for ?raw imports
  assetsInclude: ['**/*.md'],
  define: {
    global: 'globalThis',
  },
  resolve: {
    alias: {
      buffer: 'buffer',
      process: 'process/browser',
    },
  },
});
