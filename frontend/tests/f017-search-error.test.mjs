import assert from 'node:assert/strict';
import test from 'node:test';
import { retrieveDocuments } from '../src/lib/features/documents/documents-api.ts';
test('search exposes a safe embedding message without upstream details', async () => {
  const previous = globalThis.fetch;
  try {
    globalThis.fetch = async () =>
      new Response(
        JSON.stringify({ detail: { code: 'embedding_unavailable', message: 'private key' } }),
        { status: 503 },
      );
    await assert.rejects(
      retrieveDocuments('query'),
      (error) =>
        error.uiMessage.key === 'chat.errors.embedding_unavailable' &&
        !error.message.includes('private'),
    );
  } finally {
    globalThis.fetch = previous;
  }
});
