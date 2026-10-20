export default {
  plugins: ['prettier-plugin-svelte'],
  tabWidth: 2,
  useTabs: false,
  printWidth: 100,
  singleQuote: true,
  semi: true,
  trailingComma: 'all',
  endOfLine: 'lf',
  overrides: [{ files: '*.svelte', options: { parser: 'svelte' } }],
};
