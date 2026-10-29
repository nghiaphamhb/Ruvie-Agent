import { llmErrorMessage, type UiMessage } from '../../i18n/messages.ts';
export type LlmConnection = {
  configured: boolean;
  configuration_version: number;
  selected_model_id: string | null;
};
export type ModelsResult = {
  models: { id: string; name: string }[];
  selected_model_id: string | null;
  selection_required: boolean;
  configuration_version: number;
};

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
  try {
    response = await fetch(path, { ...init, credentials: 'same-origin', cache: 'no-store' });
  } catch {
    throw new LlmApiError();
  }
  if (!response.ok) throw new LlmApiError(response.status);
  return response;
}

/** Employee metadata contains no provider URL or credential presence. */
export async function getLlmConnection(): Promise<LlmConnection> {
  return (await request('/llm/connection')).json();
}
export async function getModels(): Promise<ModelsResult> {
  return (await request('/models')).json();
}

/** PATCH {model_id}: verify/save one preference; keep the previous UI ID until this succeeds. */
export async function selectLlmModel(
  csrfToken: string,
  modelId: string,
): Promise<{ selected_model_id: string; configuration_version: number }> {
  return (
    await request('/llm/connection/model', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
      body: JSON.stringify({ model_id: modelId }),
    })
  ).json();
}
