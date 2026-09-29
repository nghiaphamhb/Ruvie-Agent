import { svelte } from '@sveltejs/vite-plugin-svelte';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [svelte()],
  server: { proxy: { '/chat': 'http://127.0.0.1:8000' } }
});
