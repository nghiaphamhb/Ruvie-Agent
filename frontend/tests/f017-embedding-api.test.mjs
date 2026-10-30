import assert from 'node:assert/strict';
import test from 'node:test';
import {
  getEmbeddingConnection,
  applyEmbeddingConnection,
  EmbeddingApiError,
} from '../src/lib/features/embedding/embedding-api.ts';
import { json } from './state-loader.mjs';
const metadata = {
  configured: true,
  base_url: 'https://embed.test',
  has_api_key: true,
  network: { mode: 'direct', proxy_url: null },
  model_id: 'baai/bge-m3',
  dimension: 1024,
  distance_metric: 'cosine',
  version: 1,
  updated_at: null,
};
test('metadata projection drops provider secrets and malformed apply stays uncertain', async () => {
  const previous = globalThis.fetch;
  try {
    globalThis.fetch = async () =>
      json({ ...metadata, api_key: 'secret', api_key_ciphertext: 'cipher' });
    const result = await getEmbeddingConnection();
    assert.equal(JSON.stringify(result).includes('secret'), false);
    assert.equal('api_key_ciphertext' in result, false);
    globalThis.fetch = async () => json({ version: 2, api_key: 'secret' });
    await assert.rejects(
      applyEmbeddingConnection('csrf', {
        base_url: 'https://embed.test',
        key_action: 'clear',
        expected_version: 1,
      network: { mode: 'direct', proxy_url: null },
        model_id: 'baai/bge-m3',
      }),
      (error) =>
        error instanceof EmbeddingApiError && error.uncertain && !error.message.includes('secret'),
    );
  } finally {
    globalThis.fetch = previous;
  }
});
test('provider error bodies are projected to a safe known code only', async () => {
  const previous = globalThis.fetch;
  try {
    globalThis.fetch = async () => json({ detail: { code: 'private upstream secret' } }, 503);
    await assert.rejects(
      getEmbeddingConnection(),
      (error) => error.code === 'network' && !JSON.stringify(error).includes('private'),
    );
    globalThis.fetch = async () =>
      json({ detail: { code: 'embedding_authentication_failed' } }, 503);
    await assert.rejects(
      getEmbeddingConnection(),
      (error) => error.code === 'embedding_authentication_failed',
    );
  } finally {
    globalThis.fetch = previous;
  }
});
