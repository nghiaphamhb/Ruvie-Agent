import assert from 'node:assert/strict';
import test from 'node:test';

async function loadClient() {
  const client = await import('../src/lib/chat-api.ts').catch(() => null);
  assert.ok(client, 'chat API client must exist');
  return client;
}

function sseResponse(chunks) {
  const encoder = new TextEncoder();
  const bytes = encoder.encode(chunks);
  const accent = bytes.indexOf(0xc3);
  const pieces = [bytes.slice(0, accent + 1), bytes.slice(accent + 1, accent + 7), bytes.slice(accent + 7)];
  return new Response(new ReadableStream({
    start(controller) {
      for (const piece of pieces) controller.enqueue(piece);
      controller.close();
    }
  }), { headers: { 'Content-Type': 'text/event-stream' } });
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

test('POST sends only message and reads split UTF-8 SSE events in order', async () => {
  const { streamChat } = await loadClient();
  const events = [];
  const citation = {
    citation_id: 'doc:rev:chunk', document_id: 'doc', revision_id: 'rev', chunk_id: 'chunk',
    ordinal: 0, start_offset: 12, end_offset: 34, title: 'Hướng dẫn', source_hash: 'a'.repeat(64),
    software: 'Revit', software_version: '2026'
  };
  const frames = [
    'event: delta\ndata: {"text":"Xin chào"}\n\n',
    `event: citations\ndata: ${JSON.stringify({ citations: [citation] })}\n\n`,
    'event: completed\ndata: {}\n\n'
  ].join('');

  await withFetch(async (url, options) => {
    assert.equal(url, '/chat');
    assert.equal(options.method, 'POST');
    assert.deepEqual(JSON.parse(options.body), { message: 'Cách cài plugin?' });
    assert.equal(options.headers['Content-Type'], 'application/json');
    return sseResponse(frames);
  }, () => streamChat('Cách cài plugin?', (event) => events.push(event)));

  assert.deepEqual(events, [
    { type: 'delta', text: 'Xin chào' },
    { type: 'citations', citations: [citation] },
    { type: 'completed' }
  ]);
});

test('HTTP 401 becomes an authentication error', async () => {
  const { streamChat } = await loadClient();
  await withFetch(async () => new Response('{"detail":"authentication required"}', { status: 401 }), async () => {
    await assert.rejects(streamChat('Question', () => {}), (error) => error.code === 'auth_required');
  });
});

test('SSE provider error after a delta stops without completion', async () => {
  const { streamChat } = await loadClient();
  const events = [];
  const frames = 'event: delta\ndata: {"text":"Partial"}\n\nevent: error\ndata: {"code":"provider_unavailable","message":"secret upstream"}\n\n';
  await withFetch(async () => sseResponse(frames), async () => {
    await assert.rejects(streamChat('Question', (event) => events.push(event)), (error) =>
      error.code === 'provider_unavailable' && !error.message.includes('secret upstream'));
  });
  assert.deepEqual(events, [{ type: 'delta', text: 'Partial' }]);
});

test('stream ending without completed is an interrupted answer', async () => {
  const { streamChat } = await loadClient();
  await withFetch(async () => sseResponse('event: delta\ndata: {"text":"Partial"}\n\n'), async () => {
    await assert.rejects(streamChat('Question', () => {}), (error) => error.code === 'interrupted');
  });
});

test('malformed event is rejected without exposing its payload', async () => {
  const { streamChat } = await loadClient();
  await withFetch(async () => sseResponse('event: citations\ndata: {"citations":"secret"}\n\n'), async () => {
    await assert.rejects(streamChat('Question', () => {}), (error) =>
      error.code === 'protocol_error' && !error.message.includes('secret'));
  });
});
