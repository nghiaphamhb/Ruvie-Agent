import assert from 'node:assert/strict';
import test from 'node:test';
import { readFile } from 'node:fs/promises';
import { compile } from 'svelte/compiler';
import { render } from 'svelte/server';

test('connection form labels URL/key and disables editing while chat runs', async () => {
  const url = new URL('../src/lib/components/LlmConnectionForm.svelte', import.meta.url);
  const source = await readFile(url, 'utf8').catch(() => null);
  assert.ok(source, 'Connection form must exist');
  const compiled = compile(source, { filename: url.pathname, generate: 'server' }).js.code;
  const code = compiled.replace(/from ['"]([^'"]+)['"]/g, (match, specifier) => {
    const resolved = specifier.startsWith('.') ? new URL(specifier + (specifier.endsWith('.ts') ? '' : '.ts'), url).href : import.meta.resolve(specifier);
    return `from '${resolved}'`;
  });
  const { default: Form } = await import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
  const { body } = render(Form, { props: { csrfToken: 'csrf', disabled: true, onexpired() {}, onbusychange() {} } });
  assert.match(body, /<fieldset[^>]*disabled/);
  assert.match(body, /type="password"/);
  assert.match(body, /Base URL/);
  assert.match(body, /API key/);
  assert.match(body, /role="status"/);
});
