import assert from 'node:assert/strict';
import test from 'node:test';
import { validatePasswordChange } from '../src/lib/features/settings/password-form.ts';

const valid = {
  current_password: ' current-password ',
  new_password: ' new-password-123 ',
  password_confirmation: ' new-password-123 ',
};

test('validates required and length rules using Unicode code points without trimming', () => {
  assert.deepEqual(validatePasswordChange(valid), {});
  assert.deepEqual(
    validatePasswordChange({
      ...valid,
      current_password: '',
    }).current_password.key,
    'account.password.errors.required',
  );
  assert.deepEqual(
    validatePasswordChange({
      ...valid,
      current_password: 'x'.repeat(1025),
    }).current_password.key,
    'account.password.errors.length',
  );
  assert.deepEqual(
    validatePasswordChange({
      ...valid,
      new_password: '😀'.repeat(12),
      password_confirmation: '😀'.repeat(12),
    }),
    {},
  );
  assert.equal(
    validatePasswordChange({
      ...valid,
      new_password: '😀'.repeat(11),
      password_confirmation: '😀'.repeat(11),
    }).new_password.key,
    'account.password.errors.length',
  );
});

test('marks confirmation mismatch and unchanged password on their fields', () => {
  assert.equal(
    validatePasswordChange({
      ...valid,
      password_confirmation: 'different-password',
    }).password_confirmation.key,
    'account.password.errors.mismatch',
  );
  assert.equal(
    validatePasswordChange({
      ...valid,
      new_password: valid.current_password,
      password_confirmation: valid.current_password,
    }).new_password.key,
    'account.password.errors.unchanged',
  );
});

test('does not mutate submitted form values', () => {
  const values = { ...valid };
  const snapshot = { ...values };
  validatePasswordChange(values);
  assert.deepEqual(values, snapshot);
});
