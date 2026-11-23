import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

// base './' så att bygget fungerar från vilken sökväg som helst (Railway, artefakt, fil).
export default defineConfig({
  base: './',
  plugins: [svelte()],
  // under utveckling: spelservern (uvicorn spel.server.app:app --port 8000) bakom samma adress
  server: { proxy: { '/api': 'http://localhost:8000', '/ws': { target: 'ws://localhost:8000', ws: true } } },
  test: { include: ['src/**/*.test.ts'] },
});
