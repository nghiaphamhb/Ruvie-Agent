<script lang="ts">
  import { onDestroy, tick } from 'svelte';
  import { toast } from 'svelte-sonner';
  import { i18n } from '../../i18n/index.ts';
  import { message, type UiMessage } from '../../i18n/messages.ts';
  import PasswordField from '../auth/PasswordField.svelte';
  import {
    changePassword,
    PasswordChangeApiError,
    type PasswordChangeField,
  } from '../auth/auth-api.ts';
  import { validatePasswordChange, type PasswordChangeFormErrors } from './password-form.ts';

  let {
    csrfToken,
    active,
    onexpired,
  }: {
    csrfToken: string;
    active: boolean;
    onexpired: (notice: UiMessage) => void;
  } = $props();
  let currentPassword = $state('');
  let newPassword = $state('');
  let confirmation = $state('');
  let busy = $state(false);
  let errors = $state<PasswordChangeFormErrors>({});
  let fieldResetKey = $state(0);
  let notice = $state<{ id: number; type: 'success' | 'error'; message: UiMessage } | null>(null);
  let nextNoticeId = 1;
  let formGeneration = 0;
  let aborter: AbortController | undefined;

  const ids: Record<PasswordChangeField, string> = {
    current_password: 'change-current-password',
    new_password: 'change-new-password',
    password_confirmation: 'change-password-confirmation',
  };
  const values = () => ({
    current_password: currentPassword,
    new_password: newPassword,
    password_confirmation: confirmation,
  });
  function resetPasswordFields() {
    fieldResetKey++;
    currentPassword = '';
    newPassword = '';
    confirmation = '';
  }
  function clearForm() {
    formGeneration++;
    aborter?.abort();
    aborter = undefined;
    busy = false;
    resetPasswordFields();
    errors = {};
  }
  $effect(() => {
    if (!active) {
      clearForm();
      notice = null;
    }
  });
  $effect(() => {
    const current = notice;
    if (!current) {
      toast.dismiss('password-change');
      return;
    }
    toast[current.type]($i18n.message(current.message), {
      id: 'password-change',
      duration: 5000,
      onDismiss: () => {
        if (notice?.id === current.id) notice = null;
      },
      onAutoClose: () => {
        if (notice?.id === current.id) notice = null;
      },
    });
  });
  onDestroy(() => {
    clearForm();
    toast.dismiss('password-change');
  });

  function showError(notice: UiMessage) {
    // Store a translation key so an open toast follows locale changes.
    formNotice('error', notice);
  }
  function formNotice(type: 'success' | 'error', message: UiMessage) {
    notice = { id: nextNoticeId++, type, message };
  }
  async function submit(event: SubmitEvent) {
    event.preventDefault();
    if (!active || busy) return;
    const submitted = values();
    const localErrors = validatePasswordChange(submitted);
    errors = localErrors;
    if (Object.keys(localErrors).length) {
      showError(Object.values(localErrors)[0]!);
      document.getElementById(ids[Object.keys(localErrors)[0] as PasswordChangeField])?.focus();
      return;
    }
    const generation = ++formGeneration;
    aborter = new AbortController();
    busy = true;
    let focusAfterResponse: PasswordChangeField | undefined;
    try {
      await changePassword(csrfToken, submitted, aborter.signal);
      if (generation !== formGeneration || !active) return;
      resetPasswordFields();
      errors = {};
      formNotice('success', message('account.password.success'));
    } catch (error) {
      if (generation !== formGeneration || !active) return;
      resetPasswordFields();
      errors = error instanceof PasswordChangeApiError ? error.fieldErrors : {};
      if (error instanceof PasswordChangeApiError && error.status === 401) {
        notice = null;
        onexpired(error.uiMessage);
        return;
      }
      focusAfterResponse = Object.keys(errors)[0] as PasswordChangeField | undefined;
      showError(
        error instanceof PasswordChangeApiError
          ? error.uiMessage
          : message('account.password.errors.unavailable'),
      );
    } finally {
      if (generation === formGeneration) {
        busy = false;
        aborter = undefined;
        if (focusAfterResponse) {
          await tick();
          if (generation === formGeneration && active) {
            document.getElementById(ids[focusAfterResponse])?.focus();
          }
        }
      }
    }
  }
</script>

<section class="password-settings" aria-labelledby="password-change-title">
  <h3 id="password-change-title">{$i18n.t('account.password.title')}</h3>
  <p class="help">{$i18n.t('account.password.help')}</p>
  <form onsubmit={submit} novalidate>
    <div class="field">
      <label for={ids.current_password}>{$i18n.t('account.password.current')}</label>
      <PasswordField
        id={ids.current_password}
        bind:value={currentPassword}
        autocomplete="current-password"
        disabled={busy}
        invalid={Boolean(errors.current_password)}
        describedby={errors.current_password ? `${ids.current_password}-error` : undefined}
        resetKey={fieldResetKey}
        toggleLabel="account.password.showCurrent"
        toggleHideLabel="account.password.hideCurrent"
      />
      {#if errors.current_password}<span
          class="field-error"
          id={`${ids.current_password}-error`}
          role="alert">{$i18n.message(errors.current_password)}</span
        >{/if}
    </div>
    <div class="field">
      <label for={ids.new_password}>{$i18n.t('account.password.new')}</label>
      <PasswordField
        id={ids.new_password}
        bind:value={newPassword}
        autocomplete="new-password"
        disabled={busy}
        invalid={Boolean(errors.new_password)}
        describedby={errors.new_password ? `${ids.new_password}-error` : undefined}
        resetKey={fieldResetKey}
        toggleLabel="account.password.showNew"
        toggleHideLabel="account.password.hideNew"
      />
      {#if errors.new_password}<span
          class="field-error"
          id={`${ids.new_password}-error`}
          role="alert">{$i18n.message(errors.new_password)}</span
        >{/if}
    </div>
    <div class="field">
      <label for={ids.password_confirmation}>{$i18n.t('account.password.confirmation')}</label>
      <PasswordField
        id={ids.password_confirmation}
        bind:value={confirmation}
        autocomplete="new-password"
        disabled={busy}
        invalid={Boolean(errors.password_confirmation)}
        describedby={errors.password_confirmation
          ? `${ids.password_confirmation}-error`
          : undefined}
        resetKey={fieldResetKey}
        toggleLabel="account.password.showConfirmation"
        toggleHideLabel="account.password.hideConfirmation"
      />
      {#if errors.password_confirmation}<span
          class="field-error"
          id={`${ids.password_confirmation}-error`}
          role="alert">{$i18n.message(errors.password_confirmation)}</span
        >{/if}
    </div>
    <button class="submit" type="submit" disabled={busy}>
      {busy ? $i18n.t('account.password.submitting') : $i18n.t('account.password.submit')}
    </button>
  </form>
</section>

<style>
  .password-settings {
    max-width: 440px;
  }
  h3 {
    margin: 0 0 8px;
    font-size: 18px;
  }
  .help {
    margin: 0 0 20px;
    color: var(--muted, #687783);
    line-height: 1.5;
  }
  form {
    display: grid;
    gap: 16px;
  }
  .field {
    display: grid;
    gap: 7px;
  }
  .field :global(.password-field) {
    width: 100%;
    min-width: 0;
  }
  .field :global(input) {
    box-sizing: border-box;
    width: 100%;
    min-height: 46px;
    padding: 11px 14px;
    border: 1px solid var(--border);
    border-radius: 10px;
    background: var(--surface);
    color: var(--ink);
    font: inherit;
    line-height: 1.4;
    transition:
      border-color 160ms ease,
      box-shadow 160ms ease;
  }
  .field :global(input:hover:not(:disabled)) {
    border-color: var(--muted);
  }
  .field :global(input:focus-visible) {
    border-color: var(--focus-color);
    outline: 2px solid var(--focus-color);
    outline-offset: 2px;
  }
  .field :global(input[aria-invalid='true']) {
    border-color: var(--error);
  }
  .field :global(input:disabled) {
    opacity: 0.65;
    cursor: wait;
  }
  .field :global(.password-toggle) {
    top: 1px;
    right: 1px;
    border-radius: 9px;
  }
  .field :global(.password-toggle:hover:not(:disabled)),
  .field :global(.password-toggle[aria-pressed='true']) {
    background: var(--soft);
  }
  .field :global(.password-toggle:focus-visible) {
    outline: 2px solid var(--focus-color);
    outline-offset: -3px;
  }
  .field :global(.password-toggle img) {
    opacity: 0.85;
  }
  :global(.workspace-shell[data-theme='dark']) .field :global(.password-toggle img) {
    filter: brightness(0) invert(1);
  }
  label {
    color: var(--ink);
    font-weight: 600;
  }
  .field-error {
    color: var(--error);
    font-size: 13px;
  }
  .submit {
    justify-self: start;
    min-height: 46px;
    padding: 11px 18px;
    border: 1px solid transparent;
    border-radius: 10px;
    background: var(--send-background);
    color: var(--send-ink);
    font: inherit;
    font-weight: 600;
    cursor: pointer;
    transition: box-shadow 160ms ease;
  }
  .submit:hover:not(:disabled) {
    background: var(--accent-hover);
  }
  .submit:active:not(:disabled) {
    box-shadow: inset 0 0 0 2px var(--border);
  }
  .submit:disabled {
    opacity: 0.65;
    cursor: wait;
  }
  .submit:focus-visible {
    outline: 2px solid var(--focus-color, var(--accent));
    outline-offset: 2px;
  }
  @media (prefers-reduced-motion: reduce) {
    .field :global(input),
    .submit {
      transition: none;
    }
  }
</style>
