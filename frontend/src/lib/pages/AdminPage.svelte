<script lang="ts">
  import { onDestroy, untrack, type Snippet } from 'svelte';
  import { i18n } from '../i18n/index.ts';
  import AccountsPanel from '../features/admin/AccountsPanel.svelte';
  import { createAdminState } from '../features/admin/admin-state.svelte.ts';
  let {
    csrfToken,
    onexpired,
    onforbidden,
    view = 'admin-users',
    onselect = async () => {},
    settings,
    active = true,
  }: {
    csrfToken: string;
    onexpired: () => void;
    onforbidden: () => void;
    view?: 'admin-users' | 'admin-settings';
    onselect?: (view: 'admin-users' | 'admin-settings') => Promise<void>;
    settings?: Snippet;
    active?: boolean;
  } = $props();
  // The session owner mounts one page per actor; disposal invalidates all late responses.
  const state = untrack(() => createAdminState({ csrfToken, onexpired, onforbidden }));
  onDestroy(state.dispose);
  const tabs = [
    { id: 'users', view: 'admin-users', label: 'admin.users' },
    { id: 'setting', view: 'admin-settings', label: 'admin.systemSettings' },
  ] as const;
  /** Select an admin view with the keyboard; the workspace revalidates access first. */
  async function tabKey(event: KeyboardEvent) {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const index = tabs.findIndex((tab) => tab.view === view);
    const next =
      event.key === 'Home'
        ? tabs[0]
        : event.key === 'End'
          ? tabs[tabs.length - 1]
          : tabs[(index + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length];
    await onselect(next.view);
    document.getElementById('admin-tab-' + next.id)?.focus();
  }
</script>

<section class="admin-panel" aria-label={$i18n.t('admin.navigation')}>
  <div class="admin-tabs" role="tablist" aria-label={$i18n.t('admin.navigation')}>
    {#each tabs as tab (tab.id)}
      <button
        id={'admin-tab-' + tab.id}
        type="button"
        role="tab"
        aria-selected={view === tab.view}
        aria-controls={'admin-panel-' + tab.id}
        tabindex={view === tab.view ? 0 : -1}
        onkeydown={tabKey}
        onclick={() => onselect(tab.view)}>{$i18n.t(tab.label)}</button
      >
    {/each}
  </div>
  <div
    id="admin-panel-users"
    role="tabpanel"
    aria-labelledby="admin-tab-users"
    hidden={view !== 'admin-users'}
  >
    {#if view === 'admin-users'}<AccountsPanel {state} {active} />{/if}
  </div>
  <div
    id="admin-panel-setting"
    role="tabpanel"
    aria-labelledby="admin-tab-setting"
    hidden={view !== 'admin-settings'}
  >
    {#if view === 'admin-settings'}{@render settings?.()}{/if}
  </div>
</section>

<style>
  .admin-panel {
    display: flex;
    flex-direction: column;
    width: 100%;
    min-height: 100%;
    min-width: 0;
    color: var(--ink);
  }
  .admin-tabs {
    display: flex;
    flex: none;
    gap: 8px;
    padding: 0 clamp(16px, 3vw, 32px);
    border-bottom: 1px solid var(--border);
  }
  .admin-tabs button {
    min-height: 44px;
    padding: 10px 16px;
    border: 0;
    border-bottom: 2px solid transparent;
    background: transparent;
    color: var(--muted);
    font: inherit;
    cursor: pointer;
  }
  .admin-tabs button:hover {
    background: var(--soft);
    color: var(--ink);
  }
  .admin-tabs button[aria-selected='true'] {
    border-bottom-color: var(--ink);
    color: var(--ink);
    font-weight: 600;
  }
  .admin-tabs button:focus-visible {
    outline: 2px solid var(--ink);
    outline-offset: -4px;
  }
  #admin-panel-setting:not([hidden]) {
    display: flex;
    flex: 1;
  }
</style>
