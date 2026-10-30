import assert from 'node:assert/strict';
import test from 'node:test';
import { loadState, json } from './state-loader.mjs';

/** State-level network regression; real Playwright rendering must be run separately. */
for (const embedding of [false, true]) {
  test(`F018 ${embedding ? 'embedding' : 'reply'} draft follows selected network`, async () => {
    const mod = await loadState(embedding
      ? '../src/lib/features/embedding/embedding-state.svelte.ts'
      : '../src/lib/features/llm/organization-llm-state.svelte.ts');
    const state = (embedding ? mod.createEmbeddingState : mod.createOrganizationLlmState)({
      csrfToken: 'csrf', onexpired() {}, onforbidden() {}, onapplied() {},
    });
    const previous = globalThis.fetch;
    const bodies = [];
    try {
      globalThis.fetch = async (path, init = {}) => {
        if (init.body) bodies.push(JSON.parse(init.body));
        if (path.endsWith('/catalog') || path.endsWith('/verify'))
          return json({ version: 1, models: [{ id: 'baai/bge-m3', name: 'BGE', supported: true }] });
        return json({
          configured: true, base_url: 'https://provider.test/v1', has_api_key: true,
          network: { mode: 'direct', proxy_url: null }, version: 1, updated_at: null,
          ...(embedding
            ? { model_id: 'baai/bge-m3', dimension: 1024, distance_metric: 'cosine' }
            : { allowed_model_ids: ['baai/bge-m3'], default_model_id: 'baai/bge-m3' }),
        });
      };
      await state.open();
      state.networkMode = 'proxy';
      state.proxyUrl = 'socks5://127.0.0.1:12334';
      assert.equal(state.dirty, true);
      await state.verify();
      assert.deepEqual(bodies[0].network, {
        mode: 'proxy', proxy_url: 'socks5://127.0.0.1:12334',
      });
      state.networkMode = 'direct';
      assert.equal(state.verified, false);
      await state.verify();
      assert.deepEqual(bodies[1].network, { mode: 'direct', proxy_url: null });
      assert.equal(state.keyAction, 'keep');
    } finally {
      state.dispose();
      globalThis.fetch = previous;
    }
  });
}
