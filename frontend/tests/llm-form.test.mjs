import assert from 'node:assert/strict';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

test('organization form exposes explicit key actions, verify/apply and controlled policy with disabled semantics', async () => {
  const server = await createServer({
    root: fileURLToPath(new URL('../', import.meta.url)),
    cacheDir: fileURLToPath(new URL('../dist/.f016-form-cache', import.meta.url)),
    configFile: false,
    plugins: [svelte()],
    server: { middlewareMode: true, hmr: false },
    appType: 'custom',
  });
  try {
    const { default: Form } = await server.ssrLoadModule(
      '/src/lib/features/llm/LlmConnectionForm.svelte',
    );
    const { render } = await server.ssrLoadModule('svelte/server');
    const { initI18n } = await server.ssrLoadModule('/src/lib/i18n/index.ts');
    await initI18n();
    const state = {
      metadata: { configured: true, has_api_key: true },
      baseUrl: 'https://provider.test/v1',
      apiKey: '',
      keyAction: 'replace',
      busy: false,
      verified: true,
      canApply: false,
      canKeep: true,
      uncertain: false,
      errorCode: null,
      saved: false,
      models: [{ id: 'a', name: 'A', available: true }],
      allowedModelIds: ['a'],
      defaultModelId: 'a',
      open() {},
      close() {},
      verify() {},
      apply() {},
      setPolicy() {},
    };
    const html = render(Form, { props: { state, disabled: true, active: false } }).body;
    assert.match(html, /<fieldset[^>]*disabled/);
    assert.match(html, /type="password"/);
    assert.match(html, /aria-haspopup="listbox"/);
    assert.match(html, /class="key-chevron/);
    assert.match(html, /role="tooltip"/);
    assert.match(html, /data-key-action="keep"/);
    assert.match(html, /data-key-action="clear"/);
    assert.match(html, /data-key-action="replace"/);
    assert.match(html, /role="status"/);
    assert.match(html, /<table/);
    assert.match(html, /class="form-footer/);
    assert.match(html, /type="checkbox"/);
    assert.match(html, /type="radio"/);
    assert.match(html, /role="status"/);
    assert.doesNotMatch(html, /Using your personal connection/);
    state.errorCode = 'llm_settings_unavailable';
    const failureHtml = render(Form, { props: { state, active: false } }).body;
    assert.doesNotMatch(failureHtml, /Chưa có kết nối LLM hoặc không thể lưu cấu hình/);
  } finally {
    await server.close();
  }
});
