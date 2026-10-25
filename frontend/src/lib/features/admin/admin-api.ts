import { message, type UiMessage } from '../../i18n/messages.ts';
import type { AccountInput, AccountRole, AccountFieldErrors } from './admin-form.ts';

export type AccountSummary = {
  id: string;
  display_name: string;
  email: string;
  system_role: AccountRole;
  is_active: boolean;
  created_at: string;
};
export type AccountListQuery = { q?: string; page?: number; page_size?: number };
export type AccountPresence = { is_online: boolean; last_active_at: string | null };
export type AccountList = {
  users: AccountSummary[];
  total: number;
  page: number;
  page_size: number;
  presence?: Record<string, AccountPresence>;
};
const safeCodes = [
  'authentication_required',
  'admin_required',
  'csrf_invalid',
  'origin_not_allowed',
  'email_taken',
  'validation_error',
  'account_creation_failed',
  'account_lookup_unavailable',
  'account_update_unavailable',
  'account_not_found',
  'last_active_admin',
] as const;
type AdminErrorCode = (typeof safeCodes)[number] | 'unknown';

/** Safe server code/status only; raw server bodies and credentials are discarded. */
export class AdminApiError extends Error {
  readonly code: AdminErrorCode;
  readonly status?: number;
  readonly fieldErrors: AccountFieldErrors;
  constructor(code: AdminErrorCode, status?: number, fieldErrors: AccountFieldErrors = {}) {
    super('Account administration request failed');
    this.code = code;
    this.status = status;
    this.fieldErrors = fieldErrors;
  }
}

async function request(path: string, init: RequestInit = {}): Promise<Response> {
  try {
    return await fetch(path, { ...init, credentials: 'same-origin', cache: 'no-store' });
  } catch {
    throw new AdminApiError('unknown');
  }
}

/** Reject malformed success before exposing allowlisted account metadata to UI. */
function summary(value: unknown): AccountSummary {
  if (!value || typeof value !== 'object') throw new AdminApiError('unknown');
  const user = value as Record<string, unknown>;
  if (
    typeof user.id !== 'string' ||
    !user.id ||
    typeof user.display_name !== 'string' ||
    typeof user.email !== 'string' ||
    (user.system_role !== 'user' && user.system_role !== 'admin') ||
    typeof user.is_active !== 'boolean' ||
    typeof user.created_at !== 'string' ||
    !/(?:Z|[+-]\d{2}:\d{2})$/i.test(user.created_at) ||
    !Number.isFinite(Date.parse(user.created_at))
  )
    throw new AdminApiError('unknown');
  return {
    id: user.id,
    display_name: user.display_name,
    email: user.email,
    system_role: user.system_role,
    is_active: user.is_active,
    created_at: user.created_at,
  };
}

async function body(response: Response): Promise<Record<string, unknown>> {
  let value;
  try {
    value = await response.json();
  } catch {
    throw new AdminApiError('unknown', response.status);
  }
  if (response.ok) return value;
  const detail = value?.detail;
  const code: AdminErrorCode = safeCodes.includes(detail?.code) ? detail.code : 'unknown';
  const fields: AccountFieldErrors = {};
  if (response.status === 409 && code === 'email_taken')
    fields.email = message('auth.errors.emailTaken');
  if (response.status === 422 && code === 'validation_error') {
    for (const field of ['display_name', 'email', 'password', 'system_role'] as const) {
      const failure = detail?.fields?.[field];
      let ui: UiMessage | undefined;
      if (failure === 'required') ui = message('auth.errors.required');
      else if (field === 'display_name' && failure === 'name_length')
        ui = message('auth.errors.nameLength');
      else if (field === 'email' && ['invalid_email', 'email_length'].includes(failure))
        ui = message('auth.errors.invalidEmail');
      else if (field === 'password' && failure === 'password_length')
        ui = message('auth.errors.passwordLength');
      else if (
        failure === 'invalid_type' ||
        (field === 'system_role' && failure === 'invalid_role')
      )
        ui = message('auth.errors.invalid');
      if (ui) fields[field] = ui;
    }
  }
  throw new AdminApiError(code, response.status, fields);
}

/** POST /admin/users: recipient identity/role -> metadata, never an auth session. */
export async function createAccount(
  input: AccountInput,
  csrfToken: string,
): Promise<AccountSummary> {
  const response = await request('/admin/users', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
    body: JSON.stringify({
      display_name: input.display_name.trim(),
      email: input.email.trim().toLowerCase(),
      password: input.password,
      system_role: input.system_role,
    }),
  });
  const value = await body(response);
  return summary(value?.user);
}

/** GET exact email returns zero/one summary; a match does not prove a previous POST committed. */
export async function lookupAccount(email: string): Promise<AccountSummary | null> {
  const response = await request(
    '/admin/users?email=' + encodeURIComponent(email.trim().toLowerCase()),
  );
  const value = await body(response);
  if (!Array.isArray(value?.users) || value.users.length > 1)
    throw new AdminApiError('unknown', response.status);
  return value.users.length ? summary(value.users[0]) : null;
}

/** PATCH changed identity/role fields and an optional password reset; activity stays server-owned. */
export async function updateAccount(
  id: string,
  input: { display_name?: string; email?: string; system_role?: AccountRole; password?: string },
  csrfToken: string,
): Promise<AccountSummary> {
  const update: {
    display_name?: string;
    email?: string;
    system_role?: AccountRole;
    password?: string;
  } = {};
  if (input.display_name !== undefined) update.display_name = input.display_name.trim();
  if (input.email !== undefined) update.email = input.email.trim().toLowerCase();
  if (input.system_role !== undefined) update.system_role = input.system_role;
  if (input.password !== undefined) update.password = input.password;
  if (!Object.keys(update).length) throw new AdminApiError('validation_error');
  const response = await request(`/admin/users/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
    body: JSON.stringify(update),
  });
  const value = await body(response);
  return summary(value?.user);
}

/** GET by immutable ID to reconcile an update whose response may have been lost. */
export async function getAccount(id: string): Promise<AccountSummary> {
  const response = await request(`/admin/users/${encodeURIComponent(id)}`);
  const value = await body(response);
  return summary(value?.user);
}

/** GET a bounded admin-only page; search text never supplies identity or authorization. */
export async function listAccounts(query: AccountListQuery = {}): Promise<AccountList> {
  const q = (query.q ?? '').trim();
  const page = query.page ?? 1;
  const pageSize = query.page_size ?? 20;
  if (
    Array.from(q).length > 255 ||
    !Number.isInteger(page) ||
    page < 1 ||
    page > 1_000_000 ||
    !Number.isInteger(pageSize) ||
    pageSize < 1 ||
    pageSize > 100
  )
    throw new AdminApiError('validation_error');
  const params = new URLSearchParams({ q, page: String(page), page_size: String(pageSize) });
  const response = await request('/admin/users/list?' + params);
  const value = await body(response);
  if (
    !Array.isArray(value?.users) ||
    value.users.length > pageSize ||
    typeof value.total !== 'number' ||
    !Number.isSafeInteger(value.total) ||
    value.total < value.users.length ||
    value.page !== page ||
    value.page_size !== pageSize
  )
    throw new AdminApiError('unknown', response.status);
  const users = value.users.map(summary);
  let presence: Record<string, AccountPresence> | undefined;
  if (value.presence !== undefined) {
    if (!value.presence || typeof value.presence !== 'object' || Array.isArray(value.presence))
      throw new AdminApiError('unknown');
    const records = value.presence as Record<string, AccountPresence>;
    presence = Object.fromEntries(
      users.map((user) => {
        const record = records[user.id];
        if (
          !record ||
          typeof record.is_online !== 'boolean' ||
          (record.last_active_at !== null &&
            (typeof record.last_active_at !== 'string' ||
              !/(?:Z|[+-]\d{2}:\d{2})$/i.test(record.last_active_at) ||
              !Number.isFinite(Date.parse(record.last_active_at))))
        )
          throw new AdminApiError('unknown');
        return [user.id, { is_online: record.is_online, last_active_at: record.last_active_at }];
      }),
    );
  }
  return {
    users,
    total: value.total,
    page,
    page_size: pageSize,
    ...(presence ? { presence } : {}),
  };
}
