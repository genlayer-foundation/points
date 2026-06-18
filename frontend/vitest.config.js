import { defineConfig } from 'vitest/config';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { svelteTesting } from '@testing-library/svelte/vite';
import { fileURLToPath, URL } from 'node:url';

const local = (p) => fileURLToPath(new URL(p, import.meta.url));

export default defineConfig({
  plugins: [svelteTesting(), svelte()],
  resolve: {
    conditions: ['browser'],
    alias: {
      'svelte-spa-router/wrap': local('./src/lib/wrap.js'),
      'svelte-spa-router': local('./src/lib/Router.svelte'),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/tests/setupTests.js'],
    include: ['src/**/*.{test,spec}.{js,ts,svelte}'],
    // Use the new server.deps.inline pattern instead of the deprecated deps.inline
    server: {
      deps: {
        inline: [/svelte/]
      }
    }
  },
});
