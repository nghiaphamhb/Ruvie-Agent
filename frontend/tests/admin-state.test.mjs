import assert from 'node:assert/strict';
import test from 'node:test';
import { loadState, json } from './state-loader.mjs';

const input = {
  display_name: 'An',
  email: ' AN@example.test ',
  password: 'password12345',
  system_role: 'user',
};
const account = {
  id: 'new',
  display_name: 'An',
  email: 'an@example.test',
  system_role: 'user',
  is_active: true,
  created_at: '2026-10-23T12:00:00Z',
};
const listedAccount = {
  id: 'target',
  display_name: 'Before',
  email: 'before@example.test',
  system_role: 'user',
  is_active: true,
  created_at: '2026-10-23T12:00:00Z',
};
async function owner(callbacks = {}) {
  const module = await loadState('../src/lib/features/admin/admin-state.svelte.ts');
  assert.ok(module, 'Admin state owner must exist');
  return module.createAdminState({
    csrfToken: 'actor',
    onexpired() {
      assert.fail('unexpected expiry');
    },
    onforbidden() {
      assert.fail('unexpected demotion');
    },
    ...callbacks,
  });
}

test('background presence failure retains rows and recovers without exposing a list error', async () => {
  const state = await owner();
  const previous = globalThis.fetch;
  const presence = { [account.id]: { is_online: true, last_active_at: '2026-10-25T12:00:00Z' } };
  try {
    globalThis.fetch = async () =>
      json({ users: [account], total: 1, page: 1, page_size: 20, presence });
    await state.loadUsers();
    globalThis.fetch = async () => {
      throw Error('unavailable');
    };
    await state.loadUsers(undefined, true);
    assert.deepEqual(state.users, [account]);
    assert.deepEqual(state.presence, presence);
    assert.equal(state.presenceStale, true);
    assert.equal(state.listError, null);
    globalThis.fetch = async () =>
      json({ users: [account], total: 1, page: 1, page_size: 20, presence });
    await state.loadUsers(undefined, true);
    assert.equal(state.presenceStale, false);
  } finally {
    state.dispose();
    globalThis.fetch = previous;
  }
});

test('create locks duplicate submits/close and stores only recipient metadata after success', async () => {
  const state = await owner();
  const previous = globalThis.fetch;
  let resolve;
  let calls = 0;
  try {
    globalThis.fetch = () => {
      calls++;
      return new Promise((done) => {
        resolve = done;
      });
    };
    state.open();
    const pending = state.create(input);
    assert.equal(state.busy, true);
    state.close();
    assert.equal(state.formOpen, true);
    await state.create(input);
    assert.equal(calls, 1);
    resolve(json({ user: account }, 201));
    assert.equal(await pending, true);
    assert.equal(state.formOpen, false);
    assert.deepEqual(state.created, account);
    assert.equal(JSON.stringify(state).includes('password12345'), false);
    state.open();
    assert.equal(state.created, null);
  } finally {
    state.dispose();
    globalThis.fetch = previous;
  }
});

test('uncertain create blocks resubmission until exact-email lookup; found account is not creation success', async () => {
  const state = await owner();
  const previous = globalThis.fetch;
  const paths = [];
  try {
    state.open();
    globalThis.fetch = async (path) => {
      paths.push(path);
      throw new Error('lost');
    };
    await state.create(input);
    assert.equal(state.uncertain, true);
    await state.create(input);
    assert.equal(paths.length, 1);
    globalThis.fetch = async (path) => {
      paths.push(path);
      return json({ users: [account] });
    };
    await state.lookup();
    assert.equal(paths[1], '/admin/users?email=an%40example.test');
    assert.deepEqual(state.found, account);
    assert.equal(state.created, null);
    await state.create(input);
    assert.equal(paths.length, 2);
    globalThis.fetch = async () => json({ users: [] });
    await state.lookup();
    assert.equal(state.uncertain, false);
    assert.equal(state.lookupDone, true);
  } finally {
    state.dispose();
    globalThis.fetch = previous;
  }
});

test('lookup failure keeps uncertainty; known rejection permits correction', async () => {
  const state = await owner();
  const previous = globalThis.fetch;
  try {
    state.open();
    globalThis.fetch = async () => {
      throw new Error('lost');
    };
    await state.create(input);
    globalThis.fetch = async () => json({ detail: { code: 'account_lookup_unavailable' } }, 503);
    await state.lookup();
    assert.equal(state.uncertain, true);
    state.close();
    state.open();
    globalThis.fetch = async () => json({ detail: { code: 'email_taken' } }, 409);
    await state.create(input);
    assert.equal(state.uncertain, false);
    assert.equal(state.formOpen, true);
    assert.equal(state.fieldErrors.email.key, 'auth.errors.emailTaken');
  } finally {
    state.dispose();
    globalThis.fetch = previous;
  }
});

test('401 clears account data; only admin_required invokes lost-permission callback', async () => {
  let expired = 0,
    forbidden = 0;
  const state = await owner({
    onexpired() {
      expired++;
    },
    onforbidden() {
      forbidden++;
    },
  });
  const previous = globalThis.fetch;
  try {
    for (const [status, code] of [
      [403, 'csrf_invalid'],
      [403, 'origin_not_allowed'],
      [403, 'admin_required'],
      [401, 'authentication_required'],
    ]) {
      state.open();
      globalThis.fetch = async () => json({ detail: { code } }, status);
      await state.create(input);
      if (code === 'csrf_invalid' || code === 'origin_not_allowed') {
        assert.equal(expired, 0);
        assert.equal(forbidden, 0);
      }
    }
    assert.equal(expired, 1);
    assert.equal(forbidden, 1);
    assert.equal(state.formOpen, false);
    assert.equal(state.created, null);
    assert.equal(state.sentEmail, '');
  } finally {
    state.dispose();
    globalThis.fetch = previous;
  }
});

test('save updates a single list row and reconciles a lost PATCH response by immutable ID', async () => {
  const state = await owner();
  const previous = globalThis.fetch;
  const paths = [];
  const updated = { ...listedAccount, display_name: 'After', email: 'after@example.test' };
  let serverAccount = listedAccount;
  try {
    globalThis.fetch = async (path) => {
      paths.push(path);
      if (path.startsWith('/admin/users/list'))
        return json({ users: [serverAccount], total: 1, page: 1, page_size: 20 });
      if (path === '/admin/users/target' && paths.filter((item) => item === path).length === 1)
        throw new Error('response lost after server commit');
      if (path === '/admin/users/target') {
        serverAccount = updated;
        return json({ user: updated });
      }
      assert.fail(`Unexpected request: ${path}`);
    };
    await state.loadUsers();
    assert.deepEqual(
      await state.saveUser(listedAccount, {
        display_name: 'After',
        email: 'AFTER@example.test',
      }),
      updated,
    );
    await new Promise((resolve) => setTimeout(resolve, 0));
    assert.deepEqual(paths, [
      '/admin/users/list?q=&page=1&page_size=20',
      '/admin/users/target',
      '/admin/users/target',
      '/admin/users/list?q=&page=1&page_size=20',
    ]);
    assert.deepEqual(state.users, [updated]);
    assert.equal(state.editError, null);
  } finally {
    state.dispose();
    globalThis.fetch = previous;
  }
});

test('failed reconciliation keeps the list unchanged and does not resend PATCH', async () => {
  const state = await owner();
  const previous = globalThis.fetch;
  const paths = [];
  try {
    globalThis.fetch = async (path) => {
      paths.push(path);
      if (path.startsWith('/admin/users/list'))
        return json({ users: [listedAccount], total: 1, page: 1, page_size: 20 });
      if (path === '/admin/users/target' && paths.filter((item) => item === path).length === 1)
        throw new Error('response lost');
      if (path === '/admin/users/target') return json({ user: listedAccount });
      assert.fail(`Unexpected request: ${path}`);
    };
    await state.loadUsers();
    assert.equal(await state.saveUser(listedAccount, { display_name: 'After' }), null);
    assert.deepEqual(paths, [
      '/admin/users/list?q=&page=1&page_size=20',
      '/admin/users/target',
      '/admin/users/target',
    ]);
    assert.deepEqual(state.users, [listedAccount]);
    assert.equal(state.editError, 'account_update_unavailable');
  } finally {
    state.dispose();
    globalThis.fetch = previous;
  }
});

test('password update with a lost response checks only the actor session and never reads or retries account data', async () => {
  const state = await owner();
  const previous = globalThis.fetch;
  const paths = [];
  try {
    globalThis.fetch = async (path, init = {}) => {
      paths.push([path, init.method ?? 'GET']);
      if (path === '/admin/users/target') throw new Error('response lost after commit');
      if (path === '/auth/session') return json({ user: { id: 'actor' }, csrf_token: 'actor' });
      assert.fail(`Unexpected request: ${path}`);
    };
    assert.equal(await state.saveUser(listedAccount, { password: '  new-password-123  ' }), null);
    assert.deepEqual(paths, [
      ['/admin/users/target', 'PATCH'],
      ['/auth/session', 'GET'],
    ]);
    assert.equal(state.editError, 'account_update_unavailable');
  } finally {
    state.dispose();
    globalThis.fetch = previous;
  }
});

test('self password reset with a lost response expires the session when server confirms revocation', async () => {
  let expired = 0;
  const state = await owner({
    onexpired() {
      expired++;
    },
  });
  const previous = globalThis.fetch;
  const paths = [];
  try {
    globalThis.fetch = async (path) => {
      paths.push(path);
      if (path === '/admin/users/target') throw new Error('response lost after commit');
      if (path === '/auth/session')
        return json({ detail: { code: 'authentication_required' } }, 401);
      assert.fail(`Unexpected request: ${path}`);
    };
    assert.equal(await state.saveUser(listedAccount, { password: 'new-password-123' }), null);
    assert.deepEqual(paths, ['/admin/users/target', '/auth/session']);
    assert.equal(expired, 1);
    assert.equal(state.editError, null);
  } finally {
    state.dispose();
    globalThis.fetch = previous;
  }
});

test('role changes are saved and a lost self-demotion response exits admin without logout', async () => {
  const state = await owner();
  const previous = globalThis.fetch;
  const updated = { ...listedAccount, system_role: 'admin' };
  let demoted = 0;
  try {
    globalThis.fetch = async (path, init) => {
      if (path === '/admin/users/target' && init.method === 'PATCH') {
        assert.deepEqual(JSON.parse(init.body), { system_role: 'admin' });
        return json({ user: updated });
      }
      if (path.startsWith('/admin/users/list'))
        return json({ users: [updated], total: 1, page: 1, page_size: 20 });
      assert.fail(`Unexpected request: ${path}`);
    };
    await state.loadUsers();
    assert.deepEqual(await state.saveUser(listedAccount, { system_role: 'admin' }), updated);
    await new Promise((resolve) => setTimeout(resolve, 0));
    assert.deepEqual(state.users, [updated]);

    globalThis.fetch = async (path, init) => {
      if (path === '/admin/users/target' && init.method === 'PATCH')
        throw new Error('demotion committed but response was lost');
      if (path === '/admin/users/target') return json({ detail: { code: 'admin_required' } }, 403);
      assert.fail(`Unexpected request: ${path}`);
    };
    const adminState = await owner({
      onforbidden() {
        demoted++;
      },
    });
    await adminState.saveUser({ ...updated, id: 'target' }, { system_role: 'user' });
    assert.equal(demoted, 1);
    adminState.dispose();
  } finally {
    state.dispose();
    globalThis.fetch = previous;
  }
});

test('dispose ignores late success and late 401 from a previous account', async () => {
  const previous = globalThis.fetch;
  try {
    for (const response of [json({ user: account }, 201), json({}, 401)]) {
      const state = await owner();
      let resolve;
      globalThis.fetch = () =>
        new Promise((done) => {
          resolve = done;
        });
      state.open();
      const pending = state.create(input);
      state.dispose();
      resolve(response);
      await pending;
      assert.equal(state.created, null);
      assert.equal(state.formOpen, false);
      assert.equal(state.busy, false);
    }
  } finally {
    globalThis.fetch = previous;
  }
});

test('confirmed rollback allows a deliberate new POST; lookup not-found also unlocks a deliberate retry', async () => {
  const state = await owner();
  const previous = globalThis.fetch;
  let calls = 0;
  try {
    state.open();
    globalThis.fetch = async () => {
      calls++;
      return json({ detail: { code: 'account_creation_failed' } }, 500);
    };
    await state.create(input);
    assert.equal(state.uncertain, false);
    assert.equal(state.created, null);
    globalThis.fetch = async () => {
      calls++;
      throw new Error('lost');
    };
    await state.create(input);
    assert.equal(calls, 2);
    globalThis.fetch = async () => json({ users: [] });
    await state.lookup();
    globalThis.fetch = async () => {
      calls++;
      return json({ user: account }, 201);
    };
    assert.equal(calls, 2);
    assert.equal(await state.create(input), true);
    assert.equal(calls, 4);
  } finally {
    state.dispose();
    globalThis.fetch = previous;
  }
});

test('disposing during lookup clears metadata and ignores a late account match', async () => {
  const state = await owner();
  const previous = globalThis.fetch;
  try {
    state.open();
    globalThis.fetch = async () => {
      throw new Error('lost');
    };
    await state.create(input);
    let resolve;
    globalThis.fetch = () =>
      new Promise((done) => {
        resolve = done;
      });
    const pending = state.lookup();
    state.dispose();
    resolve(json({ users: [account] }));
    await pending;
    assert.equal(state.found, null);
    assert.equal(state.sentEmail, '');
    assert.equal(state.lookupDone, false);
  } finally {
    state.dispose();
    globalThis.fetch = previous;
  }
});

test('lookup after a known email conflict does not turn the rejection into an unknown outcome', async () => {
  const state = await owner();
  const previous = globalThis.fetch;
  let posts = 0;
  try {
    state.open();
    globalThis.fetch = async (_path, init) => {
      if (init.method === 'POST') {
        posts++;
        return json({ detail: { code: 'email_taken' } }, 409);
      }
      return json({ users: [account] });
    };
    await state.create(input);
    await state.lookup();
    assert.equal(state.uncertain, false);
    assert.deepEqual(state.found, account);
    await state.create(input);
    assert.equal(posts, 1);
  } finally {
    state.dispose();
    globalThis.fetch = previous;
  }
});

test('account list ignores an older response and keeps only the latest page', async () => {
  const state = await owner();
  const previous = globalThis.fetch;
  const pending = [];
  try {
    globalThis.fetch = () => new Promise((resolve) => pending.push(resolve));
    const oldRequest = state.loadUsers({ q: 'old', page: 1 });
    const newRequest = state.loadUsers({ q: 'new', page: 1 });
    pending[1](json({ users: [account], total: 1, page: 1, page_size: 20 }));
    await newRequest;
    pending[0](json({ users: [], total: 0, page: 1, page_size: 20 }));
    await oldRequest;
    assert.deepEqual(state.users, [account]);
    assert.equal(state.total, 1);
    assert.equal(state.listLoading, false);
    assert.equal(state.listError, null);
  } finally {
    state.dispose();
    globalThis.fetch = previous;
  }
});

test('account list reports safe errors and retries through the same page loader', async () => {
  const state = await owner();
  const previous = globalThis.fetch;
  let calls = 0;
  try {
    globalThis.fetch = async () => {
      calls++;
      return calls === 1
        ? json({ detail: { code: 'account_lookup_unavailable' } }, 503)
        : json({ users: [account], total: 1, page: 1, page_size: 20 });
    };
    await state.loadUsers({ q: '', page: 1 });
    assert.equal(state.listError, 'account_lookup_unavailable');
    await state.loadUsers({ q: '', page: 1 });
    assert.equal(state.listError, null);
    assert.deepEqual(state.users, [account]);
    assert.equal(calls, 2);
  } finally {
    state.dispose();
    globalThis.fetch = previous;
  }
});

test('activity mutation reconciles lost response without retrying the write', async () => {
  const state = await owner();
  const previous = globalThis.fetch;
  let patches = 0;
  try {
    globalThis.fetch = async (url, init = {}) => {
      if (init.method === 'PATCH') {
        patches++;
        throw Error('lost');
      }
      if (url === '/admin/users/target')
        return json({ user: { ...listedAccount, is_active: false } });
      return json({
        users: [{ ...listedAccount, is_active: false }],
        total: 1,
        page: 1,
        page_size: 20,
      });
    };
    const result = await state.changeActivity(listedAccount, false);
    assert.equal(result.status, 'observed');
    assert.equal(result.user.is_active, false);
    assert.equal(patches, 1);
  } finally {
    state.dispose();
    globalThis.fetch = previous;
  }
});

test('activity response after owner disposal cannot expire a new session', async () => {
  let expired = 0;
  const state = await owner({
    onexpired() {
      expired++;
    },
  });
  const previous = globalThis.fetch;
  let finish;
  try {
    globalThis.fetch = () =>
      new Promise((resolve) => {
        finish = resolve;
      });
    const pending = state.changeActivity(listedAccount, false);
    state.dispose();
    finish(json({ detail: { code: 'authentication_required' } }, 401));
    assert.equal((await pending).status, 'ignored');
    assert.equal(expired, 0);
  } finally {
    state.dispose();
    globalThis.fetch = previous;
  }
});

test('a list started during an uncertain activity write cannot clear uncertainty', async () => {
  const state = await owner();
  const previous = globalThis.fetch;
  let finishPatch, finishList;
  try {
    globalThis.fetch = (url, init = {}) => {
      if (init.method === 'PATCH')
        return new Promise((_, reject) => {
          finishPatch = reject;
        });
      if (url.startsWith('/admin/users/list'))
        return new Promise((resolve) => {
          finishList = resolve;
        });
      throw Error('lookup unavailable');
    };
    const operation = state.changeActivity(listedAccount, false);
    const staleList = state.loadUsers(undefined, true);
    finishPatch(Error('lost'));
    assert.equal((await operation).status, 'uncertain');
    finishList(json({ users: [listedAccount], total: 1, page: 1, page_size: 20 }));
    await staleList;
    assert.deepEqual(state.activityUncertainIds, ['target']);
  } finally {
    state.dispose();
    globalThis.fetch = previous;
  }
});

test('activity remains blocked after an uncertain response until a fresh account list is read', async () => {
  const state = await owner();
  const previous = globalThis.fetch;
  let writes = 0;
  try {
    globalThis.fetch = async (url, init = {}) => {
      if (init.method === 'PATCH') {
        writes++;
        throw Error('network');
      }
      if (url === '/admin/users/target') throw Error('unavailable');
      return json({ users: [listedAccount], total: 1, page: 1, page_size: 20 });
    };
    assert.equal((await state.changeActivity(listedAccount, false)).status, 'uncertain');
    assert.deepEqual(state.activityUncertainIds, ['target']);
    assert.equal((await state.changeActivity(listedAccount, false)).status, 'ignored');
    assert.equal(writes, 1);
    await state.loadUsers();
    assert.deepEqual(state.activityUncertainIds, []);
  } finally {
    state.dispose();
    globalThis.fetch = previous;
  }
});

test('a rejected activity write does not leave a superseded list request loading forever', async () => {
  const state = await owner();
  const previous = globalThis.fetch;
  let finishList;
  try {
    globalThis.fetch = (url, init = {}) => {
      if (init.method === 'PATCH')
        return Promise.resolve(json({ detail: { code: 'last_active_admin' } }, 409));
      if (url.startsWith('/admin/users/list'))
        return new Promise((resolve) => {
          finishList = resolve;
        });
      throw Error('unexpected request');
    };
    const list = state.loadUsers();
    assert.equal(state.listLoading, true);
    assert.equal((await state.changeActivity(listedAccount, false)).status, 'rejected');
    finishList(json({ users: [listedAccount], total: 1, page: 1, page_size: 20 }));
    await list;
    assert.equal(state.listLoading, false);
  } finally {
    state.dispose();
    globalThis.fetch = previous;
  }
});

test('uncertainty on two accounts remains tracked independently', async () => {
  const state = await owner();
  const previous = globalThis.fetch;
  const other = { ...listedAccount, id: 'other' };
  let writes = 0;
  try {
    globalThis.fetch = async (_url, init = {}) => {
      if (init.method === 'PATCH') writes++;
      throw Error('network');
    };
    assert.equal((await state.changeActivity(listedAccount, false)).status, 'uncertain');
    assert.equal((await state.changeActivity(other, false)).status, 'uncertain');
    assert.equal((await state.changeActivity(listedAccount, false)).status, 'ignored');
    assert.equal((await state.changeActivity(other, false)).status, 'ignored');
    assert.equal(writes, 2);
  } finally {
    state.dispose();
    globalThis.fetch = previous;
  }
});

test('activity permission failures go to the right owner and never retry', async () => {
  const previous = globalThis.fetch;
  try {
    for (const [status, code, result, expired, forbidden] of [
      [401, 'authentication_required', 'ignored', 1, 0],
      [403, 'admin_required', 'ignored', 0, 1],
      [403, 'csrf_invalid', 'rejected', 0, 0],
      [403, 'origin_not_allowed', 'rejected', 0, 0],
    ]) {
      let expiredCount = 0,
        forbiddenCount = 0,
        calls = 0;
      const state = await owner({
        onexpired() {
          expiredCount++;
        },
        onforbidden() {
          forbiddenCount++;
        },
      });
      try {
        globalThis.fetch = async () => {
          calls++;
          return json({ detail: { code } }, status);
        };
        assert.equal((await state.changeActivity(listedAccount, false)).status, result);
        assert.equal(expiredCount, expired);
        assert.equal(forbiddenCount, forbidden);
        assert.equal(calls, 1);
      } finally {
        state.dispose();
      }
    }
  } finally {
    globalThis.fetch = previous;
  }
});
