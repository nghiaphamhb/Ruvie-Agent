<script lang="ts">
  import { onDestroy, onMount, tick } from 'svelte';
  import { i18n } from '../../i18n/index.ts';
  import PasswordField from '../auth/PasswordField.svelte';
  import {
    validateAccount,
    type AccountFieldErrors,
    type AccountInput,
    type AccountRole,
  } from './admin-form.ts';

  let {
    busy,
    uncertain,
    fieldErrors,
    oncreate,
    oncancel,
    embedded = false,
  }: {
    busy: boolean;
    uncertain: boolean;
    fieldErrors: AccountFieldErrors;
    oncreate: (input: AccountInput) => Promise<boolean>;
    oncancel: () => void;
    embedded?: boolean;
  } = $props();
  let name = $state(''),
    email = $state(''),
    password = $state('');
  let role = $state<AccountRole>('user');
  let localErrors = $state<AccountFieldErrors>({});
  let form: HTMLFormElement;
  let active = true;
  const fields = $derived({ ...fieldErrors, ...localErrors });
  onMount(() => form.querySelector<HTMLInputElement>('[name="display_name"]')?.focus());
  onDestroy(() => {
    active = false;
    password = '';
  });

  async function focusError(errors: AccountFieldErrors) {
    const first = ['display_name', 'email', 'password', 'system_role'].find(
      (field) => field in errors,
    );
    await tick();
    if (active && first) {
      const selector = first === 'password' ? '#admin-password' : `[name="${first}"]`;
      form.querySelector<HTMLElement>(selector)?.focus();
    }
  }
  /** Password belongs only to this form and the single in-flight request. */
  async function submit(event: SubmitEvent) {
    event.preventDefault();
    if (busy || uncertain) return;
    localErrors = validateAccount(name, email, password, role);
    if (Object.keys(localErrors).length) {
      await focusError(localErrors);
      return;
    }
    let succeeded: boolean;
    try {
      succeeded = await oncreate({ display_name: name, email, password, system_role: role });
    } finally {
      password = '';
    }
    // The state owner publishes server errors before Svelte updates this prop.
    await tick();
    if (!succeeded && active) await focusError(fieldErrors);
  }
</script>

<svelte:window
  onkeydown={(event) => {
    if (
      event.key === 'Escape' &&
      !busy &&
      !event.defaultPrevented &&
      !document.querySelector('dialog[open]')
    ) {
      event.preventDefault();
      oncancel();
    }
  }}
/>

<form
  bind:this={form}
  class:embedded
  aria-label={$i18n.t('admin.create')}
  aria-busy={busy}
  novalidate
  onsubmit={submit}
  oninput={() => {
    localErrors = {};
  }}
>
  {#if !embedded}<h2>{$i18n.t('admin.create')}</h2>{/if}
  <fieldset disabled={busy}>
    <label for="admin-name">{$i18n.t('auth.name')}</label>
    <input
      id="admin-name"
      name="display_name"
      data-dialog-initial-focus
      autocomplete="name"
      required
      bind:value={name}
      aria-invalid={Boolean(fields.display_name)}
      aria-describedby={fields.display_name ? 'admin-name-error' : undefined}
    />
    {#if fields.display_name}<p id="admin-name-error" class="field-error" role="alert">
        {$i18n.message(fields.display_name)}
      </p>{/if}
    <label for="admin-email">{$i18n.t('auth.email')}</label>
    <input
      id="admin-email"
      name="email"
      type="email"
      autocomplete="email"
      required
      bind:value={email}
      aria-invalid={Boolean(fields.email)}
      aria-describedby={fields.email ? 'admin-email-error' : undefined}
    />
    {#if fields.email}<p id="admin-email-error" class="field-error" role="alert">
        {$i18n.message(fields.email)}
      </p>{/if}
    <label for="admin-role">{$i18n.t('admin.role')}</label>
    <select
      id="admin-role"
      name="system_role"
      bind:value={role}
      aria-invalid={Boolean(fields.system_role)}
      aria-describedby={fields.system_role ? 'admin-role-help admin-role-error' : 'admin-role-help'}
    >
      <option value="user">{$i18n.t('admin.roleUser')}</option><option value="admin"
        >{$i18n.t('admin.roleAdmin')}</option
      >
    </select>
    <p id="admin-role-help">
      {$i18n.t('admin.roleHelp')}
    </p>
    {#if fields.system_role}<p id="admin-role-error" class="field-error" role="alert">
        {$i18n.message(fields.system_role)}
      </p>{/if}
    <label for="admin-password">{$i18n.t('admin.initialPassword')}</label>
    <PasswordField
      id="admin-password"
      bind:value={password}
      disabled={busy}
      autocomplete="new-password"
      invalid={Boolean(fields.password)}
      describedby={fields.password ? 'admin-password-error' : undefined}
    />
    {#if fields.password}<p id="admin-password-error" class="field-error" role="alert">
        {$i18n.message(fields.password)}
      </p>{/if}
    <div class="actions">
      <button type="button" onclick={oncancel}>{$i18n.t('admin.cancel')}</button>
      <button type="submit" class="primary" disabled={uncertain}
        >{$i18n.t(busy ? 'admin.busy' : 'admin.create')}</button
      >
    </div>
  </fieldset>
</form>

<style>
  form {
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.25rem;
    background: var(--surface);
  }
  form.embedded {
    border: 0;
    padding: 0;
    background: transparent;
  }
  h2 {
    margin: 0 0 1rem;
    font-size: 1.2rem;
  }
  fieldset {
    border: 0;
    padding: 0;
    margin: 0;
    display: grid;
    gap: 0.65rem;
    min-width: 0;
  }
  input,
  select,
  button,
  form :global(.password-field input) {
    font: inherit;
    color: var(--ink);
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 0.5rem;
    padding: 0.65rem 0.75rem;
    min-height: 44px;
    max-width: 100%;
  }
  input,
  select,
  form :global(.password-field input) {
    width: 100%;
    box-sizing: border-box;
  }
  .field-error {
    color: var(--error);
  }
  :global(.workspace-shell[data-theme='dark']) form :global(.password-toggle img) {
    filter: brightness(0) invert(1);
  }
  label {
    margin-top: 0.4rem;
    font-size: 14px;
    font-weight: 500;
    color: var(--muted);
  }
  p {
    margin: 0;
    line-height: 1.5;
    font-size: 13px;
    color: var(--muted);
  }
  .actions {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 0.75rem;
    margin-top: 1.25rem;
  }
  .primary {
    background: var(--ink);
    color: var(--surface);
    border-color: var(--ink);
  }
  button {
    cursor: pointer;
  }
  button:disabled {
    opacity: 0.6;
    cursor: default;
  }
  :focus-visible,
  form :global(.password-field input:focus-visible) {
    outline: 2px solid var(--ink);
    outline-offset: 3px;
  }
  select {
    background: var(--surface);
    color-scheme: var(--control-color-scheme, light);
  }
  option {
    background: var(--surface);
    color: var(--ink);
  }
  option:checked {
    background: var(--soft);
  }
  @supports (appearance: base-select) {
    select,
    select::picker(select) {
      appearance: base-select;
    }
    select::picker(select) {
      margin-top: 6px;
      position-area: block-end span-inline-end;
      position-try-order: normal;
      padding: 4px;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: var(--surface);
      color: var(--ink);
      box-shadow: 0 12px 28px #0004;
    }
    option {
      min-height: 40px;
      padding: 8px 12px;
      border-radius: 4px;
      cursor: pointer;
    }
    option:hover,
    option:focus-visible,
    option:checked {
      background: var(--soft);
      color: var(--ink);
    }
    option::checkmark {
      display: none;
    }
    select::picker-icon {
      color: var(--muted);
    }
  }
</style>
