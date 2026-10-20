<script lang="ts">
  import { type Snippet } from 'svelte';
  import { i18n } from '../../i18n/index.ts';
  import ThemeSelector from './ThemeSelector.svelte';
  import type { createThemeState } from './theme.ts';
  import LanguageSelector from '../../shared/LanguageSelector.svelte';
  let {
    open,
    onclose,
    children,
    theme,
    tab = $bindable('general'),
  }: {
    open: boolean;
    onclose: () => void;
    children: Snippet;
    theme: ReturnType<typeof createThemeState>;
    tab?: 'general' | 'llm' | 'appearance';
  } = $props();
  let dialog: HTMLDialogElement;
  /** Arrow/Home/End select a tab and keep focus within the tab list. */
  function tabKey(event: KeyboardEvent) {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const tabs = ['general', 'llm', 'appearance'] as const;
    const index = tabs.indexOf(tab);
    tab =
      event.key === 'Home'
        ? tabs[0]
        : event.key === 'End'
          ? tabs[2]
          : tabs[(index + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length];
    dialog.querySelector<HTMLButtonElement>('#settings-tab-' + tab)?.focus();
  }
  /** Keep Tab on operable controls in this dialog, including the last action. */
  function dialogKey(event: KeyboardEvent) {
    if (event.key !== 'Tab') return;
    const controls = [
      ...dialog.querySelectorAll<HTMLElement>('button,input,select,textarea,a[href],[tabindex]'),
    ].filter(
      (element) =>
        element.tabIndex >= 0 &&
        !element.matches(':disabled,input[type=radio]:not(:checked)') &&
        element.getClientRects().length > 0,
    );
    const first = controls[0],
      last = controls.at(-1);
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last?.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first?.focus();
    }
  }
  // Keep child form mounted, even when closed: its requests and catalog keep one owner.
  $effect(() => {
    if (open && !dialog.open) dialog.showModal();
    else if (!open && dialog.open) dialog.close();
  });
</script>

<dialog
  class="settings-dialog"
  bind:this={dialog}
  aria-labelledby="settings-heading"
  onkeydown={dialogKey}
  onclose={() => {
    if (open) onclose();
  }}
  oncancel={(event) => {
    event.preventDefault();
    onclose();
  }}
>
  <header>
    <h2 id="settings-heading">{$i18n.t('workspace.settings')}</h2>
    <button
      class="settings-close"
      type="button"
      aria-label={$i18n.t('workspace.closeSettings')}
      onclick={onclose}>×</button
    >
  </header>
  <div class="settings-tabs" role="tablist" aria-label={$i18n.t('workspace.settings')}>
    <button
      id="settings-tab-general"
      type="button"
      role="tab"
      aria-selected={tab === 'general'}
      aria-controls="settings-general"
      tabindex={tab === 'general' ? 0 : -1}
      onkeydown={tabKey}
      onclick={() => (tab = 'general')}>{$i18n.t('language.label')}</button
    >
    <button
      id="settings-tab-llm"
      type="button"
      role="tab"
      aria-selected={tab === 'llm'}
      aria-controls="settings-llm"
      tabindex={tab === 'llm' ? 0 : -1}
      onkeydown={tabKey}
      onclick={() => (tab = 'llm')}>{$i18n.t('nav.llm')}</button
    >
    <button
      id="settings-tab-appearance"
      type="button"
      role="tab"
      aria-selected={tab === 'appearance'}
      aria-controls="settings-appearance"
      tabindex={tab === 'appearance' ? 0 : -1}
      onkeydown={tabKey}
      onclick={() => (tab = 'appearance')}>{$i18n.t('theme.display')}</button
    >
  </div>
  <div
    id="settings-appearance"
    role="tabpanel"
    tabindex="0"
    aria-labelledby="settings-tab-appearance"
    hidden={tab !== 'appearance'}
  >
    <ThemeSelector {theme} />
  </div>
  <div
    id="settings-general"
    role="tabpanel"
    tabindex="0"
    aria-labelledby="settings-tab-general"
    hidden={tab !== 'general'}
  >
    <LanguageSelector id="account-language" />
  </div>
  <div
    id="settings-llm"
    role="tabpanel"
    tabindex="0"
    aria-labelledby="settings-tab-llm"
    hidden={tab !== 'llm'}
  >
    {@render children()}
  </div>
</dialog>

<style>
  dialog {
    --radius: 8px;
    color-scheme: var(--control-color-scheme, dark);
    width: min(720px, calc(100vw - 32px));
    max-height: calc(100dvh - 32px);
    padding: 24px;
    border: 1px solid var(--border);
    border-radius: 12px;
    background: var(--surface);
    color: var(--ink);
    overflow: auto;
  }
  dialog::backdrop {
    background: #010c1dcc;
    backdrop-filter: blur(4px);
  }
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }
  h2 {
    margin: 0;
    font-size: 22px;
  }
  button {
    min-height: 44px;
    padding: 10px 14px;
    border: 0;
    border-radius: var(--radius);
    background: transparent;
    color: var(--ink);
  }
  button:hover {
    background: var(--soft);
  }
  .settings-close {
    font-size: 26px;
    min-width: 44px;
  }
  .settings-tabs {
    display: flex;
    gap: 8px;
    margin: 16px 0 24px;
    flex-wrap: wrap;
  }
  .settings-tabs button[aria-selected='true'] {
    background: var(--soft);
  }
  #settings-appearance {
    padding: 12px 0;
  }
  #settings-general {
    max-width: 300px;
    padding: 8px;
  }
  :global(.settings-dialog .llm-panel) {
    width: 100%;
    margin: 0;
    padding: 0;
    border: 0;
    background: transparent;
  }
</style>
