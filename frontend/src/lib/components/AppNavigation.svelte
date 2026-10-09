<script lang="ts">
  import { i18n } from '../i18n/index.ts';
  import LanguageSelector from './LanguageSelector.svelte';
  // Ported from references/src/lib/components/layout/Sidebar.svelte:
  // brand above navigation, rounded rows, account actions at the bottom.
  let { activeView, accountName, busy, onselect, onlogout }: {
    activeView: 'chat' | 'documents' | 'llm';
    accountName: string;
    busy: boolean;
    onselect: (view: 'chat' | 'documents' | 'llm') => void;
    onlogout: () => void;
  } = $props();
  const items = [
    { id: 'chat', label: 'nav.chat' },
    { id: 'documents', label: 'nav.documents' },
    { id: 'llm', label: 'nav.llm' }
  ] as const;
</script>

<aside class="sidebar">
  <div class="brand"><span class="brand-mark" aria-hidden="true">R</span><span>Ruvie Agent</span></div>
  <nav aria-label={$i18n.t('nav.main')}>
    {#each items as item (item.id)}
      <button type="button" aria-current={activeView === item.id ? 'page' : undefined}
        onclick={() => onselect(item.id)}>{$i18n.t(item.label)}</button>
    {/each}
  </nav>
  <div class="account">
    <LanguageSelector id="account-language" />
    <span class="account-name">{accountName}</span>
    <button type="button" onclick={onlogout} disabled={busy}>{$i18n.t('auth.logout')}</button>
  </div>
</aside>

<style>
  .sidebar { min-width: 0; display: flex; flex-direction: column; min-height: 0; overflow-y: auto; padding: calc(2 * var(--space)) calc(1.5 * var(--space)); background: var(--paper); background-image: var(--paper-gradient); border-right: 1px solid var(--border); }
  .brand { padding: 8px; margin-bottom: 28px; }
  nav { display: grid; gap: 4px; }
  button { width: 100%; min-height: 44px; padding: 10px 14px; text-align: left; border: 0; border-radius: var(--radius); background: transparent; color: var(--ink); }
  button:hover { background: var(--soft); }
  button[aria-current="page"] { background: var(--soft); font-weight: 650; }
  .account { margin-top: auto; padding-top: 24px; }
  .account-name { display: block; padding: 10px 14px; overflow-wrap: anywhere; font-weight: 600; }
</style>
