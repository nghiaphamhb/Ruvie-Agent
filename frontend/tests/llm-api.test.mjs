import assert from 'node:assert/strict';
import test from 'node:test';
async function client() {
  const api = await import('../src/lib/features/llm/llm-api.ts').catch(() => null);
  assert.ok(api, 'LLM connection client must exist');
  return api;
}
async function withFetch(fake, run) {
  const original = globalThis.fetch;
  globalThis.fetch = fake;
  try {
    await run();
  } finally {
    globalThis.fetch = original;
  }
}
test('connection and catalog reads use same-origin cookies', async () => {
  const api = await client();
  const paths = [];
  await withFetch(
    async (path, options) => {
      paths.push(path);
      assert.equal(options.credentials, 'same-origin');
      return Response.json(
        path === '/models'
          ? { models: [{ id: 'b', name: 'B' }], selected_model_id: 'b', selection_required: false }
          : {
              configured: true,
              configuration_version: 1,
              selected_model_id: 'b',
            },
      );
    },
    async () => {
      assert.equal((await api.getLlmConnection()).configured, true);
      assert.equal((await api.getModels()).selected_model_id, 'b');
    },
  );
  assert.deepEqual(paths, ['/llm/connection', '/models']);
});
test('personal credential mutations are not exported by the employee client', async () => {
  const api = await client();
  assert.equal(api.saveLlmConnection, undefined);
  assert.equal(api.deleteLlmConnection, undefined);
});

test('API errors retain status and hide raw provider details', async () => {
  const api = await client();
  for (const status of [401, 403, 422, 502, 503]) {
    await withFetch(
      async () => Response.json({ detail: 'private-key' }, { status }),
      async () => {
        await assert.rejects(
          api.getModels(),
          (error) =>
            error instanceof api.LlmApiError &&
            error.status === status &&
            !error.message.includes('private-key'),
        );
      },
    );
  }
  await withFetch(
    async () => {
      throw new Error('private-network');
    },
    async () => {
      await assert.rejects(
        api.getModels(),
        (error) => error instanceof api.LlmApiError && !error.message.includes('private-network'),
      );
    },
  );
});

test('selection saves only model_id using cookie and CSRF', async () => {
  const api = await client();
  assert.equal(typeof api.selectLlmModel, 'function');
  await withFetch(
    async (path, options) => {
      assert.equal(path, '/llm/connection/model');
      assert.equal(options.method, 'PATCH');
      assert.equal(options.credentials, 'same-origin');
      assert.equal(options.headers['X-CSRF-Token'], 'csrf');
      assert.deepEqual(JSON.parse(options.body), { model_id: 'b' });
      return Response.json({ selected_model_id: 'b' });
    },
    async () => assert.equal((await api.selectLlmModel('csrf', 'b')).selected_model_id, 'b'),
  );
});
