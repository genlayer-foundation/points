import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

export default defineConfig({
  plugins: [
    svelte({
      compilerOptions: {
        // Jangan paksa runes mode jika masih banyak library lama
        runes: false,
      },
    }),
  ],
});
