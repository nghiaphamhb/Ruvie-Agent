import { message, type UiMessage } from '../../i18n/messages.ts';
import type { PasswordChangeField } from '../auth/auth-api.ts';

export type PasswordChangeValues = {
  current_password: string;
  new_password: string;
  password_confirmation: string;
};

export type PasswordChangeFormErrors = Partial<Record<PasswordChangeField, UiMessage>>;

export function validatePasswordChange(values: PasswordChangeValues): PasswordChangeFormErrors {
  const errors: PasswordChangeFormErrors = {};
  const current = values.current_password;
  const next = values.new_password;
  const confirmation = values.password_confirmation;

  if (!current) errors.current_password = message('account.password.errors.required');
  else if ([...current].length > 1024)
    errors.current_password = message('account.password.errors.length');
  if (!next) errors.new_password = message('account.password.errors.required');
  else if ([...next].length < 12 || [...next].length > 128) {
    errors.new_password = message('account.password.errors.length');
  }
  if (!confirmation) errors.password_confirmation = message('account.password.errors.required');
  else if (next !== confirmation)
    errors.password_confirmation = message('account.password.errors.mismatch');
  if (current && next && current === next)
    errors.new_password = message('account.password.errors.unchanged');
  return errors;
}
