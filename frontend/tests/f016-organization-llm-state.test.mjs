import assert from 'node:assert/strict';
import test from 'node:test';
import { loadState, json } from './state-loader.mjs';

const metadata = {
  configured: true,
  base_url: 'https://provider.test/v1',
  has_api_key: true,
  allowed_model_ids: ['a'],
  default_model_id: 'a',
  version: 2,
  updated_at: null,
};
async function owner(callbacks = {}) {
  const module = await loadState('../src/lib/features/llm/organization-llm-state.svelte.ts');
  assert.ok(module, 'organization state is missing');
  return module.createOrganizationLlmState({
    csrfToken: 'csrf',
    onexpired() {
      assert.fail('unexpected expiry');
    },
    onforbidden() {
      assert.fail('unexpected role loss');
    },
    onapplied() {},
    ...callbacks,
  });
}
test('verify edits only the draft; apply uses version and clears key after committed metadata', async () => {
  const state = await owner();
  const previous = globalThis.fetch;
  const bodies = [];
  try {
    globalThis.fetch = async (path, init) => {
      if (init?.body) bodies.push(JSON.parse(init.body));
      if (path.endsWith('/verify'))
        return json({
          models: [
            { id: 'a', name: 'A' },
            { id: 'b', name: 'B' },
          ],
          version: 2,
        });
      return json(init?.method === 'PUT' ? { ...metadata, version: 3 } : metadata);
    };
    await state.open();
    state.apiKey = 'draft-secret';
    state.keyAction = 'replace';
    await state.verify();
    assert.equal(state.verified, true);
    assert.equal(state.metadata.version, 2);
    state.setPolicy({ allowedModelIds: ['b'], defaultModelId: 'b' });
    assert.equal(await state.apply(), true);
    assert.equal(state.apiKey, '');
    assert.equal(state.metadata.version, 3);
    assert.equal(bodies[1].expected_version, 2);
    assert.deepEqual(bodies[1].allowed_model_ids, ['b']);
  } finally {
    state.dispose();
    globalThis.fetch = previous;
  }
});
test('closing while verify runs ignores late responses and clears draft secrets', async () => {
  const state = await owner();
  const previous = globalThis.fetch;
  let release;
  try {
    globalThis.fetch = async () => json(metadata);
    await state.open();
    state.apiKey = 'draft-secret';
    state.keyAction = 'replace';
    globalThis.fetch = () =>
      new Promise((resolve) => {
        release = resolve;
      });
    const pending = state.verify();
    state.close();
    release(json({ models: [{ id: 'a', name: 'A' }], version: 2 }));
    await pending;
    assert.equal(state.apiKey, '');
    assert.equal(state.verified, false);
    assert.deepEqual(state.models, []);
  } finally {
    state.dispose();
    globalThis.fetch = previous;
  }
});
test('conflict and uncertain apply never retry; CSRF 403 does not imply role loss', async () => {
  let forbidden = 0;
  const state = await owner({
    onforbidden() {
      forbidden++;
    },
  });
  const previous = globalThis.fetch;
  try {
    globalThis.fetch = async (path) =>
      json(path.endsWith('/verify') ? { models: [{ id: 'a', name: 'A' }], version: 2 } : metadata);
    await state.open();
    await state.verify();
    let calls = 0;
    globalThis.fetch = async () => {
      calls++;
      return json({ detail: { code: 'configuration_conflict' } }, 409);
    };
    assert.equal(await state.apply(), false);
    assert.equal(calls, 1);
    assert.equal(state.verified, false);
    assert.equal(state.errorCode, 'configuration_conflict');
    globalThis.fetch = async () => json({ models: [{ id: 'a', name: 'A' }], version: 2 });
    await state.verify();
    globalThis.fetch = async (_path, init) => {
      if (init?.method === 'PUT') calls++;
      throw Error('lost');
    };
    await state.apply();
    assert.equal(state.uncertain, true);
    assert.equal(calls, 2);
    assert.equal(state.apiKey, '');
    globalThis.fetch = async () => json({ detail: { code: 'csrf_invalid' } }, 403);
    await state.open();
    assert.equal(forbidden, 0);
  } finally {
    state.dispose();
    globalThis.fetch = previous;
  }
});
test('editing connection invalidates verification and disallows sending the old key to another URL', async () => {
  const state = await owner();
  const previous = globalThis.fetch;
  try {
    globalThis.fetch = async (path) =>
      json(path.endsWith('/verify') ? { models: [{ id: 'a', name: 'A' }], version: 2 } : metadata);
    await state.open();
    await state.verify();
    assert.equal(state.verified, true);
    state.apiKey = 'draft-secret';
    state.baseUrl = 'https://other.test/v1';
    assert.equal(state.verified, false);
    assert.equal(state.apiKey, '');
    assert.equal(state.keyAction, 'clear');
    assert.equal(await state.apply(), false);
  } finally {
    state.dispose();
    globalThis.fetch = previous;
  }
});

test('reload returns a result only for the current completed request', async () => {
  const state = await owner();
  const previous = globalThis.fetch;
  try {
    globalThis.fetch = async () => json(metadata);
    assert.equal(await state.open(), true);
    globalThis.fetch = async () => json({ detail: { code: 'llm_settings_unavailable' } }, 503);
    assert.equal(await state.open(), false);
    let release;
    globalThis.fetch = () => new Promise((resolve) => (release = resolve));
    const pending = state.open();
    state.close();
    release(json(metadata));
    assert.equal(await pending, undefined);
  } finally {
    state.dispose();
    globalThis.fetch = previous;
  }
});
