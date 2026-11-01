import assert from 'node:assert/strict';
import test from 'node:test';
import { loadState, json, frame, catalog } from './state-loader.mjs';

test('history ignores a slow previous selection and clears on disposal', async () => {
  const { createChatState } = await loadState('../src/lib/features/chat/chat-state.svelte.ts');
  const original = globalThis.fetch;
  const pending = [];
  globalThis.fetch = (url, init) => new Promise((resolve) => pending.push({ url, init, resolve }));
  try {
    const chat = createChatState({
      csrfToken: 'csrf',
      getCatalog: () => null,
      isLocked: () => false,
      onexpired() {},
      onModelUnavailable() {},
    });
    const first = chat.open('first');
    const second = chat.open('second');
    const detail = (id) => ({
      conversation: { id, title: id, version: 1 },
      turns: [
        { id: id + '-turn', question: id, answer: 'answer', citations: [], status: 'completed' },
      ],
      next_cursor: null,
    });
    pending[1].resolve(json(detail('second')));
    await second;
    pending[0].resolve(json(detail('first')));
    await first;
    assert.equal(chat.conversationId, 'second');
    assert.equal(chat.turns[0].question, 'second');
    chat.dispose();
    assert.equal(chat.turns.length, 0);
    assert.equal(chat.conversationId, null);
  } finally {
    globalThis.fetch = original;
  }
});

test('remote active attempt locks send and stop preserves a completed race result', async () => {
  const { createChatState } = await loadState('../src/lib/features/chat/chat-state.svelte.ts');
  const original = globalThis.fetch;
  let stopped = false;
  const calls = [];
  globalThis.fetch = async (url, init) => {
    calls.push({ url, init });
    if (init.method === 'POST') {
      stopped = true;
      return json({ attempt_id: 'attempt', status: 'completed' });
    }
    return json({
      conversation: { id: 'chat', title: 'Chat', version: 1 },
      turns: [
        {
          id: 'turn',
          attempt_id: 'attempt',
          question: 'Question',
          answer: 'Committed',
          citations: [],
          model_id: 'one',
          status: stopped ? 'completed' : 'generating',
          content_unavailable: false,
        },
      ],
      next_cursor: null,
    });
  };
  try {
    const chat = createChatState({
      csrfToken: 'csrf',
      getCatalog: () => null,
      isLocked: () => false,
      onexpired() {},
      onModelUnavailable() {},
    });
    await chat.open('chat');
    assert.equal(chat.busy, true);
    await chat.stop();
    assert.equal(chat.busy, false);
    assert.equal(chat.turns[0].status, 'completed');
    assert.equal(chat.turns[0].answer, 'Committed');
    const stop = calls.find((call) => call.init.method === 'POST');
    assert.equal(stop.url, '/conversations/chat/turns/turn/stop');
    assert.equal(stop.init.headers['X-CSRF-Token'], 'csrf');
    assert.deepEqual(JSON.parse(stop.init.body), { attempt_id: 'attempt' });
    chat.dispose();
  } finally {
    globalThis.fetch = original;
  }
});

test('hydration never retains redacted assistant text or citation metadata', async () => {
  const { createChatState } = await loadState('../src/lib/features/chat/chat-state.svelte.ts');
  const original = globalThis.fetch;
  globalThis.fetch = async () =>
    json({
      conversation: { id: 'chat', title: 'Chat', version: 1 },
      turns: [
        {
          id: 'turn',
          question: 'Question',
          answer: 'must not retain',
          citations: [{ title: 'must not retain' }],
          status: 'completed',
          content_unavailable: true,
        },
      ],
      next_cursor: null,
    });
  try {
    const chat = createChatState({
      getCatalog: () => null,
      isLocked: () => false,
      onexpired() {},
      onModelUnavailable() {},
    });
    await chat.open('chat');
    assert.equal(chat.turns[0].answer, '');
    assert.deepEqual(chat.turns[0].citations, []);
    assert.equal(chat.turns[0].contentUnavailable, true);
    chat.dispose();
  } finally {
    globalThis.fetch = original;
  }
});

test('failed history retains a localized safe explanation', async () => {
  const { createChatState } = await loadState('../src/lib/features/chat/chat-state.svelte.ts');
  const original = globalThis.fetch;
  globalThis.fetch = async () =>
    json({
      conversation: { id: 'chat', title: 'Chat', version: 1 },
      turns: [
        {
          id: 'turn',
          question: 'Question',
          answer: '',
          citations: [],
          status: 'error',
          error_code: 'embedding_unavailable',
          content_unavailable: false,
        },
      ],
      next_cursor: null,
    });
  try {
    const chat = createChatState({
      getCatalog: () => null,
      isLocked: () => false,
      onexpired() {},
      onModelUnavailable() {},
    });
    await chat.open('chat');
    assert.equal(chat.turns[0].error?.key, 'chat.errors.embedding_unavailable');
    chat.dispose();
  } finally {
    globalThis.fetch = original;
  }
});

test('stop during admission waits for accepted and stops the durable attempt', async () => {
  const { createChatState } = await loadState('../src/lib/features/chat/chat-state.svelte.ts');
  const original = globalThis.fetch;
  let output;
  let stopCount = 0;
  globalThis.fetch = async (url) => {
    if (url === '/chat')
      return new Response(
        new ReadableStream({
          start(controller) {
            output = controller;
          },
          cancel() {},
        }),
        { headers: { 'Content-Type': 'text/event-stream' } },
      );
    if (url.endsWith('/stop')) {
      stopCount++;
      return json({ attempt_id: 'attempt', status: 'stopped' });
    }
    if (url === '/conversations') return json({ items: [], next_cursor: null });
    return json({
      conversation: { id: 'chat', title: 'Chat', version: 1 },
      turns: [
        {
          id: 'turn',
          attempt_id: 'attempt',
          question: 'Question',
          answer: '',
          citations: [],
          model_id: 'one',
          status: 'stopped',
          content_unavailable: false,
        },
      ],
      next_cursor: null,
    });
  };
  try {
    const chat = createChatState({
      csrfToken: 'csrf',
      getCatalog: () => catalog,
      isLocked: () => false,
      onexpired() {},
      onModelUnavailable() {},
    });
    chat.draft = 'Question';
    const sending = chat.submit();
    await new Promise((resolve) => setTimeout(resolve, 0));
    const stopping = chat.stop();
    assert.equal(chat.busy, true, 'Admission must remain owned until its IDs arrive');
    output.enqueue(
      frame('accepted', { conversation_id: 'chat', turn_id: 'turn', attempt_id: 'attempt' }),
    );
    for (let i = 0; i < 10 && stopCount === 0; i++)
      await new Promise((resolve) => setTimeout(resolve, 0));
    assert.equal(stopCount, 1);
    output.close();
    await sending;
    await stopping;
    await new Promise((resolve) => setTimeout(resolve, 0));
    assert.equal(chat.turns[0].status, 'stopped');
    chat.dispose();
  } finally {
    globalThis.fetch = original;
  }
});

test('late stop response cannot cancel a newer attempt in the same conversation', async () => {
  const { createChatState } = await loadState('../src/lib/features/chat/chat-state.svelte.ts');
  const original = globalThis.fetch;
  const outputs = [];
  let finishStop;
  globalThis.fetch = async (url) => {
    if (url === '/chat')
      return new Response(
        new ReadableStream({
          start(c) {
            outputs.push(c);
          },
        }),
        { headers: { 'Content-Type': 'text/event-stream' } },
      );
    if (url.endsWith('/stop'))
      return new Promise((resolve) => {
        finishStop = () => resolve(json({ status: 'completed' }));
      });
    if (url === '/conversations') return json({ items: [], next_cursor: null });
    return json({ conversation: { id: 'chat' }, turns: [], next_cursor: null });
  };
  try {
    const chat = createChatState({
      csrfToken: 'csrf',
      getCatalog: () => catalog,
      isLocked: () => false,
      onexpired() {},
      onModelUnavailable() {},
    });
    chat.draft = 'First';
    const first = chat.submit();
    await new Promise((r) => setTimeout(r, 0));
    outputs[0].enqueue(
      frame('accepted', { conversation_id: 'chat', turn_id: 'first', attempt_id: 'first-attempt' }),
    );
    await new Promise((r) => setTimeout(r, 0));
    const stopping = chat.stop();
    outputs[0].enqueue(frame('completed', {}));
    await first;
    chat.draft = 'Second';
    const second = chat.submit();
    await new Promise((r) => setTimeout(r, 0));
    finishStop();
    await stopping;
    assert.equal(chat.busy, true);
    assert.equal(chat.turns.at(-1).question, 'Second');
    outputs[1].enqueue(
      frame('accepted', {
        conversation_id: 'chat',
        turn_id: 'second',
        attempt_id: 'second-attempt',
      }),
    );
    outputs[1].enqueue(frame('completed', {}));
    await second;
    chat.dispose();
  } finally {
    globalThis.fetch = original;
  }
});

test('pending admission stop settles when a conflict reconciles existing history', async () => {
  const { createChatState } = await loadState('../src/lib/features/chat/chat-state.svelte.ts');
  const original = globalThis.fetch;
  let rejectSend;
  globalThis.fetch = async (url) => {
    if (url === '/chat')
      return new Promise((resolve) => {
        rejectSend = () => resolve(json({ detail: { code: 'generation_active' } }, 409));
      });
    return json({
      conversation: { id: 'chat', title: 'Chat', version: 1 },
      turns: [],
      next_cursor: null,
    });
  };
  let timer;
  try {
    const chat = createChatState({
      csrfToken: 'csrf',
      getCatalog: () => catalog,
      isLocked: () => false,
      onexpired() {},
      onModelUnavailable() {},
    });
    await chat.open('chat');
    chat.draft = 'Question';
    const sending = chat.submit();
    await new Promise((r) => setTimeout(r, 0));
    const stopping = chat.stop();
    rejectSend();
    await sending;
    await Promise.race([
      stopping,
      new Promise((_, reject) => {
        timer = setTimeout(() => reject(new Error('Stop waiter did not settle')), 500);
      }),
    ]);
    chat.dispose();
  } finally {
    clearTimeout(timer);
    globalThis.fetch = original;
  }
});

test('lost accepted retries the original request ID and reconciles without another local turn', async () => {
  const { createChatState } = await loadState('../src/lib/features/chat/chat-state.svelte.ts');
  const original = globalThis.fetch;
  const submissions = [];
  globalThis.fetch = async (url, init) => {
    if (url === '/chat') {
      submissions.push(JSON.parse(init.body));
      if (submissions.length === 1)
        return new Response(
          new ReadableStream({
            start(controller) {
              controller.close();
            },
          }),
          { headers: { 'Content-Type': 'text/event-stream' } },
        );
      return json(
        {
          detail: {
            code: 'request_already_recorded',
            conversation_id: 'chat',
            turn_id: 'saved',
            attempt_id: 'attempt',
          },
        },
        409,
      );
    }
    return json({
      conversation: { id: 'chat', title: 'Question', version: 1 },
      turns: [
        {
          id: 'saved',
          attempt_id: 'attempt',
          question: 'Question',
          answer: 'Committed',
          citations: [],
          model_id: 'one',
          status: 'completed',
          content_unavailable: false,
        },
      ],
      next_cursor: null,
    });
  };
  try {
    const chat = createChatState({
      csrfToken: 'csrf',
      getCatalog: () => catalog,
      isLocked: () => false,
      onexpired() {},
      onModelUnavailable() {},
    });
    chat.draft = 'Question';
    await chat.submit();
    assert.equal(
      submissions.length,
      1,
      'an uncertain result must not automatically resend the question',
    );
    await chat.retry(chat.turns[0].id);
    assert.equal(submissions[0].request_id, submissions[1].request_id);
    assert.equal(chat.conversationId, 'chat');
    assert.equal(chat.turns.length, 1);
    assert.equal(chat.turns[0].serverId, 'saved');
    assert.equal(chat.turns[0].answer, 'Committed');
    chat.dispose();
  } finally {
    globalThis.fetch = original;
  }
});
