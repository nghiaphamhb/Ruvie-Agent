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
  try {
    return await run();
  } finally {
    globalThis.fetch = original;
  }
}

test('login sends credentials using same-origin cookie mode', async () => {
  const { login } = await loadClient();
  const payload = {
    user: { id: 'u1', display_name: 'Person', system_role: 'user' },
    csrf_token: 'csrf',
  };
  await withFetch(
    async (url, options) => {
      assert.equal(url, '/auth/login');
      assert.equal(options.method, 'POST');
      assert.equal(options.credentials, 'same-origin');
      assert.deepEqual(JSON.parse(options.body), {
        email: 'person@example.test',
        password: 'secret',
      });
      return Response.json(payload);
    },
    async () => assert.deepEqual(await login('person@example.test', 'secret'), payload),
  );
});

test('session treats 401 as signed out and logout sends CSRF header', async () => {
  const { getAuthSession, logout } = await loadClient();
  await withFetch(
    async (url, options) => {
      if (url === '/auth/session') return new Response('', { status: 401 });
      assert.equal(url, '/auth/logout');
      assert.equal(options.headers['X-CSRF-Token'], 'csrf-token');
      return new Response(null, { status: 204 });
    },
    async () => {
      assert.equal(await getAuthSession(), null);
      await logout('csrf-token');
    },
  );
});

test('password change sends only its fields with same-origin cookie and CSRF', async () => {
  const api = await import('../src/lib/features/auth/auth-api.ts');
  assert.equal(typeof api.changePassword, 'function');
  let calls = 0;
  const command = {
    current_password: ' current-password ',
    new_password: ' new-password-123 ',
    password_confirmation: ' new-password-123 ',
  };
  await withFetch(
    async (url, init) => {
      calls++;
      assert.equal(url, '/auth/password');
      assert.equal(init.method, 'POST');
      assert.equal(init.credentials, 'same-origin');
      assert.equal(init.cache, 'no-store');
      assert.equal(init.headers['X-CSRF-Token'], 'csrf-token');
      assert.deepEqual(JSON.parse(init.body), command);
      return new Response(null, { status: 204 });
    },
    async () => {
      await api.changePassword('csrf-token', command);
      assert.equal(calls, 1);
    },
  );
});

test('password change maps safe field errors without exposing server text or retrying', async () => {
  const api = await import('../src/lib/features/auth/auth-api.ts');
  assert.equal(typeof api.changePassword, 'function');
  let calls = 0;
  await withFetch(
    async () => {
      calls++;
      return Response.json(
        {
          detail: {
            code: 'current_password_incorrect',
            fields: { current_password: 'current_password_incorrect', arbitrary: 'secret-marker' },
            input: 'secret-marker',
          },
        },
        { status: 422 },
      );
    },
    async () => {
      await assert.rejects(
        api.changePassword('csrf-token', {
          current_password: 'secret-marker',
          new_password: 'new-password-123',
          password_confirmation: 'new-password-123',
        }),
        (error) => {
          assert.equal(error.status, 422);
          assert.equal(error.code, 'current_password_incorrect');
          assert.deepEqual(Object.keys(error.fieldErrors), ['current_password']);
          assert.doesNotMatch(error.message, /secret-marker/);
          assert.doesNotMatch(error.uiMessage.key, /secret-marker/);
          return true;
        },
      );
      assert.equal(calls, 1);
    },
  );
});

test('network failure on password change is marked as an uncertain result', async () => {
  const api = await import('../src/lib/features/auth/auth-api.ts');
  assert.equal(typeof api.changePassword, 'function');
  await withFetch(
    async () => {
      throw new TypeError('secret-marker');
    },
    async () => {
      await assert.rejects(
        api.changePassword('csrf-token', {
          current_password: 'current-password',
          new_password: 'new-password-123',
          password_confirmation: 'new-password-123',
        }),
        (error) => {
          assert.equal(error.code, 'result_unknown');
          assert.doesNotMatch(error.message, /secret-marker/);
          return true;
        },
      );
    },
  );
});

test('register sends only three fields and preserves password whitespace using cookies', async () => {
  const api = await import('../src/lib/features/auth/auth-api.ts');
  assert.equal(typeof api.register, 'function', 'registration client is required');
  const session = {
    user: { id: 'new', display_name: 'Nguyễn An', system_role: 'admin' },
    csrf_token: 'csrf',
  };
  await withFetch(
    async (url, init) => {
      assert.equal(url, '/auth/register');
      assert.equal(init.credentials, 'same-origin');
      assert.equal(init.method, 'POST');
      assert.deepEqual(JSON.parse(init.body), {
        display_name: 'Nguyễn An',
        email: 'AN@example.test',
        password: ' secret-password ',
      });
      return Response.json(session, { status: 201 });
    },
    async () =>
      assert.deepEqual(
        await api.register(' Nguyễn An ', ' AN@example.test ', ' secret-password '),
        session,
      ),
  );
});
test('register maps duplicate and validation fields without displaying raw server input', async () => {
  const api = await import('../src/lib/features/auth/auth-api.ts');
  assert.equal(typeof api.register, 'function');
  for (const [status, body, field, key] of [
    [
      409,
      { detail: { code: 'email_taken', fields: { email: 'email_taken' } } },
      'email',
      'auth.errors.emailTaken',
    ],
    [
      422,
      {
        detail: {
          code: 'validation_error',
          fields: { password: 'password_length', role: 'secret' },
          input: 'unsafe password',
        },
      },
      'password',
      'auth.errors.passwordLength',
    ],
  ]) {
    await withFetch(
      async () => Response.json(body, { status }),
      async () => {
        await assert.rejects(api.register('Name', 'an@example.test', 'password-long'), (error) => {
          assert.equal(error.status, status);
          assert.equal(error.fieldErrors[field].key, key);
          assert.equal(error.fieldErrors.role, undefined);
          assert.equal(String(error).includes('unsafe'), false);
          return true;
        });
      },
    );
  }
});
test('register network and server failure never retries automatically', async () => {
  const api = await import('../src/lib/features/auth/auth-api.ts');
  assert.equal(typeof api.register, 'function');
  for (const fake of [
    async () => {
      throw Error('private network error');
    },
    async () => Response.json({ detail: 'secret SQL' }, { status: 500 }),
  ]) {
    let calls = 0;
    await withFetch(
      async (...args) => {
        calls++;
        return fake(...args);
      },
      async () => {
        await assert.rejects(api.register('Name', 'an@example.test', 'password-long'), (error) => {
          assert.ok(
            error.uiMessage.key.startsWith('auth.') ||
              error.uiMessage.key === 'common.errors.network',
          );
          assert.equal(String(error).includes('secret'), false);
          return true;
        });
        assert.equal(calls, 1);
      },
    );
  }
});

test('setup reads a strict boolean without caching or creating a session', async () => {
  const api = await loadClient();
  assert.equal(typeof api.getAuthSetup, 'function');
  for (const requires_initial_admin of [true, false]) {
    await withFetch(
      async (url, options) => {
        assert.equal(url, '/auth/setup');
        assert.equal(options.credentials, 'same-origin');
        assert.equal(options.cache, 'no-store');
        return Response.json({ requires_initial_admin });
      },
      async () => assert.deepEqual(await api.getAuthSetup(), { requires_initial_admin }),
    );
  }
});

test('setup unavailable or malformed is never interpreted as an empty database', async () => {
  const api = await loadClient();
  assert.equal(typeof api.getAuthSetup, 'function');
  for (const response of [
    Response.json({ detail: 'private SQL' }, { status: 503 }),
    Response.json({}),
    Response.json({ requires_initial_admin: 'true' }),
    new Response('private invalid JSON'),
  ]) {
    await withFetch(
      async () => response,
      async () => {
        await assert.rejects(api.getAuthSetup(), (error) => {
          assert.equal(error.uiMessage.key, 'auth.errors.setup');
          assert.equal(String(error).includes('private'), false);
          return true;
        });
      },
    );
  }
});

test('bootstrap conflict preserves the code and does not invent an email field error', async () => {
  const api = await loadClient();
  await withFetch(
    async () => Response.json({ detail: { code: 'setup_already_completed' } }, { status: 409 }),
    async () =>
      assert.rejects(api.register('Name', 'name@example.test', 'password-long'), (error) => {
        assert.equal(error.code, 'setup_already_completed');
        assert.equal(error.uiMessage.key, 'auth.errors.setupCompleted');
        assert.deepEqual(error.fieldErrors, {});
        return true;
      }),
  );
});

test('unknown conflict codes never masquerade as email conflicts', async () => {
  const api = await loadClient();
  await withFetch(
    async () =>
      Response.json({ detail: { code: 'unrecognized', input: 'private' } }, { status: 409 }),
    async () =>
      assert.rejects(api.register('Name', 'name@example.test', 'password-long'), (error) => {
        assert.deepEqual(error.fieldErrors, {});
        assert.equal(error.uiMessage.key, 'auth.errors.registrationFailed');
        return true;
      }),
  );
});

test('session reads do not cache', async () => {
  const api = await loadClient();
  let observed;
  await withFetch(
    async (_url, options) => {
      observed = options;
      return Response.json({
        user: { id: 'u', display_name: 'U', system_role: 'user' },
        csrf_token: 'csrf',
      });
    },
    async () => {
      await api.getAuthSession();
      assert.equal(observed.cache, 'no-store');
    },
  );
});

test('session rejects missing or unknown server roles', async () => {
  const api = await loadClient();
  for (const role of [undefined, 'owner', null]) {
    await withFetch(
      async () => {
        return Response.json({
          user: { id: 'u', display_name: 'U', system_role: role },
          csrf_token: 'csrf',
        });
      },
      async () => assert.rejects(api.getAuthSession(), api.AuthApiError),
    );
  }
});

test('disabled login is recognized only for the exact 403 code', async () => {
  const { login } = await loadClient();
  for (const [status, payload, expected] of [
    [403, { detail: { code: 'account_disabled' } }, 'auth.errors.accountDisabled'],
    [401, { detail: { code: 'account_disabled' } }, 'auth.errors.credentials'],
    [403, { detail: { code: 'origin_not_allowed' } }, 'auth.errors.request'],
    [403, {}, 'auth.errors.request'],
  ]) {
    let calls = 0;
    await withFetch(
      async () => {
        calls++;
        return Response.json(payload, { status });
      },
      async () => {
        await assert.rejects(
          login('user@example.test', 'secret'),
          (error) => error.uiMessage.key === expected && error.status === status,
        );
      },
    );
    assert.equal(calls, 1);
  }
  await withFetch(
    async () => new Response('{', { status: 403 }),
    async () => {
      await assert.rejects(
        login('user@example.test', 'secret'),
        (error) => error.uiMessage.key === 'auth.errors.request',
      );
    },
  );
  await withFetch(
    async () => {
      throw new Error('private network detail');
    },
    async () => {
      await assert.rejects(
        login('user@example.test', 'secret'),
        (error) =>
          error.uiMessage.key === 'common.errors.network' &&
          !JSON.stringify(error).includes('private network detail'),
      );
    },
  );
});
