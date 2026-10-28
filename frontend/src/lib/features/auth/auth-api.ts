import { message, type UiMessage } from '../../i18n/messages.ts';
import type { AuthField, AuthFieldErrors } from './auth-form.ts';
export type AuthUser = { id: string; display_name: string; system_role: 'user' | 'admin' };
export type AuthSession = { user: AuthUser; csrf_token: string };
export type AuthSetup = { requires_initial_admin: boolean };
export type PasswordChangeField = 'current_password' | 'new_password' | 'password_confirmation';
export type PasswordChangeFieldErrors = Partial<Record<PasswordChangeField, UiMessage>>;

/** One safe response from POST /auth/password; never retains its request or raw body. */
export class PasswordChangeApiError extends Error {
  readonly status?: number;
  readonly code: string;
  readonly uiMessage: UiMessage;
  readonly fieldErrors: PasswordChangeFieldErrors;
  constructor(
    code: string,
    uiMessage: UiMessage,
    status?: number,
    fieldErrors: PasswordChangeFieldErrors = {},
  ) {
    super('Password change request failed');
    this.code = code;
    this.uiMessage = uiMessage;
    this.status = status;
    this.fieldErrors = fieldErrors;
  }
}

/** Preserve HTTP status and safe translation keys; never expose raw backend detail. */
export class AuthApiError extends Error {
  readonly status?: number;
  readonly uiMessage: UiMessage;
  readonly fieldErrors: AuthFieldErrors;
  readonly code?: string;
  constructor(
    uiMessage: UiMessage,
    status?: number,
    fieldErrors: AuthFieldErrors = {},
    code?: string,
  ) {
    super('Authentication request failed');
    this.uiMessage = uiMessage;
    this.status = status;
    this.fieldErrors = fieldErrors;
    this.code = code;
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
  try {
    const value = await response.json();
    const user = value?.user;
    if (
      !user ||
      typeof user.id !== 'string' ||
      !user.id ||
      typeof user.display_name !== 'string' ||
      !['user', 'admin'].includes(user.system_role) ||
      typeof value.csrf_token !== 'string' ||
      !value.csrf_token
    ) {
      throw new Error('Invalid session');
    }
    return {
      user: { id: user.id, display_name: user.display_name, system_role: user.system_role },
      csrf_token: value.csrf_token,
    };
  } catch {
    throw new AuthApiError(message('auth.errors.request'), response.status);
  }
}

export async function getAuthSession(): Promise<AuthSession | null> {
  const response = await request('/auth/session', { cache: 'no-store' });
  if (response.status === 401) return null;
  return readSession(response);
}

/** Presence writes contain no identity or client timestamp; the cookie selects the session. */
export async function sendPresence(csrfToken: string, signal: AbortSignal): Promise<void> {
  const response = await request('/auth/presence', {
    method: 'POST',
    signal,
    cache: 'no-store',
    headers: { 'X-CSRF-Token': csrfToken },
  });
  if (!response.ok) throw new AuthApiError(message('auth.errors.session'), response.status);
}

/** Setup is a strict server fact; a failed/malformed response never means zero accounts. */
export async function getAuthSetup(): Promise<AuthSetup> {
  const response = await request('/auth/setup', { cache: 'no-store' });
  try {
    if (!response.ok) throw new Error('Setup unavailable');
    const body = await response.json();
    if (typeof body?.requires_initial_admin !== 'boolean') throw new Error('Invalid setup');
    return { requires_initial_admin: body.requires_initial_admin };
  } catch {
    throw new AuthApiError(message('auth.errors.setup'), response.status);
  }
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
  if (response.status === 409 && detail.code === 'setup_already_completed') {
    throw new AuthApiError(
      message('auth.errors.setupCompleted'),
      409,
      {},
      'setup_already_completed',
    );
  }
  if (response.status === 409 && detail.code !== 'email_taken') {
    throw new AuthApiError(message('auth.errors.registrationFailed'), 409);
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
  throw new AuthApiError(
    message(key),
    response.status,
    fields,
    detail.code === 'email_taken' ? 'email_taken' : undefined,
  );
}

export async function logout(csrfToken: string): Promise<void> {
  const response = await request('/auth/logout', {
    method: 'POST',
    headers: { 'X-CSRF-Token': csrfToken },
  });
  if (!response.ok) throw new AuthApiError(message('auth.errors.logout'), response.status);
}

/** POST /auth/password changes only the signed-in user's password; never retries. */
export async function changePassword(
  csrfToken: string,
  command: {
    current_password: string;
    new_password: string;
    password_confirmation: string;
  },
  signal?: AbortSignal,
): Promise<void> {
  let response: Response;
  try {
    response = await request('/auth/password', {
      method: 'POST',
      body: JSON.stringify(command),
      signal,
      cache: 'no-store',
      headers: { 'X-CSRF-Token': csrfToken },
    });
  } catch {
    throw new PasswordChangeApiError(
      'result_unknown',
      message('account.password.errors.resultUnknown'),
    );
  }
  if (response.status === 204) return;

  const detail = await response.json().catch(() => null);
  const serverCode = typeof detail?.detail?.code === 'string' ? detail.detail.code : '';
  const rawFields = detail?.detail?.fields;
  const fieldErrors: PasswordChangeFieldErrors = {};
  const errorKeys = {
    required: 'required',
    invalid_type: 'invalid',
    password_length: 'length',
    current_password_incorrect: 'currentIncorrect',
    password_confirmation_mismatch: 'mismatch',
    password_unchanged: 'unchanged',
  } as const;
  if (rawFields && typeof rawFields === 'object' && !Array.isArray(rawFields)) {
    for (const field of ['current_password', 'new_password', 'password_confirmation'] as const) {
      const fieldCode = rawFields[field];
      if (typeof fieldCode === 'string' && fieldCode in errorKeys) {
        fieldErrors[field] = message(
          `account.password.errors.${errorKeys[fieldCode as keyof typeof errorKeys]}`,
        );
      }
    }
  }

  if (response.status === 401) {
    throw new PasswordChangeApiError(
      'authentication_required',
      message('account.password.errors.sessionExpired'),
      response.status,
    );
  }
  if (response.status === 403) {
    throw new PasswordChangeApiError(
      serverCode === 'origin_not_allowed' ? serverCode : 'csrf_invalid',
      message('account.password.errors.forbidden'),
      response.status,
    );
  }
  if (response.status === 422) {
    const code = [
      'validation_error',
      'current_password_incorrect',
      'password_confirmation_mismatch',
      'password_unchanged',
    ].includes(serverCode)
      ? serverCode
      : 'validation_error';
    if (Object.keys(fieldErrors).length === 0 && code !== 'validation_error') {
      if (code === 'current_password_incorrect') {
        fieldErrors.current_password = message('account.password.errors.currentIncorrect');
      } else if (code === 'password_confirmation_mismatch') {
        fieldErrors.password_confirmation = message('account.password.errors.mismatch');
      } else if (code === 'password_unchanged') {
        fieldErrors.new_password = message('account.password.errors.unchanged');
      }
    }
    const uiMessage =
      code === 'current_password_incorrect'
        ? message('account.password.errors.currentIncorrect')
        : code === 'password_confirmation_mismatch'
          ? message('account.password.errors.mismatch')
          : code === 'password_unchanged'
            ? message('account.password.errors.unchanged')
            : message('account.password.errors.invalid');
    throw new PasswordChangeApiError(code, uiMessage, response.status, fieldErrors);
  }
  throw new PasswordChangeApiError(
    serverCode === 'password_change_unavailable' ? serverCode : 'password_change_unavailable',
    message('account.password.errors.unavailable'),
    response.status,
  );
}
