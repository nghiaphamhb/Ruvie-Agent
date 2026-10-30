import assert from 'node:assert/strict';
import test from 'node:test';
import { loadState, json } from './state-loader.mjs';
const metadata = {
  configured: true,
  base_url: 'https://embed.test/v1',
  has_api_key: true,
  network: { mode: 'direct', proxy_url: null },
  model_id: 'baai/bge-m3',
  dimension: 1024,
  distance_metric: 'cosine',
  version: 2,
  updated_at: null,
};
async function owner() {
  const mod = await loadState('../src/lib/features/embedding/embedding-state.svelte.ts');
  assert.ok(mod, 'embedding owner missing');
  return mod.createEmbeddingState({
    csrfToken: 'csrf',
    onexpired() {
      assert.fail('expiry');
    },
    onforbidden() {
      assert.fail('role');
    },
    onapplied() {},
  });
}
test('unsupported selection remains selected and cannot apply; verify does not save', async () => {
  const state = await owner();
  const previous = globalThis.fetch;
  const requests = [];
  try {
    globalThis.fetch = async (path, init) => {
      requests.push([path, init]);
      if (path.endsWith('/catalog'))
        return json({
          version: 2,
          models: [
            { id: 'baai/bge-m3', name: 'BGE', dimension: null, supported: true, reason_code: null },
            {
              id: 'other',
              name: 'Other',
              dimension: 1024,
              supported: false,
              reason_code: 'embedding_model_unsupported',
            },
          ],
        });
      if (path.endsWith('/verify'))
        return json({
          version: 2,
          model_id: 'baai/bge-m3',
          dimension: 1024,
          distance_metric: 'cosine',
          compatible: true,
        });
      return json(init.method === 'PUT' ? { ...metadata, version: 3 } : metadata);
    };
    await state.open();
    await state.verify();
    state.selectModel('other');
    assert.equal(state.defaultModelId, 'other');
    assert.equal(state.canApply, false);
    assert.equal(await state.apply(), false);
    state.selectModel('baai/bge-m3');
    await state.probe();
    assert.equal(state.canApply, true);
    assert.equal(state.metadata.version, 2);
    await state.apply();
    assert.equal(state.metadata.version, 3);
    assert.equal(state.apiKey, '');
    assert.equal(requests.filter(([, init]) => init.method === 'PUT').length, 1);
  } finally {
    state.dispose();
    globalThis.fetch = previous;
  }
});
test('close invalidates late catalog and erases secret', async () => {
  const state = await owner();
  const previous = globalThis.fetch;
  let release;
  try {
    globalThis.fetch = async () => json(metadata);
    await state.open();
    state.apiKey = 'secret';
    globalThis.fetch = () => new Promise((resolve) => (release = resolve));
    const pending = state.verify();
    state.close();
    release(json({ version: 2, models: [] }));
    await pending;
    assert.equal(state.apiKey, '');
    assert.equal(state.models.length, 0);
    assert.equal(state.verified, false);
  } finally {
    state.dispose();
    globalThis.fetch = previous;
  }
});
