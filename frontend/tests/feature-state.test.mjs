import assert from 'node:assert/strict';
import test from 'node:test';
import { loadState, catalog, citation, json, frame } from './state-loader.mjs';

test('Stop retains partial text and retry uses the original question/model without duplicate turns', async () => {
  const module = await loadState('../src/lib/features/chat/chat-state.svelte.ts');
  assert.ok(module, 'Chat feature owner must exist');
  const originalFetch = globalThis.fetch;
  const requests = [];
  try {
    globalThis.fetch = async (path, init) => {
      let controller;
      const stream = new ReadableStream({
        start(c) {
          controller = c;
        },
      });
      requests.push({ body: JSON.parse(init.body), controller });
      init.signal.addEventListener('abort', () => controller.error(new Error('aborted')), {
        once: true,
      });
      return new Response(stream, { headers: { 'Content-Type': 'text/event-stream' } });
    };
    const chat = module.createChatState({
      onexpired() {
        assert.fail('unexpected logout');
      },
      getCatalog: () => catalog,
      isLocked: () => false,
      onModelUnavailable() {},
    });
    chat.draft = 'Original question';
    const first = chat.submit();
    await new Promise((resolve) => setTimeout(resolve, 0));
    requests[0].controller.enqueue(frame('delta', { text: 'Partial' }));
    requests[0].controller.enqueue(frame('citations', { citations: [citation] }));
    await new Promise((resolve) => setTimeout(resolve, 0));
    chat.stop();
    assert.equal(chat.busy, false);
    assert.equal(chat.turns[0].status, 'stopped');
    assert.equal(chat.turns[0].answer, 'Partial');
    assert.deepEqual(chat.turns[0].citations, []);
    await first;
    chat.draft = 'Unsent draft';
    const retry = chat.retry(chat.turns[0].id);
    await new Promise((resolve) => setTimeout(resolve, 0));
    assert.deepEqual(requests[1].body, { message: 'Original question', model_id: 'one' });
    assert.equal(chat.turns.length, 1);
    assert.equal(chat.draft, 'Unsent draft');
    requests[1].controller.enqueue(frame('delta', { text: 'Replacement' }));
    requests[1].controller.enqueue(frame('completed', {}));
    await retry;
    assert.equal(chat.turns[0].answer, 'Replacement');
    assert.equal(chat.turns[0].status, 'completed');
    chat.dispose();
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('documents search keeps the newest query and disposal ignores an old account 401', async () => {
  const module = await loadState('../src/lib/features/documents/documents-state.svelte.ts');
  assert.ok(module, 'Documents feature owner must exist');
  const originalFetch = globalThis.fetch;
  const pending = [];
  let expired = 0;
  try {
    globalThis.fetch = (path, init) =>
      new Promise((resolve) => pending.push({ path, init, resolve }));
    const docs = module.createDocumentsState({
      csrfToken: 'csrf',
      onexpired() {
        expired++;
      },
    });
    docs.query = 'first';
    const first = docs.search();
    docs.query = 'second';
    const second = docs.search();
    assert.equal(pending.length, 2);
    assert.deepEqual(JSON.parse(pending[1].init.body), { query: 'second', limit: 10 });
    pending[1].resolve(
      json([{ chunk_id: 'ch', document_id: 'd', text: 'Second result', citation }]),
    );
    await second;
    assert.equal(docs.results[0].text, 'Second result');
    pending[0].resolve(json([], 401));
    await first;
    assert.equal(expired, 0);
    assert.equal(docs.results[0].text, 'Second result');
    docs.query = 'third';
    const last = docs.search();
    docs.dispose();
    pending[2].resolve(json([], 401));
    await last;
    assert.equal(expired, 0);
    assert.equal(docs.results.length, 0);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('LLM initialization is idempotent and failed preference change preserves the confirmed model', async () => {
  const module = await loadState('../src/lib/features/llm/llm-state.svelte.ts');
  assert.ok(module, 'LLM feature owner must exist');
  const originalFetch = globalThis.fetch;
  const calls = [];
  try {
    globalThis.fetch = async (path, init = {}) => {
      calls.push({ path, init });
      if (init.method === 'PATCH') return json({ detail: 'secret provider detail' }, 503);
      return path === '/models'
        ? json(catalog)
        : json({
            configured: true,
            configuration_version: 1,
            selected_model_id: 'one',
          });
    };
    const llm = module.createLlmState({
      csrfToken: 'csrf',
      onexpired() {
        assert.fail('unexpected logout');
      },
      isLocked: () => false,
    });
    await Promise.all([llm.initialize(), llm.initialize()]);
    assert.equal(calls.filter((c) => c.path === '/models').length, 1);
    await llm.chooseModel('two');
    assert.equal(llm.catalog.selected_model_id, 'one');
    assert.ok(llm.modelError);
    assert.ok(!JSON.stringify(llm.modelError).includes('secret provider detail'));
    llm.dispose();
    assert.equal(llm.apiKey, undefined);
    assert.equal(llm.catalog, null);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('retrieve rejects malformed source payload without exposing raw content', async () => {
  const api = await import('../src/lib/features/documents/documents-api.ts');
  assert.equal(typeof api.retrieveDocuments, 'function', 'Validated retrieval client must exist');
  const originalFetch = globalThis.fetch;
  try {
    globalThis.fetch = async () => json([{ text: '<secret>', citation: { title: 'bad' } }]);
    await assert.rejects(
      api.retrieveDocuments('query'),
      (e) => e instanceof api.DocumentsApiError && !e.message.includes('secret'),
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('editing a query while its response is pending does not display results for the old text', async () => {
  const { createDocumentsState } = await loadState(
    '../src/lib/features/documents/documents-state.svelte.ts',
  );
  const originalFetch = globalThis.fetch;
  let resolveRequest;
  try {
    globalThis.fetch = () => new Promise((resolve) => (resolveRequest = resolve));
    const docs = createDocumentsState({
      csrfToken: 'csrf',
      onexpired() {
        assert.fail('unexpected logout');
      },
    });
    docs.query = 'old';
    const pending = docs.search();
    docs.query = 'edited';
    resolveRequest(json([{ chunk_id: 'ch', document_id: 'd', text: 'Old text', citation }]));
    await pending;
    assert.deepEqual(docs.results, []);
    assert.equal(docs.query, 'edited');
    docs.dispose();
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('submitting without a valid model reports configuration error and retains the draft without a request', async () => {
  const { createChatState } = await loadState('../src/lib/features/chat/chat-state.svelte.ts');
  const originalFetch = globalThis.fetch;
  let notices = 0;
  try {
    globalThis.fetch = () => assert.fail('Missing model must not send an API request');
    for (const value of [
      null,
      { ...catalog, selection_required: true },
      { ...catalog, selected_model_id: null },
      { ...catalog, selected_model_id: 'missing' },
    ]) {
      const chat = createChatState({
        getCatalog: () => value,
        isLocked: () => false,
        onexpired() {},
        onModelUnavailable() {},
        onMissingModel() {
          notices++;
        },
      });
      chat.draft = 'Software fails to start';
      await chat.submit();
      assert.equal(chat.draft, 'Software fails to start');
      assert.equal(chat.turns.length, 0);
      assert.equal(chat.busy, false);
      chat.dispose();
    }
    assert.equal(notices, 4);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
