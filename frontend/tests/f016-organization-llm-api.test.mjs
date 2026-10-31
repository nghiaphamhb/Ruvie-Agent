import assert from 'node:assert/strict';
import test from 'node:test';

test('admin client sends cookie/CSRF and explicit key actions only to admin endpoints', async () => {
  const api = await import('../src/lib/features/llm/organization-llm-api.ts').catch(() => null);
  assert.ok(api, 'organization API client is missing');
  const previous = globalThis.fetch;
  const calls = [];
  try {
    globalThis.fetch = async (path, init) => {
      calls.push([path, init]);
      return Response.json(
        path.endsWith('/verify')
          ? { models: [{ id: 'a', name: 'A' }], version: 0 }
          : {
              configured: true,
              base_url: 'https://provider.test/v1',
              has_api_key: true,
              network: { mode: 'direct', proxy_url: null },
              allowed_model_ids: ['a'],
              default_model_id: 'a',
              version: 1,
              updated_at: null,
            },
      );
    };
    await api.verifyOrganizationConnection('csrf', {
      base_url: 'https://provider.test/v1',
      key_action: 'clear',
      expected_version: 0,
      network: { mode: 'direct', proxy_url: null },
    });
    await api.applyOrganizationConnection('csrf', {
      base_url: 'https://provider.test/v1',
      key_action: 'replace',
      api_key: 'draft-key',
      expected_version: 0,
      network: { mode: 'direct', proxy_url: null },
      allowed_model_ids: ['a'],
      default_model_id: 'a',
    });
    assert.deepEqual(
      calls.map(([path]) => path),
      ['/admin/llm/connection/verify', '/admin/llm/connection'],
    );
    for (const [, init] of calls) {
      assert.equal(init.credentials, 'same-origin');
      assert.equal(init.headers['X-CSRF-Token'], 'csrf');
      assert.equal(init.cache, 'no-store');
    }
    assert.equal(JSON.parse(calls[0][1].body).api_key, undefined);
  } finally {
    globalThis.fetch = previous;
  }
});

test('admin errors keep safe codes and never retry a mutation or expose raw detail', async () => {
  const api = await import('../src/lib/features/llm/organization-llm-api.ts').catch(() => null);
  assert.ok(api);
  const previous = globalThis.fetch;
  let calls = 0;
  try {
    globalThis.fetch = async () => {
      calls++;
      return Response.json(
        { detail: { code: 'admin_required', secret: 'private-key' } },
        { status: 403 },
      );
    };
    await assert.rejects(
      api.getOrganizationConnection(),
      (error) => error.code === 'admin_required' && !String(error).includes('private-key'),
    );
    globalThis.fetch = async () => {
      calls++;
      throw Error('private-upstream');
    };
    await assert.rejects(
      api.applyOrganizationConnection('csrf', {}),
      (error) => error.uncertain && !String(error).includes('private-upstream'),
    );
    assert.equal(calls, 2);
  } finally {
    globalThis.fetch = previous;
  }
});
