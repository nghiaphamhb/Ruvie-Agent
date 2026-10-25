<script lang="ts">
  import { onDestroy, onMount, tick, untrack } from 'svelte';
  import { i18n } from '../../i18n/index.ts';
  import { toast } from 'svelte-sonner';
  import type { AccountSummary } from './admin-api.ts';
  import eyeHide from '../../assets/auth/eye-hide.svg';

  let {
    user,
    busy,
    error,
    onsave,
    onclose,
  }: {
    user: AccountSummary;
    busy: boolean;
    error: string | null;
    onsave: (
      user: AccountSummary,
      changes: {
        display_name?: string;
        email?: string;
        system_role?: 'user' | 'admin';
        password?: string;
      },
    ) => Promise<AccountSummary | null>;
    onclose: () => void;
  } = $props();
  let dialog: HTMLElement;
  let visiblePassword = $state(false);
  let currentUser = $state(untrack(() => user));
  let displayName = $state(untrack(() => user.display_name));
  let email = $state(untrack(() => user.email));
  let role = $state(untrack(() => user.system_role));
  let password = $state('');
  let previousOverflow = '';
  const hasChanges = $derived(
    displayName.trim() !== currentUser.display_name ||
      email.trim().toLowerCase() !== currentUser.email.toLowerCase() ||
      role !== currentUser.system_role ||
      password.length > 0,
  );

  onMount(async () => {
    previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    await tick();
    dialog.querySelector<HTMLInputElement>('[name="display_name"]')?.focus();
  });
  onDestroy(() => {
    document.body.style.overflow = previousOverflow;
    password = '';
  });

  function closeOnEscape(event: KeyboardEvent) {
    if (event.defaultPrevented) return;
    if (event.key === 'Escape') {
      // Let the native Role picker consume Escape before dismissing the enclosing modal.
      if (
        CSS.supports('appearance', 'base-select') &&
        dialog.querySelector('select')?.matches(':open')
      )
        return;
      if (busy) return;
      event.preventDefault();
      onclose();
      return;
    }
    if (event.key !== 'Tab') return;
    const focusable = [
      ...dialog.querySelectorAll<HTMLElement>(
        'button:not(:disabled), input:not(:disabled), select:not(:disabled), [tabindex]:not([tabindex="-1"])',
      ),
    ];
    const first = focusable[0];
    const last = focusable.at(-1);
    if (!first || !last) return;
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  function close() {
    if (!busy) onclose();
  }

  function initials(name: string) {
    return name
      .trim()
      .split(/\s+/)
      .slice(0, 2)
      .map((part) => part[0])
      .join('')
      .toLocaleUpperCase();
  }

  async function save(event: SubmitEvent) {
    event.preventDefault();
    const changes: {
      display_name?: string;
      email?: string;
      system_role?: 'user' | 'admin';
      password?: string;
    } = {};
    if (displayName.trim() !== currentUser.display_name) changes.display_name = displayName.trim();
    if (email.trim().toLowerCase() !== currentUser.email.toLowerCase())
      changes.email = email.trim().toLowerCase();
    if (role !== currentUser.system_role) changes.system_role = role;
    if (password.length) changes.password = password;
    if (!Object.keys(changes).length || busy) return;
    const updated = await onsave(currentUser, changes);
    if (!updated) return;
    currentUser = updated;
    displayName = updated.display_name;
    email = updated.email;
    password = '';
    window.dispatchEvent(
      new CustomEvent('ruvie:account-updated', {
        detail: { ...updated, password_changed: changes.password !== undefined },
      }),
    );
    if (changes.password !== undefined) password = '';
    toast.success(
      $i18n.t(changes.password !== undefined ? 'admin.passwordUpdated' : 'admin.userUpdated'),
    );
  }
</script>

<div
  class="backdrop"
  data-edit-user-backdrop
  role="presentation"
  onclick={(event) => {
    if (event.target === event.currentTarget) close();
  }}
>
  <div
    bind:this={dialog}
    class="dialog"
    role="dialog"
    aria-modal="true"
    aria-labelledby="edit-user-title"
    onkeydown={closeOnEscape}
    tabindex="-1"
  >
    <header>
      <h2 id="edit-user-title">{$i18n.t('admin.editTitle')}</h2>
      <button
        class="close"
        type="button"
        aria-label={$i18n.t('ux.close')}
        onclick={close}
        disabled={busy}>×</button
      >
    </header>
    <div class="identity">
      <div class="avatar" aria-hidden="true">{initials(currentUser.display_name)}</div>
      <div class="identity-text">
        <strong>{currentUser.display_name}</strong>
        <span
          >{$i18n.t('admin.createdAt')}
          {new Date(currentUser.created_at).toLocaleDateString($i18n.locale)}</span
        >
      </div>
    </div>
    <form onsubmit={save}>
      <label>
        <span>{$i18n.t('auth.name')}</span>
        <input
          name="display_name"
          bind:value={displayName}
          autocomplete="off"
          required
          disabled={busy}
        />
      </label>
      <label>
        <span>{$i18n.t('auth.email')}</span>
        <input type="email" bind:value={email} autocomplete="off" required disabled={busy} />
      </label>
      <label>
        <span>{$i18n.t('admin.role')}</span>
        <select bind:value={role} disabled={busy}>
          <option value="user">{$i18n.t('admin.roleUser')}</option>
          <option value="admin">{$i18n.t('admin.roleAdmin')}</option>
        </select>
      </label>
      <label>
        <span>{$i18n.t('admin.newPassword')}</span>
        <span class="password-field">
          <input
            type={visiblePassword ? 'text' : 'password'}
            bind:value={password}
            autocomplete="new-password"
            placeholder={$i18n.t('admin.passwordPlaceholder')}
            minlength="12"
            maxlength="128"
            disabled={busy}
          />
          <button
            type="button"
            class="toggle-password"
            aria-label={$i18n.t(visiblePassword ? 'admin.hidePassword' : 'admin.showPassword')}
            aria-pressed={visiblePassword}
            disabled={busy}
            onclick={() => (visiblePassword = !visiblePassword)}
            ><img src={eyeHide} alt="" /></button
          >
        </span>
      </label>
      <footer>
        <button type="button" disabled={busy} onclick={close}>{$i18n.t('admin.cancel')}</button>
        <button type="submit" class="save" disabled={!hasChanges || busy}>
          {$i18n.t(busy ? 'admin.busy' : 'admin.save')}
        </button>
      </footer>
    </form>
    {#if error}
      <p role="alert">
        {$i18n.t(
          error === 'account_not_found'
            ? 'admin.errors.account_not_found'
            : error === 'last_active_admin'
              ? 'admin.errors.last_active_admin'
              : error === 'account_update_unavailable'
                ? 'admin.errors.account_update_unavailable'
                : error === 'email_taken'
                  ? 'admin.errors.email_taken'
                  : error === 'validation_error'
                    ? 'admin.errors.validation_error'
                    : 'admin.errors.unknown',
        )}
      </p>
    {/if}
  </div>
</div>

<style>
  .backdrop {
    position: fixed;
    z-index: 1000;
    inset: 0;
    display: grid;
    place-items: center;
    padding: 1rem;
    background: #010c1dcc;
    backdrop-filter: blur(4px);
  }
  .dialog {
    width: min(30rem, 100%);
    max-height: min(90dvh, 48rem);
    overflow-y: auto;
    padding: 24px;
    border: 1px solid var(--border);
    border-radius: 16px;
    background: var(--surface);
    color: var(--ink);
    box-shadow: 0 24px 80px rgb(0 0 0 / 35%);
  }
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    min-height: 44px;
  }
  h2 {
    margin: 0;
    font-size: 20px;
  }
  button,
  input,
  select {
    font: inherit;
    color: inherit;
  }
  button {
    min-width: 44px;
    min-height: 44px;
    border: 1px solid var(--border);
    border-radius: 0.65rem;
    background: var(--surface);
    cursor: pointer;
  }
  button:focus-visible,
  input:focus-visible,
  select:focus-visible {
    outline: 2px solid var(--ink);
    outline-offset: 2px;
  }
  button:disabled {
    cursor: not-allowed;
    opacity: 0.55;
  }
  .close {
    border: 0;
    font-size: 1.5rem;
    line-height: 1;
    background: transparent;
  }
  .identity {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 16px 0 20px;
  }
  .avatar {
    display: grid;
    flex: 0 0 44px;
    width: 44px;
    height: 44px;
    place-items: center;
    border-radius: 50%;
    background: var(--ink);
    color: var(--surface);
    font-size: 1.25rem;
  }
  .identity-text {
    display: grid;
    min-width: 0;
    gap: 0.2rem;
  }
  .identity-text strong {
    overflow-wrap: anywhere;
  }
  .identity-text span {
    color: var(--muted);
    font-size: 0.8rem;
  }
  form {
    display: grid;
    gap: 0.75rem;
  }
  label {
    display: grid;
    gap: 0.3rem;
    font-size: 14px;
    font-weight: 500;
  }
  label > span:first-child {
    color: var(--muted);
  }
  input,
  select {
    box-sizing: border-box;
    width: 100%;
    min-height: 44px;
    padding: 0.65rem 0.75rem;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: transparent;
  }
  .password-field {
    position: relative;
  }
  .password-field input {
    min-width: 0;
    padding-right: 52px;
  }
  .toggle-password {
    position: absolute;
    top: 0;
    right: 0;
    border: 0;
    display: grid;
    place-items: center;
    width: 44px;
    height: 44px;
    background: transparent;
  }
  .toggle-password img {
    filter: brightness(0);
    opacity: 0.6;
  }
  :global(.workspace-shell[data-theme='dark']) .toggle-password img {
    filter: brightness(0) invert(1);
  }
  footer {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    padding-top: 12px;
  }
  .save {
    min-width: 6rem;
    border-radius: 8px;
    border-color: var(--ink);
    background: var(--ink);
    color: var(--surface);
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
