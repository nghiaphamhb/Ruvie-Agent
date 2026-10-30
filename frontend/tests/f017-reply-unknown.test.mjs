import assert from 'node:assert/strict';
import test from 'node:test';
import { loadState, json } from './state-loader.mjs';
test('unknown reply apply rereads metadata without claiming its own commit or retrying PUT', async () => {
  const mod = await loadState('../src/lib/features/llm/organization-llm-state.svelte.ts');
  const state = mod.createOrganizationLlmState({
    csrfToken: 'csrf',
    onexpired() {},
    onforbidden() {},
    onapplied() {
      assert.fail('unknown mutation cannot report success');
    },
  });
  const previous = globalThis.fetch;
  let puts = 0,
    gets = 0;
  const metadata = {
    configured: true,
    base_url: 'https://reply.test',
    has_api_key: true,
    allowed_model_ids: ['a'],
    default_model_id: 'a',
    version: 2,
    updated_at: null,
  };
  try {
    globalThis.fetch = async (path, init) => {
      if (init.method === 'PUT') {
        puts++;
        throw new Error('lost response');
      }
      if (path.endsWith('/verify')) return json({ models: [{ id: 'a', name: 'A' }], version: 2 });
      gets++;
      return json({ ...metadata, version: gets === 1 ? 2 : 3 });
    };
    await state.open();
    state.apiKey = 'draft-secret';
    await state.verify();
    assert.equal(await state.apply(), false);
    assert.equal(state.uncertain, true);
    assert.equal(state.saved, false);
    assert.equal(state.apiKey, '');
    assert.equal(state.metadata.version, 3);
    assert.equal(puts, 1);
    assert.equal(gets, 2);
  } finally {
    state.dispose();
    globalThis.fetch = previous;
  }
});
