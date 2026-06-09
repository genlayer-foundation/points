import { defineConfig } from 'vitest/config';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { svelteTesting } from '@testing-library/svelte/vite';

export default defineConfig({
  plugins: [svelteTesting(), svelte()],
  resolve: {
    conditions: ['browser']
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
