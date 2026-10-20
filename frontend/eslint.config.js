import { defineConfig } from 'eslint/config';
import js from '@eslint/js';
import globals from 'globals';
import ts from 'typescript-eslint';
import svelte from 'eslint-plugin-svelte';
import prettier from 'eslint-config-prettier';

export default defineConfig(
  {
    ignores: [
      '**/node_modules/**',
      '**/references/**',
      '**/dist/**',
      '**/build/**',
      '**/.svelte-kit/**',
      '.husky/_/**',
      '**/[aA][rR][cC][hH][iI][vV][eE]/**',
    ],
  },
  js.configs.recommended,
  ts.configs.recommended,
  svelte.configs.recommended,
  { files: ['src/**/*.{js,ts,svelte}'], languageOptions: { globals: globals.browser } },
  {
    files: ['tests/**/*.{js,mjs,ts}', '*.{js,mjs,ts}'],
    // Browser test callbacks run in page.evaluate(), while the harness runs in Node.
    languageOptions: { globals: { ...globals.node, ...globals.browser } },
  },
  {
    files: ['**/*.svelte', '**/*.svelte.ts', '**/*.svelte.js'],
    languageOptions: { parserOptions: { parser: ts.parser } },
  },
  {
    rules: {
      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],
    },
  },
  prettier,
  svelte.configs.prettier,
);
