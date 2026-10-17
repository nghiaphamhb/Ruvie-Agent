import { message, type UiMessage } from '../../i18n/messages.ts';
export type Citation = {
  citation_id: string;
  document_id: string;
  revision_id: string;
  chunk_id: string;
  ordinal: number;
  start_offset: number;
  end_offset: number;
  title: string;
  source_hash: string;
  software: string;
  software_version: string;
};

export type ChatEvent =
  | { type: 'delta'; text: string }
  | { type: 'citations'; citations: Citation[] }
  | { type: 'completed' };

export type ChatErrorCode =
  | 'auth_required'
  | 'invalid_request'
  | 'model_unavailable'
  | 'provider_unavailable'
  | 'generation_failed'
  | 'network_error'
  | 'interrupted'
  | 'protocol_error';

/** Carry a safe message key; translate only when the UI renders it. */
export class ChatApiError extends Error {
  readonly code: ChatErrorCode;
  readonly uiMessage: UiMessage;

  constructor(code: ChatErrorCode) {
    super('Chat request failed');
    this.uiMessage = message(`chat.errors.${code}`);
    this.name = 'ChatApiError';
    this.code = code;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function isCitation(value: unknown): value is Citation {
  if (!isRecord(value)) return false;
  return ['citation_id', 'document_id', 'revision_id', 'chunk_id', 'title', 'source_hash', 'software', 'software_version']
    .every((field) => typeof value[field] === 'string')
    && ['ordinal', 'start_offset', 'end_offset'].every((field) => typeof value[field] === 'number');
}

function parseFrame(frame: string): ChatEvent | { type: 'error'; code: 'provider_unavailable' | 'generation_failed' } {
  const lines = frame.split('\n');
  const name = lines.find((line) => line.startsWith('event:'))?.slice(6).trim();
  const rawData = lines.filter((line) => line.startsWith('data:')).map((line) => line.slice(5).trimStart()).join('\n');
  let data: unknown;
  try {
    data = JSON.parse(rawData);
  } catch {
    throw new ChatApiError('protocol_error');
  }
  if (!isRecord(data)) throw new ChatApiError('protocol_error');

  if (name === 'delta' && typeof data.text === 'string') return { type: 'delta', text: data.text };
  if (name === 'citations' && Array.isArray(data.citations) && data.citations.every(isCitation)) {
    return { type: 'citations', citations: data.citations };
  }
  if (name === 'completed') return { type: 'completed' };
  if (name === 'error' && (data.code === 'provider_unavailable' || data.code === 'generation_failed')) {
    return { type: 'error', code: data.code };
  }
  throw new ChatApiError('protocol_error');
}

/** POST {message, model_id?}; read the existing SSE contract. URL/key stay on the server. */
export async function streamChat(
  message: string,
  onEvent: (event: ChatEvent) => void,
  signal?: AbortSignal,
  modelId?: string
): Promise<void> {
  if (!message.trim()) throw new ChatApiError('invalid_request');

  let response: Response;
  try {
    response = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, ...(modelId === undefined ? {} : { model_id: modelId }) }),
      credentials: 'same-origin',
      signal
    });
  } catch {
    if (signal?.aborted) throw new ChatApiError('interrupted');
    throw new ChatApiError('network_error');
  }

  if (response.status === 401) throw new ChatApiError('auth_required');
  if (response.status === 422) throw new ChatApiError(modelId === undefined ? 'invalid_request' : 'model_unavailable');
  if (!response.ok) throw new ChatApiError('network_error');
  if (!response.headers.get('content-type')?.startsWith('text/event-stream') || !response.body) {
    throw new ChatApiError('protocol_error');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let pending = '';
  try {
    while (true) {
      let chunk: ReadableStreamReadResult<Uint8Array>;
      try {
        chunk = await reader.read();
      } catch {
        throw new ChatApiError('interrupted');
      }
      if (chunk.done) break;
      pending = (pending + decoder.decode(chunk.value, { stream: true })).replace(/\r\n/g, '\n');
      let boundary: number;
      while ((boundary = pending.indexOf('\n\n')) !== -1) {
        const frame = pending.slice(0, boundary);
        pending = pending.slice(boundary + 2);
        if (!frame.trim()) continue;
        const event = parseFrame(frame);
        if (event.type === 'error') throw new ChatApiError(event.code);
        onEvent(event);
        if (event.type === 'completed') return;
      }
    }
  } finally {
    reader.releaseLock();
  }
  throw new ChatApiError('interrupted');
}
