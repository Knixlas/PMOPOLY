import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

// base './' så att bygget fungerar från vilken sökväg som helst (Railway, artefakt, fil).
export default defineConfig({
  base: './',
  plugins: [svelte()],
  test: { include: ['src/**/*.test.ts'] },
});
