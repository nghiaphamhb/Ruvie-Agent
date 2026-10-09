import { message, type UiMessage } from './i18n/messages.ts';
export type AuthUser = { id: string; display_name: string };
export type AuthSession = { user: AuthUser; csrf_token: string };

/** Preserve HTTP status and a safe translation key, without browser dependencies. */
export class AuthApiError extends Error {
  readonly status?: number;
  readonly uiMessage: UiMessage;
  constructor(uiMessage: UiMessage, status?: number) {
    super('Authentication request failed');
    this.uiMessage = uiMessage;
    this.status = status;
  }
}

async function request(path: string, init: RequestInit = {}): Promise<Response> {
  try {
    return await fetch(path, { ...init, credentials: 'same-origin', headers: { ...init.headers, 'Content-Type': 'application/json' } });
  } catch {
    throw new AuthApiError(message('common.errors.network'));
  }
}

async function readSession(response: Response): Promise<AuthSession> {
  if (!response.ok) throw new AuthApiError(response.status === 401 ? message('auth.errors.credentials') : message('auth.errors.request'), response.status);
  return response.json() as Promise<AuthSession>;
}

export async function getAuthSession(): Promise<AuthSession | null> {
  const response = await request('/auth/session');
  if (response.status === 401) return null;
  return readSession(response);
}

export async function login(email: string, password: string): Promise<AuthSession> {
  const response = await request('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) });
  return readSession(response);
}

export async function logout(csrfToken: string): Promise<void> {
  const response = await request('/auth/logout', { method: 'POST', headers: { 'X-CSRF-Token': csrfToken } });
  if (!response.ok) throw new AuthApiError(message('auth.errors.logout'), response.status);
}
