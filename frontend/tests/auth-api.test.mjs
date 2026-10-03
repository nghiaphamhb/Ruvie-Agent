import assert from 'node:assert/strict';
import test from 'node:test';

async function loadClient() {
  const client = await import('../src/lib/auth-api.ts').catch(() => null);
  assert.ok(client, 'auth API client must exist');
  return client;
}

async function withFetch(fake, run) {
  const original = globalThis.fetch;
  globalThis.fetch = fake;
  try { return await run(); } finally { globalThis.fetch = original; }
}

test('login sends credentials using same-origin cookie mode', async () => {
  const { login } = await loadClient();
  const payload = { user: { id: 'u1', display_name: 'Person' }, csrf_token: 'csrf' };
  await withFetch(async (url, options) => {
    assert.equal(url, '/auth/login');
    assert.equal(options.method, 'POST');
    assert.equal(options.credentials, 'same-origin');
    assert.deepEqual(JSON.parse(options.body), { email: 'person@example.test', password: 'secret' });
    return Response.json(payload);
  }, async () => assert.deepEqual(await login('person@example.test', 'secret'), payload));
});

test('session treats 401 as signed out and logout sends CSRF header', async () => {
  const { getAuthSession, logout } = await loadClient();
  await withFetch(async (url, options) => {
    if (url === '/auth/session') return new Response('', { status: 401 });
    assert.equal(url, '/auth/logout');
    assert.equal(options.headers['X-CSRF-Token'], 'csrf-token');
    return new Response(null, { status: 204 });
  }, async () => {
    assert.equal(await getAuthSession(), null);
    await logout('csrf-token');
  });
});
