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

export class LlmApiError extends Error {
  readonly status?: number;
  constructor(status?: number) {
    const messages: Record<number, string> = {
      401: 'Phiên đăng nhập đã hết hạn.',
      403: 'Không thể xác nhận yêu cầu. Hãy tải lại trang.',
      422: 'URL hoặc model không hợp lệ. Hãy kiểm tra kết nối.',
      502: 'Không lấy được model. Hãy kiểm tra URL, key và thử lại.',
      503: 'Chưa có kết nối LLM hoặc không thể lưu cấu hình.'
    };
    super(messages[status ?? 0] ?? 'Không thể kết nối máy chủ. Hãy thử lại.');
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
