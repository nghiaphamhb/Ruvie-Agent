import assert from 'node:assert/strict';
import test from 'node:test';

test('registration validation counts Unicode characters and identifies the first invalid fields', async () => {
  const form = await import('../src/lib/features/auth/auth-form.ts').catch(() => null);
  assert.ok(form, 'shared form validation is required');
  assert.deepEqual(form.validateRegistration('Nguyễn An', 'an@example.test', '🔒'.repeat(12), '🔒'.repeat(12)), {});
  const errors = form.validateRegistration(' ', 'a b@example.test', 'short', 'short');
  assert.equal(errors.display_name.key, 'auth.errors.required');
  assert.equal(errors.email.key, 'auth.errors.invalidEmail');
  assert.equal(errors.password.key, 'auth.errors.passwordLength');
  assert.deepEqual(form.validateRegistration('Name', 'a@example.test', 'a'.repeat(128), 'a'.repeat(128)), {});
  assert.equal(form.validateRegistration('Name', 'a@example.test', 'a'.repeat(129), 'a'.repeat(129)).password.key, 'auth.errors.passwordLength');
});

test('login retains native local-domain email and existing short passwords', async () => {
  const {validateLogin} = await import('../src/lib/features/auth/auth-form.ts');
  assert.deepEqual(validateLogin('person@localhost', 'short'), {});
});


test('registration requires an exact password confirmation, including whitespace and Unicode', async () => {
  const {validateRegistration}=await import('../src/lib/features/auth/auth-form.ts');
  const password=' 🔒'.repeat(12);
  assert.equal(validateRegistration('An','an@example.test',password,'').password_confirmation?.key,'auth.errors.required');
  assert.equal(validateRegistration('An','an@example.test',password,password.trim()).password_confirmation?.key,'auth.errors.passwordMismatch');
  assert.equal(validateRegistration('An','an@example.test',password,password.normalize('NFKC')+'x').password_confirmation?.key,'auth.errors.passwordMismatch');
  assert.deepEqual(validateRegistration('An','an@example.test',password,password),{});
});
