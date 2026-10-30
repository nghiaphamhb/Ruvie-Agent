import assert from 'node:assert/strict';
import test from 'node:test';

const account = {
  id: 'new',
  display_name: 'An',
  email: 'an@example.test',
  system_role: 'admin',
  is_active: true,
  created_at: '2026-10-23T12:00:00Z',
};
const input = {
  display_name: ' An ',
  email: ' AN@example.test ',
  password: ' password12345 ',
  system_role: 'admin',
};
async function api() {
  const result = await import('../src/lib/features/admin/admin-api.ts').catch(() => null);
  assert.ok(result, 'Admin account HTTP client must exist');
  return result;
}
const json = (body, status = 200) => new Response(JSON.stringify(body), { status });

test('list accounts encodes a bounded page/search and returns only safe metadata', async () => {
  const { listAccounts } = await api();
  assert.equal(typeof listAccounts, 'function', 'Paginated account list client must exist');
  const previous = globalThis.fetch;
  try {
    globalThis.fetch = async (url, init) => {
      assert.equal(url, '/admin/users/list?q=An+%2B+%25_&page=2&page_size=10');
      assert.equal(init.credentials, 'same-origin');
      assert.equal(init.cache, 'no-store');
      return json({
        users: [{ ...account, password_hash: 'private' }],
        total: 11,
        page: 2,
        page_size: 10,
      });
    };
    assert.deepEqual(await listAccounts({ q: ' An + %_ ', page: 2, page_size: 10 }), {
      users: [account],
      total: 11,
      page: 2,
      page_size: 10,
    });
    globalThis.fetch = async (url) => {
      assert.equal(url, '/admin/users/list?q=&page=1&page_size=20');
      return json({ users: [], total: 0, page: 1, page_size: 20 });
    };
    assert.deepEqual(await listAccounts(), { users: [], total: 0, page: 1, page_size: 20 });
  } finally {
    globalThis.fetch = previous;
  }
});

test('list rejects malformed pagination/accounts and safely propagates permission failures', async () => {
  const { listAccounts, AdminApiError } = await api();
  assert.equal(typeof listAccounts, 'function', 'Paginated account list client must exist');
  const previous = globalThis.fetch;
  const valid = { users: [account], total: 1, page: 1, page_size: 20 };
  try {
    for (const payload of [
      null,
      {},
      { ...valid, users: null },
      { ...valid, total: -1 },
      { ...valid, total: '1' },
      { ...valid, page: 2 },
      { ...valid, page_size: 1000 },
      { ...valid, users: Array(21).fill(account) },
      { ...valid, total: 0 },
      { ...valid, users: [{ ...account, created_at: undefined }] },
    ]) {
      globalThis.fetch = async () => json(payload);
      await assert.rejects(listAccounts(), AdminApiError);
    }
    for (const [status, code] of [
      [401, 'authentication_required'],
      [403, 'admin_required'],
      [503, 'account_lookup_unavailable'],
    ]) {
      globalThis.fetch = async () => json({ detail: { code, private: 'secret' } }, status);
      await assert.rejects(
        listAccounts(),
        (error) =>
          error.code === code &&
          error.status === status &&
          !JSON.stringify(error).includes('secret'),
      );
    }
    for (const options of [
      { page: 0 },
      { page: 1.5 },
      { page: 1000001 },
      { page_size: 101 },
      { q: 'x'.repeat(256) },
    ]) {
      let calls = 0;
      globalThis.fetch = async () => {
        calls++;
        return json(valid);
      };
      await assert.rejects(listAccounts(options), AdminApiError);
      assert.equal(calls, 0, 'Invalid list query must not be sent');
    }
  } finally {
    globalThis.fetch = previous;
  }
});

test('directory presence validates timestamps and exposes only the displayed users', async () => {
  const { listAccounts, AdminApiError } = await api();
  const previous = globalThis.fetch;
  const record = { is_online: true, last_active_at: '2026-10-25T12:00:00Z' };
  const valid = {
    users: [account],
    total: 1,
    page: 1,
    page_size: 20,
    presence: { [account.id]: record },
  };
  try {
    globalThis.fetch = async () =>
      json({ ...valid, presence: { ...valid.presence, secret: { token: 'private' } } });
    assert.deepEqual((await listAccounts()).presence, valid.presence);
    for (const invalid of [
      null,
      {},
      { ...record, is_online: 'yes' },
      { ...record, last_active_at: 'invalid' },
      { ...record, last_active_at: '2026-10-25T12:00:00' },
    ]) {
      globalThis.fetch = async () => json({ ...valid, presence: { [account.id]: invalid } });
      await assert.rejects(listAccounts(), AdminApiError);
    }
  } finally {
    globalThis.fetch = previous;
  }
});

test('admin create sends only recipient fields with current cookie and CSRF and returns no session', async () => {
  const { createAccount } = await api();
  const previous = globalThis.fetch;
  try {
    globalThis.fetch = async (url, init) => {
      assert.equal(url, '/admin/users');
      assert.equal(init.method, 'POST');
      assert.equal(init.credentials, 'same-origin');
      assert.equal(init.headers['X-CSRF-Token'], 'actor-csrf');
      assert.deepEqual(JSON.parse(init.body), {
        display_name: 'An',
        email: 'an@example.test',
        password: ' password12345 ',
        system_role: 'admin',
      });
      return json({ user: { ...account, password_hash: 'private' }, csrf_token: 'recipient' }, 201);
    };
    assert.deepEqual(await createAccount({ ...input, actor_id: 'forged' }, 'actor-csrf'), account);
  } finally {
    globalThis.fetch = previous;
  }
});

test('lookup encodes exact email, does not cache and rejects multiple or malformed accounts', async () => {
  const { lookupAccount, AdminApiError } = await api();
  const previous = globalThis.fetch;
  try {
    globalThis.fetch = async (url, init) => {
      assert.equal(url, '/admin/users?email=a%2Bb%40example.test');
      assert.equal(init.cache, 'no-store');
      return json({ users: [] });
    };
    assert.equal(await lookupAccount(' A+B@example.test '), null);
    for (const users of [
      [account, account],
      [{ ...account, system_role: 'owner' }],
      [{ ...account, is_active: 'true' }],
      { ...account, created_at: 'not-a-date' },
      Object.fromEntries(Object.entries(account).filter(([key]) => key !== 'created_at')),
      null,
    ]) {
      globalThis.fetch = async () => json({ users });
      await assert.rejects(lookupAccount('an@example.test'), AdminApiError);
    }
  } finally {
    globalThis.fetch = previous;
  }
});

test('update sends only changed identity/role fields and GET reads the exact account ID', async () => {
  const { updateAccount, getAccount } = await api();
  assert.equal(typeof updateAccount, 'function', 'Admin identity update client must exist');
  assert.equal(typeof getAccount, 'function', 'Admin account-by-ID client must exist');
  const previous = globalThis.fetch;
  try {
    globalThis.fetch = async (url, init) => {
      assert.equal(url, '/admin/users/target%2Fid');
      assert.equal(init.method, 'PATCH');
      assert.equal(init.credentials, 'same-origin');
      assert.equal(init.cache, 'no-store');
      assert.equal(init.headers['X-CSRF-Token'], 'actor-csrf');
      assert.deepEqual(JSON.parse(init.body), {
        display_name: 'Renamed',
        email: 'new@example.test',
        system_role: 'user',
        password: '  new-password-123  ',
      });
      return json({
        user: { ...account, id: 'target/id', display_name: 'Renamed', email: 'new@example.test' },
      });
    };
    assert.deepEqual(
      await updateAccount(
        'target/id',
        {
          display_name: ' Renamed ',
          email: ' NEW@example.test ',
          system_role: 'user',
          password: '  new-password-123  ',
        },
        'actor-csrf',
      ),
      { ...account, id: 'target/id', display_name: 'Renamed', email: 'new@example.test' },
    );
    globalThis.fetch = async (url, init) => {
      assert.equal(url, '/admin/users/target%2Fid');
      assert.equal(init.method, undefined);
      return json({ user: { ...account, id: 'target/id' } });
    };
    assert.deepEqual(await getAccount('target/id'), { ...account, id: 'target/id' });
  } finally {
    globalThis.fetch = previous;
  }
});

test('admin errors retain only safe codes and allowlisted field messages', async () => {
  const { createAccount } = await api();
  const previous = globalThis.fetch;
  try {
    for (const [status, code] of [
      [401, 'authentication_required'],
      [403, 'admin_required'],
      [403, 'csrf_invalid'],
      [403, 'origin_not_allowed'],
      [409, 'email_taken'],
      [409, 'last_active_admin'],
      [422, 'validation_error'],
      [500, 'account_creation_failed'],
    ]) {
      globalThis.fetch = async () =>
        json(
          {
            detail: {
              code,
              password: 'private',
              fields: {
                email: 'email_taken',
                system_role: 'invalid_role',
                password: 'private',
                extra: 'required',
              },
            },
          },
          status,
        );
      await assert.rejects(createAccount(input, 'csrf'), (error) => {
        assert.equal(error.code, code);
        assert.equal(error.status, status);
        assert.equal(JSON.stringify(error).includes('private'), false);
        assert.equal(error.fieldErrors.extra, undefined);
        assert.equal(error.fieldErrors.password, undefined);
        if (status === 422) assert.equal(error.fieldErrors.system_role.key, 'auth.errors.invalid');
        return true;
      });
    }
  } finally {
    globalThis.fetch = previous;
  }
});

test('unrecognized failures and invalid success bodies remain uncertain and POST is never retried', async () => {
  const { createAccount } = await api();
  const previous = globalThis.fetch;
  try {
    for (const response of [
      () => {
        throw new Error('private');
      },
      () => json({ detail: { code: 'private' } }, 502),
      () => json({ user: { ...account, id: null } }, 201),
      () => new Response('bad', { status: 500 }),
    ]) {
      let calls = 0;
      globalThis.fetch = async () => {
        calls++;
        return response();
      };
      await assert.rejects(createAccount(input, 'csrf'), (error) => error.code === 'unknown');
      assert.equal(calls, 1);
    }
  } finally {
    globalThis.fetch = previous;
  }
});

test('activity client sends only the desired state with CSRF', async () => {
  const { setAccountActivity } = await api();
  assert.equal(typeof setAccountActivity, 'function');
  const previous = globalThis.fetch;
  try {
    globalThis.fetch = async (url, init) => {
      assert.equal(url, '/admin/users/a%2Fb/activity');
      assert.equal(init.method, 'PATCH');
      assert.equal(init.headers['X-CSRF-Token'], 'csrf');
      assert.deepEqual(JSON.parse(init.body), { is_active: false });
      return json({ user: { ...account, id: 'a/b', is_active: false } });
    };
    assert.equal((await setAccountActivity('a/b', false, 'csrf')).is_active, false);
  } finally {
    globalThis.fetch = previous;
  }
});

test('list combines role and disabled filters without dropping false', async () => {
  const { listAccounts } = await api();
  const previous = globalThis.fetch;
  try {
    globalThis.fetch = async (url) => {
      const query = new URL(url, 'https://test.local').searchParams;
      assert.equal(query.get('system_role'), 'user');
      assert.equal(query.get('is_active'), 'false');
      return json({ users: [], total: 0, page: 1, page_size: 20 });
    };
    await listAccounts({ system_role: 'user', is_active: false });
  } finally {
    globalThis.fetch = previous;
  }
});
