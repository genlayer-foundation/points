import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { paraglideVitePlugin } from '@inlang/paraglide-js';
import { fileURLToPath, URL } from 'node:url';

const local = (p) => fileURLToPath(new URL(p, import.meta.url));

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    svelte(),
    // Compiles messages/*.json into src/lib/paraglide (gitignored).
    // Locale resolution: saved choice → browser language → English.
    paraglideVitePlugin({
      project: './project.inlang',
      outdir: './src/lib/paraglide',
      strategy: ['localStorage', 'preferredLanguage', 'baseLocale'],
    }),
  ],
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
      // History-based router shim replacing the hash-only svelte-spa-router,
      // so the ~68 importing files and the route table stay unchanged.
      // More-specific '/wrap' must come first (prefix match wins by order).
      'svelte-spa-router/wrap': local('./src/lib/wrap.js'),
      'svelte-spa-router': local('./src/lib/Router.svelte'),
      buffer: 'buffer',
      process: 'process/browser',
    },
  },
});
