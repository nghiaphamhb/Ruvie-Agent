import assert from 'node:assert/strict';
import test from 'node:test';
import { loadState, json } from './state-loader.mjs';
test('switching panels keeps draft credentials but invalidates pending probe', async () => {
  const mod = await loadState('../src/lib/features/embedding/embedding-state.svelte.ts');
  const state = mod.createEmbeddingState({
    csrfToken: 'csrf',
    onexpired() {},
    onforbidden() {},
    onapplied() {},
  });
  const previous = globalThis.fetch;
  let release;
  try {
    globalThis.fetch = async () =>
      json({
        configured: true,
        base_url: 'https://embed.test',
        has_api_key: true,
        model_id: 'baai/bge-m3',
        dimension: 1024,
        distance_metric: 'cosine',
        version: 1,
        updated_at: null,
      });
    await state.open();
    state.apiKey = 'draft-key';
    globalThis.fetch = () => new Promise((resolve) => (release = resolve));
    const pending = state.verify();
    assert.equal(typeof state.suspend, 'function');
    state.suspend();
    assert.equal(state.apiKey, 'draft-key');
    release(json({ version: 1, models: [] }));
    await pending;
    assert.equal(state.verified, false);
    assert.equal(state.catalogReady, false);
    assert.equal(state.busy, false);
  } finally {
    state.dispose();
    globalThis.fetch = previous;
  }
});

test('failed metadata reload preserves an unsaved embedding URL and key', async () => {
  const mod = await loadState('../src/lib/features/embedding/embedding-state.svelte.ts');
  const state = mod.createEmbeddingState({
    csrfToken: 'csrf',
    onexpired() {},
    onforbidden() {},
    onapplied() {},
  });
  const previous = globalThis.fetch;
  try {
    globalThis.fetch = async () =>
      json({
        configured: true,
        base_url: 'https://embed.test',
        has_api_key: true,
        model_id: 'baai/bge-m3',
        dimension: 1024,
        distance_metric: 'cosine',
        version: 1,
        updated_at: null,
      });
    await state.open();
    state.baseUrl = 'https://new.test';
    state.apiKey = 'unsaved-secret';
    globalThis.fetch = async () => {
      throw Error('offline');
    };
    assert.equal(await state.open(), false);
    assert.equal(state.baseUrl, 'https://new.test');
    assert.equal(state.apiKey, 'unsaved-secret');
    assert.equal(state.metadata.version, 1);
  } finally {
    state.dispose();
    globalThis.fetch = previous;
  }
});
