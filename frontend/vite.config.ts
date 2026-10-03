import { svelte } from '@sveltejs/vite-plugin-svelte';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [svelte()],
  server: { proxy: { '/chat': 'http://127.0.0.1:8000', '/auth': 'http://127.0.0.1:8000', '/projects': 'http://127.0.0.1:8000', '/documents': 'http://127.0.0.1:8000' } }
});
