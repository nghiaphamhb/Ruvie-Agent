export type AuthUser = { id: string; display_name: string };
export type AuthSession = { user: AuthUser; csrf_token: string };

export class AuthApiError extends Error {
  readonly status?: number;
  constructor(message: string, status?: number) { super(message); this.status = status; }
}

async function request(path: string, init: RequestInit = {}): Promise<Response> {
  try {
    return await fetch(path, { ...init, credentials: 'same-origin', headers: { ...init.headers, 'Content-Type': 'application/json' } });
  } catch {
    throw new AuthApiError('Không thể kết nối máy chủ. Hãy thử lại.');
  }
}

async function readSession(response: Response): Promise<AuthSession> {
  if (!response.ok) throw new AuthApiError(response.status === 401 ? 'Email hoặc mật khẩu không đúng.' : 'Không thể xử lý yêu cầu.', response.status);
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
  if (!response.ok) throw new AuthApiError('Không thể đăng xuất. Hãy thử lại.', response.status);
}
