import { validateAccountIdentity } from '../auth/auth-form.ts';
import { message, type UiMessage } from '../../i18n/messages.ts';

export type AccountRole = 'user' | 'admin';
export type AccountField = 'display_name' | 'email' | 'password' | 'system_role';
export type AccountFieldErrors = Partial<Record<AccountField, UiMessage>>;
export type AccountInput = {
  display_name: string;
  email: string;
  password: string;
  system_role: AccountRole;
};

/** Admin provisioning reuses identity rules but never requires confirmation. */
export function validateAccount(
  name: string,
  email: string,
  password: string,
  role: string,
): AccountFieldErrors {
  const errors: AccountFieldErrors = validateAccountIdentity(name, email, password);
  if (role !== 'user' && role !== 'admin') errors.system_role = message('auth.errors.invalid');
  return errors;
}
