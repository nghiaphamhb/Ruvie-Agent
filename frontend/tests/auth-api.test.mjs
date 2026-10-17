import assert from 'node:assert/strict';
import test from 'node:test';

async function loadClient() {
  const client = await import('../src/lib/features/auth/auth-api.ts').catch(() => null);
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

test('register sends only three fields and preserves password whitespace using cookies', async () => {
  const api = await import('../src/lib/features/auth/auth-api.ts');
  assert.equal(typeof api.register, 'function', 'registration client is required');
  const session = { user: { id: 'new', display_name: 'Nguyễn An' }, csrf_token: 'csrf' };
  await withFetch(async (url, init) => {
    assert.equal(url, '/auth/register');
    assert.equal(init.credentials, 'same-origin');
    assert.equal(init.method, 'POST');
    assert.deepEqual(JSON.parse(init.body), {
      display_name: 'Nguyễn An', email: 'AN@example.test', password: ' secret-password '
    });
    return Response.json(session, { status: 201 });
  }, async () => assert.deepEqual(await api.register(' Nguyễn An ', ' AN@example.test ', ' secret-password '), session));
});
test('register maps duplicate and validation fields without displaying raw server input', async () => {
  const api = await import('../src/lib/features/auth/auth-api.ts');
  assert.equal(typeof api.register, 'function');
  for (const [status, body, field, key] of [
    [409, { detail: { code: 'email_taken', fields: { email: 'email_taken' } } }, 'email', 'auth.errors.emailTaken'],
    [422, { detail: { code: 'validation_error', fields: { password: 'password_length', role: 'secret' },
                      input: 'unsafe password' } }, 'password', 'auth.errors.passwordLength'],
  ]) {
    await withFetch(async () => Response.json(body, { status }), async () => {
      await assert.rejects(api.register('Name', 'an@example.test', 'password-long'), error => {
        assert.equal(error.status, status);
        assert.equal(error.fieldErrors[field].key, key);
        assert.equal(error.fieldErrors.role, undefined);
        assert.equal(String(error).includes('unsafe'), false);
        return true;
      });
    });
  }
});
test('register network and server failure never retries automatically', async () => {
  const api = await import('../src/lib/features/auth/auth-api.ts');
  assert.equal(typeof api.register, 'function');
  for (const fake of [async () => { throw Error('private network error'); },
                      async () => Response.json({detail:'secret SQL'}, {status:500})]) {
    let calls = 0;
    await withFetch(async (...args) => { calls++; return fake(...args); }, async () => {
      await assert.rejects(api.register('Name', 'an@example.test', 'password-long'), error => {
        assert.ok(error.uiMessage.key.startsWith('auth.') || error.uiMessage.key === 'common.errors.network');
        assert.equal(String(error).includes('secret'), false);
        return true;
      });
      assert.equal(calls, 1);
    });
  }
});
