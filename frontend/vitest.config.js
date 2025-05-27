import { defineConfig } from 'vitest/config';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
  plugins: [svelte({ hot: !process.env.VITEST })],
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