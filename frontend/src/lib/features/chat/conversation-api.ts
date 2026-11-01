/** Private history HTTP boundary. Never persist chat data in browser storage. */
import type { Citation } from './chat-api.ts';
export type Conversation = {
  id: string;
  title: string;
  version: number;
  created_at: string;
  updated_at: string;
};
export type SavedTurn = {
  id: string;
  ordinal: number;
  created_at?: string;
  started_at?: string | null;
  finished_at?: string | null;
  question: string;
  answer: string;
  model_id: string;
  attempt_id: string;
  status: string;
  citations: Citation[];
  error_code?: string | null;
  content_unavailable: boolean;
};
export type HistoryPage = {
  conversation: Conversation;
  turns: SavedTurn[];
  next_cursor: string | null;
};
export class HistoryError extends Error {
  status: number;
  code: string;
  resources: Record<string, string>;
  constructor(status: number, code: string, resources: Record<string, string> = {}) {
    super('History request failed');
    this.status = status;
    this.code = code;
    this.resources = resources;
  }
}
export async function historyRequest<T>(
  path: string,
  csrf: string,
  method = 'GET',
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch(path, {
    method,
    credentials: 'same-origin',
    cache: 'no-store',
    signal,
    headers: {
      'Content-Type': 'application/json',
      ...(method === 'GET' ? {} : { 'X-CSRF-Token': csrf }),
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    const detail = data?.detail;
    throw new HistoryError(
      response.status,
      typeof detail?.code === 'string' ? detail.code : 'history_unavailable',
      typeof detail === 'object' && detail ? detail : {},
    );
  }
  return response.status === 204 ? (undefined as T) : response.json();
}
