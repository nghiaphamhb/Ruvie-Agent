import { message, type UiMessage } from '../../i18n/messages.ts';
export type AuthField = 'display_name' | 'email' | 'password' | 'password_confirmation';
export type AuthFieldErrors = Partial<Record<AuthField, UiMessage>>;

/** Validate registration email; retain native local-domain email support for existing logins. */
export function validEmail(value: string, requireDomainDot = true): boolean {
  const email = value.trim().toLowerCase();
  return email.length >= 3 && email.length <= 320 &&
    (!requireDomainDot || email.slice(email.lastIndexOf('@') + 1).includes('.')) &&
    /^[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)*$/.test(email);
}

/** Count Unicode code points like Python len; do not trim or truncate passwords. */
export function validateRegistration(name: string, email: string, password: string, confirmation: string): AuthFieldErrors {
  const errors: AuthFieldErrors = {};
  const nameLength = Array.from(name.trim()).length;
  if (!nameLength) errors.display_name = message('auth.errors.required');
  else if (nameLength > 255) errors.display_name = message('auth.errors.nameLength');
  if (!email.trim()) errors.email = message('auth.errors.required');
  else if (!validEmail(email)) errors.email = message('auth.errors.invalidEmail');
  const passwordLength = Array.from(password).length;
  if (!passwordLength) errors.password = message('auth.errors.required');
  else if (passwordLength < 12 || passwordLength > 128) errors.password = message('auth.errors.passwordLength');
  if (!confirmation) errors.password_confirmation = message('auth.errors.required');
  else if (confirmation !== password) errors.password_confirmation = message('auth.errors.passwordMismatch');
  return errors;
}

/** Login intentionally keeps the old password policy for previously provisioned accounts. */
export function validateLogin(email: string, password: string): AuthFieldErrors {
  const errors: AuthFieldErrors = {};
  if (!email.trim()) errors.email = message('auth.errors.required');
  else if (!validEmail(email, false)) errors.email = message('auth.errors.invalidEmail');
  if (!password) errors.password = message('auth.errors.required');
  return errors;
}
