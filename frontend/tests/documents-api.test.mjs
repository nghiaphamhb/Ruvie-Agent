import assert from 'node:assert/strict';
import test from 'node:test';

async function loadClient() {
  const client = await import('../src/lib/features/documents/documents-api.ts').catch(() => null);
  assert.ok(client, 'documents API client must exist');
  return client;
}

async function withFetch(fake, run) {
  const original = globalThis.fetch;
  globalThis.fetch = fake;
  try { return await run(); } finally { globalThis.fetch = original; }
}

test('lists projects using the session cookie', async () => {
  const { listProjects } = await loadClient();
  const payload = { items: [{ id: 'p1', code: 'alpha', name: 'Alpha' }] };
  await withFetch(async (url, options) => {
    assert.equal(url, '/projects');
    assert.equal(options.credentials, 'same-origin');
    return Response.json(payload);
  }, async () => assert.deepEqual(await listProjects(), payload.items));
});

test('uploads multipart data with CSRF and lets the browser set its boundary', async () => {
  const { uploadDocument } = await loadClient();
  const file = new File(['guide'], 'guide.txt', { type: 'text/plain' });
  await withFetch(async (url, options) => {
    assert.equal(url, '/documents/upload');
    assert.equal(options.method, 'POST');
    assert.equal(options.credentials, 'same-origin');
    assert.equal(options.headers['X-CSRF-Token'], 'csrf');
    assert.equal(options.headers['Content-Type'], undefined);
    assert.ok(options.body instanceof FormData);
    assert.equal(options.body.get('project_id'), 'p1');
    assert.equal(options.body.get('file').name, 'guide.txt');
    return Response.json({ document_id: 'd1', revision_id: 'r1', job_id: 'j1', status: 'pending' }, { status: 202 });
  }, async () => {
    const result = await uploadDocument('csrf', { project_id: 'p1', title: 'Guide', software: 'Revit', software_version: '2026', file });
    assert.equal(result.status, 'pending');
  });
});

test('fetches the status for one revision', async () => {
  const { getRevisionStatus } = await loadClient();
  await withFetch(async (url, options) => {
    assert.equal(url, '/documents/revisions/r1/status');
    assert.equal(options.credentials, 'same-origin');
    return Response.json({ revision_id: 'r1', status: 'ready', error_code: null });
  }, async () => assert.equal((await getRevisionStatus('r1')).status, 'ready'));
});
