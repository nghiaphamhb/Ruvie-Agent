<script lang="ts">
  import { onDestroy, tick } from 'svelte';
  import { i18n } from '../../i18n/index.ts';
  import { validateRegistration, type AuthFieldErrors } from './auth-form.ts';
  import PasswordField from './PasswordField.svelte';
  let {
    busy,
    fieldErrors,
    email = $bindable(''),
    onregister,
    onerrorclear,
  }: {
    busy: boolean;
    fieldErrors: AuthFieldErrors;
    email?: string;
    onregister: (name: string, email: string, password: string) => Promise<boolean>;
    onerrorclear: () => void;
  } = $props();
  let name = $state('');
  let password = $state('');
  let confirmation = $state('');
  let localErrors = $state<AuthFieldErrors>({});
  let fields = $derived({ ...fieldErrors, ...localErrors });
  onDestroy(() => {
    password = '';
    confirmation = '';
  });
  function clearErrors() {
    localErrors = {};
    onerrorclear();
  }
  async function focusFirst(errors: AuthFieldErrors) {
    const first = ['display_name', 'email', 'password', 'password_confirmation'].find(
      (field) => field in errors,
    );
    if (first) {
      await tick();
      document.getElementById(first)?.focus();
    }
  }
  async function submit(event: SubmitEvent) {
    event.preventDefault();
    if (busy) return;
    onerrorclear();
    localErrors = validateRegistration(name, email, password, confirmation);
    if (Object.keys(localErrors).length) {
      await focusFirst(localErrors);
      return;
    }
    if (await onregister(name.trim(), email.trim(), password)) {
      password = '';
      confirmation = '';
    } else await focusFirst(fieldErrors);
  }
</script>

<form class="auth-form" aria-busy={busy} novalidate onsubmit={submit} oninput={clearErrors}>
  <h1>{$i18n.t('auth.register')}</h1>
  <fieldset disabled={busy}>
    <div class="auth-field">
      <label for="display_name">{$i18n.t('auth.name')}</label>
      <input
        id="display_name"
        name="display_name"
        class="auth-input"
        type="text"
        autocomplete="name"
        required
        bind:value={name}
        aria-invalid={Boolean(fields.display_name)}
        aria-describedby={localErrors.display_name ? 'name-error' : undefined}
      />
      {#if localErrors.display_name}<p id="name-error" class="field-error" role="alert">
          {$i18n.message(localErrors.display_name)}
        </p>{/if}
    </div>
    <div class="auth-field">
      <label for="email">{$i18n.t('auth.email')}</label>
      <input
        id="email"
        name="email"
        class="auth-input"
        type="email"
        autocomplete="email"
        required
        maxlength="320"
        bind:value={email}
        aria-invalid={Boolean(fields.email)}
        aria-describedby={localErrors.email ? 'email-error' : undefined}
      />
      {#if localErrors.email}<p id="email-error" class="field-error" role="alert">
          {$i18n.message(localErrors.email)}
        </p>{/if}
    </div>
    <div class="auth-field">
      <label for="password">{$i18n.t('auth.password')}</label>
      <PasswordField
        bind:value={password}
        disabled={busy}
        autocomplete="new-password"
        invalid={Boolean(fields.password)}
        describedby={localErrors.password ? 'password-error' : undefined}
      />
      {#if localErrors.password}<p id="password-error" class="field-error" role="alert">
          {$i18n.message(localErrors.password)}
        </p>{/if}
    </div>
    <div class="auth-field">
      <label for="password_confirmation">{$i18n.t('auth.confirmPassword')}</label>
      <PasswordField
        id="password_confirmation"
        bind:value={confirmation}
        disabled={busy}
        autocomplete="new-password"
        invalid={Boolean(fields.password_confirmation)}
        describedby={localErrors.password_confirmation ? 'confirmation-error' : undefined}
      />
      {#if localErrors.password_confirmation}<p
          id="confirmation-error"
          class="field-error"
          role="alert"
        >
          {$i18n.message(localErrors.password_confirmation)}
        </p>{/if}
    </div>
    <button class="auth-submit" type="submit"
      >{busy ? $i18n.t('auth.registering') : $i18n.t('auth.register')}</button
    >
  </fieldset>
</form>
