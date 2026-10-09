import assert from 'node:assert/strict';
import test from 'node:test';
async function client() {
  const api = await import('../src/lib/llm-api.ts').catch(() => null);
  assert.ok(api, 'LLM connection client must exist');
  return api;
}
async function withFetch(fake, run) {
  const original = globalThis.fetch;
  globalThis.fetch = fake;
  try { await run(); } finally { globalThis.fetch = original; }
}
test('connection and catalog reads use same-origin cookies', async () => {
  const api = await client();
  const paths = [];
  await withFetch(async (path, options) => {
    paths.push(path);
    assert.equal(options.credentials, 'same-origin');
    return Response.json(path === '/models' ? { models: [{ id: 'b', name: 'B' }], selected_model_id: 'b', selection_required: false } : { source: 'personal', base_url: 'https://llm.test/v1', has_api_key: true, selected_model_id: 'b' });
  }, async () => {
    assert.equal((await api.getLlmConnection()).has_api_key, true);
    assert.equal((await api.getModels()).selected_model_id, 'b');
  });
  assert.deepEqual(paths, ['/llm/connection', '/models']);
});
test('save distinguishes omitted key, explicit deletion, and a new key', async () => {
  const api = await client();
  const bodies = [];
  await withFetch(async (path, options) => {
    assert.equal(path, '/llm/connection');
    assert.equal(options.method, 'PUT');
    assert.equal(options.credentials, 'same-origin');
    assert.equal(options.headers['X-CSRF-Token'], 'csrf');
    bodies.push(JSON.parse(options.body));
    return Response.json({ models: [{ id: 'a', name: 'A' }], selected_model_id: 'a', selection_required: false });
  }, async () => {
    await api.saveLlmConnection('csrf', { base_url: 'https://llm.test/v1' });
    await api.saveLlmConnection('csrf', { base_url: 'https://llm.test/v1', api_key: '' });
    await api.saveLlmConnection('csrf', { base_url: 'https://other.test/v1', api_key: 'new-key' });
  });
  assert.deepEqual(bodies, [{ base_url: 'https://llm.test/v1' }, { base_url: 'https://llm.test/v1', api_key: '' }, { base_url: 'https://other.test/v1', api_key: 'new-key' }]);
});
test('disconnect accepts 204 without parsing JSON', async () => {
  const api = await client();
  await withFetch(async (path, options) => {
    assert.equal(options.method, 'DELETE');
    assert.equal(options.headers['X-CSRF-Token'], 'csrf');
    return new Response(null, { status: 204 });
  }, async () => assert.equal(await api.deleteLlmConnection('csrf'), undefined));
});
test('API errors retain status and hide raw provider details', async () => {
  const api = await client();
  for (const status of [401, 403, 422, 502, 503]) {
    await withFetch(async () => Response.json({ detail: 'private-key' }, { status }), async () => {
      await assert.rejects(api.getModels(), (error) => error instanceof api.LlmApiError && error.status === status && !error.message.includes('private-key'));
    });
  }
  await withFetch(async () => { throw new Error('private-network'); }, async () => {
    await assert.rejects(api.getModels(), (error) => error instanceof api.LlmApiError && !error.message.includes('private-network'));
  });
});

test('selection saves only model_id using cookie and CSRF', async () => {
  const api = await client();
  assert.equal(typeof api.selectLlmModel, 'function');
  await withFetch(async (path, options) => {
    assert.equal(path, '/llm/connection/model');
    assert.equal(options.method, 'PATCH');
    assert.equal(options.credentials, 'same-origin');
    assert.equal(options.headers['X-CSRF-Token'], 'csrf');
    assert.deepEqual(JSON.parse(options.body), { model_id: 'b' });
    return Response.json({ selected_model_id: 'b' });
  }, async () => assert.equal((await api.selectLlmModel('csrf', 'b')).selected_model_id, 'b'));
});
