import { message, type UiMessage } from '../../i18n/messages.ts';
import type { AuthField, AuthFieldErrors } from './auth-form.ts';
export type AuthUser = { id: string; display_name: string };
export type AuthSession = { user: AuthUser; csrf_token: string };

/** Preserve HTTP status and safe translation keys; never expose raw backend detail. */
export class AuthApiError extends Error {
  readonly status?: number;
  readonly uiMessage: UiMessage;
  readonly fieldErrors: AuthFieldErrors;
  constructor(uiMessage: UiMessage, status?: number, fieldErrors: AuthFieldErrors = {}) {
    super('Authentication request failed');
    this.uiMessage = uiMessage;
    this.status = status;
    this.fieldErrors = fieldErrors;
  }
}

async function request(path: string, init: RequestInit = {}): Promise<Response> {
  try {
    return await fetch(path, {
      ...init,
      credentials: 'same-origin',
      headers: { ...init.headers, 'Content-Type': 'application/json' },
    });
  } catch {
    throw new AuthApiError(message('common.errors.network'));
  }
}

async function readSession(response: Response): Promise<AuthSession> {
  if (!response.ok)
    throw new AuthApiError(
      response.status === 401 ? message('auth.errors.credentials') : message('auth.errors.request'),
      response.status,
    );
  return response.json() as Promise<AuthSession>;
}

export async function getAuthSession(): Promise<AuthSession | null> {
  const response = await request('/auth/session');
  if (response.status === 401) return null;
  return readSession(response);
}

export async function login(email: string, password: string): Promise<AuthSession> {
  return readSession(
    await request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  );
}

/** POST only registration identity; one attempt avoids accidental account creation retries. */
export async function register(
  displayName: string,
  email: string,
  password: string,
): Promise<AuthSession> {
  const response = await request('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ display_name: displayName.trim(), email: email.trim(), password }),
  });
  if (response.ok) return readSession(response);
  const fields: AuthFieldErrors = {};
  let detail: { code?: string; fields?: Record<string, string> } = {};
  try {
    const body = await response.json();
    if (body?.detail && typeof body.detail === 'object') detail = body.detail;
  } catch {
    /* Invalid error bodies still produce a safe localized notice. */
  }
  const statusKeys = {
    403: 'auth.errors.origin',
    409: 'auth.errors.emailTaken',
    422: 'auth.errors.invalid',
  } as const;
  if ((response.status === 422 || response.status === 409) && detail.fields) {
    for (const field of ['display_name', 'email', 'password'] as AuthField[]) {
      const code = detail.fields[field];
      if (code === 'required') fields[field] = message('auth.errors.required');
      else if (field === 'display_name' && code === 'name_length')
        fields[field] = message('auth.errors.nameLength');
      else if (field === 'password' && code === 'password_length')
        fields[field] = message('auth.errors.passwordLength');
      else if (field === 'email' && code === 'email_taken')
        fields[field] = message('auth.errors.emailTaken');
      else if (field === 'email' && ['invalid_email', 'email_length'].includes(code))
        fields[field] = message('auth.errors.invalidEmail');
      else if (code === 'invalid_type') fields[field] = message('auth.errors.invalid');
    }
  }
  if (response.status === 409) fields.email = message('auth.errors.emailTaken');
  const key =
    statusKeys[response.status as keyof typeof statusKeys] ?? 'auth.errors.registrationFailed';
  throw new AuthApiError(message(key), response.status, fields);
}

export async function logout(csrfToken: string): Promise<void> {
  const response = await request('/auth/logout', {
    method: 'POST',
    headers: { 'X-CSRF-Token': csrfToken },
  });
  if (!response.ok) throw new AuthApiError(message('auth.errors.logout'), response.status);
}
