import assert from 'node:assert/strict';
import test from 'node:test';
import { readFile } from 'node:fs/promises';
import { compile } from 'svelte/compiler';
import { render } from 'svelte/server';

test('connection form labels URL/key and disables editing while chat runs', async () => {
  const { initI18n, setLocale } = await import('../src/lib/i18n/index.ts');
  await initI18n();
  await setLocale('vi-VN');
  const url = new URL('../src/lib/features/llm/LlmConnectionForm.svelte', import.meta.url);
  const source = await readFile(url, 'utf8').catch(() => null);
  assert.ok(source, 'Connection form must exist');
  const compiled = compile(source, { filename: url.pathname, generate: 'server' }).js.code;
  const code = compiled.replace(/from ['"]([^'"]+)['"]/g, (match, specifier) => {
    const resolved = specifier.startsWith('.')
      ? new URL(specifier + (specifier.endsWith('.ts') ? '' : '.ts'), url).href
      : import.meta.resolve(specifier);
    return `from '${resolved}'`;
  });
  const { default: Form } = await import(
    'data:text/javascript;base64,' + Buffer.from(code).toString('base64')
  );
  const { body } = render(Form, {
    props: {
      state: {
        loading: false,
        modelBusy: false,
        connection: null,
        baseUrl: '',
        apiKey: '',
        clearKey: false,
        samePersonalUrl: false,
        error: null,
        notice: null,
        save() {},
        disconnect() {},
        reloadConnection() {},
      },
      disabled: true,
    },
  });
  assert.match(body, /<fieldset[^>]*disabled/);
  assert.match(body, /type="password"/);
  assert.match(body, /Base URL/);
  assert.match(body, /API key/);
  assert.match(body, /role="status"/);
});
