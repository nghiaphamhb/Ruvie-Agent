import { llmErrorMessage, type UiMessage } from './i18n/messages.ts';
export type LlmConnection = {
  source: 'personal' | 'server' | 'none';
  base_url: string | null;
  has_api_key: boolean;
  selected_model_id: string | null;
};
export type ModelsResult = {
  models: { id: string; name: string }[];
  selected_model_id: string | null;
  selection_required: boolean;
};
export type ConnectionInput = { base_url: string; api_key?: string };

/** Carry a safe message key; translate only when the UI renders it. */
export class LlmApiError extends Error {
  readonly status?: number;
  readonly uiMessage: UiMessage;
  constructor(status?: number) {
    super('LLM request failed');
    this.uiMessage = llmErrorMessage(status);
    this.name = 'LlmApiError';
    this.status = status;
  }
}

/** Use the login cookie; never display raw provider errors that may contain secrets. */
async function request(path: string, init?: RequestInit): Promise<Response> {
  let response: Response;
  try { response = await fetch(path, { ...init, credentials: 'same-origin' }); }
  catch { throw new LlmApiError(); }
  if (!response.ok) throw new LlmApiError(response.status);
  return response;
}

/** GET metadata only: the response has has_api_key, never the saved key. */
export async function getLlmConnection(): Promise<LlmConnection> {
  return (await request('/llm/connection')).json();
}
export async function getModels(): Promise<ModelsResult> {
  return (await request('/models')).json();
}

/** PUT {base_url, api_key?}: omitted key keeps the personal key; empty key deletes it. */
export async function saveLlmConnection(csrfToken: string, input: ConnectionInput): Promise<ModelsResult> {
  return (await request('/llm/connection', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
    body: JSON.stringify(input)
  })).json();
}

/** DELETE personal settings, then the caller reloads the server fallback. */
export async function deleteLlmConnection(csrfToken: string): Promise<void> {
  await request('/llm/connection', { method: 'DELETE', headers: { 'X-CSRF-Token': csrfToken } });
}

/** PATCH {model_id}: verify/save one preference; keep the previous UI ID until this succeeds. */
export async function selectLlmModel(csrfToken: string, modelId: string): Promise<{ selected_model_id: string }> {
  return (await request('/llm/connection/model', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
    body: JSON.stringify({ model_id: modelId })
  })).json();
}
