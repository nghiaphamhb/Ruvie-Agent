import assert from 'node:assert/strict';
import test from 'node:test';
const flush = () => new Promise((resolve) => setImmediate(resolve));

async function fixture(t, fetch) {
  const original = {
    window: globalThis.window,
    document: globalThis.document,
    fetch: globalThis.fetch,
  };
  const window = new EventTarget();
  const document = new EventTarget();
  document.hidden = false;
  globalThis.window = window;
  globalThis.document = document;
  globalThis.fetch = fetch;
  t.mock.timers.enable({ apis: ['setTimeout'] });
  const module = await import('../src/lib/features/auth/presence.ts');
  let expired = 0;
  const owner = module.startPresence('csrf', () => expired++);
  t.after(() => {
    owner.dispose();
    Object.assign(globalThis, original);
  });
  await flush();
  return { owner, document, window, expired: () => expired };
}

test('heartbeat uses cookie/CSRF and visible/background intervals, then stops on disposal', async (t) => {
  const calls = [];
  const f = await fixture(t, async (path, init) => {
    calls.push({ path, init });
    return new Response(null, { status: 204 });
  });
  assert.equal(calls.length, 1);
  assert.equal(calls[0].path, '/auth/presence');
  assert.equal(calls[0].init.headers['X-CSRF-Token'], 'csrf');
  assert.equal(calls[0].init.credentials, 'same-origin');
  assert.equal(calls[0].init.body, undefined);
  t.mock.timers.tick(30000);
  await flush();
  assert.equal(calls.length, 2);
  f.document.hidden = true;
  f.document.dispatchEvent(new Event('visibilitychange'));
  t.mock.timers.tick(30000);
  await flush();
  assert.equal(calls.length, 2);
  t.mock.timers.tick(30000);
  await flush();
  assert.equal(calls.length, 3);
  f.document.hidden = false;
  f.document.dispatchEvent(new Event('visibilitychange'));
  await flush();
  assert.equal(calls.length, 4);
  f.owner.dispose();
  f.window.dispatchEvent(new Event('online'));
  t.mock.timers.tick(120000);
  await flush();
  assert.equal(calls.length, 4);
});

test('temporary failure retries; a current 401 expires once and stops heartbeats', async (t) => {
  let calls = 0;
  const f = await fixture(t, async () => {
    calls++;
    return new Response(null, { status: calls === 1 ? 503 : 401 });
  });
  assert.equal(f.expired(), 0);
  f.window.dispatchEvent(new Event('online'));
  await flush();
  assert.equal(f.expired(), 1);
  t.mock.timers.tick(120000);
  await flush();
  assert.equal(calls, 2);
});

test('one request at a time; disposal aborts and ignores an old account response', async (t) => {
  let resolve;
  let signal;
  let calls = 0;
  const f = await fixture(t, async (_path, init) => {
    calls++;
    signal = init.signal;
    return new Promise((done) => {
      resolve = done;
    });
  });
  f.window.dispatchEvent(new Event('online'));
  assert.equal(calls, 1);
  f.owner.dispose();
  assert.equal(signal.aborted, true);
  resolve(new Response(null, { status: 401 }));
  await flush();
  assert.equal(f.expired(), 0);
});

test('a hung heartbeat times out and retries without overlapping requests', async (t) => {
  let calls = 0;
  const f = await fixture(t, async (_path, init) => {
    calls++;
    if (calls > 1) return new Response(null, { status: 204 });
    return new Promise((_resolve, reject) =>
      init.signal.addEventListener('abort', () => reject(new Error('aborted'))),
    );
  });
  t.mock.timers.tick(10000);
  await flush();
  assert.equal(calls, 1);
  t.mock.timers.tick(30000);
  await flush();
  assert.equal(calls, 2);
  assert.equal(f.expired(), 0);
});
