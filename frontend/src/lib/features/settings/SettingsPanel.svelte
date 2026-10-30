<script lang="ts">
  import { type Snippet } from 'svelte';
  import { i18n } from '../../i18n/index.ts';
  import ThemeSelector from './ThemeSelector.svelte';
  import type { createThemeState } from './theme.ts';
  import LanguageSelector from '../../shared/LanguageSelector.svelte';
  import ChangePasswordForm from './ChangePasswordForm.svelte';
  import type { UiMessage } from '../../i18n/messages.ts';
  let {
    theme,
    system = false,
    csrfToken = '',
    active = false,
    onexpired = () => {},
    children,
    connection = $bindable<'reply' | 'embedding'>('reply'),
  }: {
    theme: ReturnType<typeof createThemeState>;
    system?: boolean;
    csrfToken?: string;
    active?: boolean;
    onexpired?: (notice: UiMessage) => void;
    children?: Snippet;
    connection?: 'reply' | 'embedding';
  } = $props();
  const prefix = $derived(system ? 'admin-' : '');
  let selected = $state<'appearance' | 'account'>('appearance');
  const heading = $derived(system ? 'admin.systemSettings' : 'workspace.settings');
  function chooseTab(next: 'appearance' | 'account', focus = false) {
    if (system && next === 'account') return;
    selected = next;
    if (focus) document.getElementById(`settings-tab-${next}`)?.focus();
  }
  let connectionsOpen = $state(true);
  $effect(() => {
    if (active && system) connection = 'reply';
  });
  function onTabKeydown(event: KeyboardEvent) {
    if (system) {
      if (!connectionsOpen) return;
      let next: 'reply' | 'embedding';
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp')
        next = connection === 'reply' ? 'embedding' : 'reply';
      else if (event.key === 'Home') next = 'reply';
      else if (event.key === 'End') next = 'embedding';
      else return;
      event.preventDefault();
      connection = next;
      document.getElementById('admin-settings-tab-' + next)?.focus();
      return;
    }
    const order = ['appearance', 'account'] as const;
    const index = order.indexOf(selected);
    let next: number;
    if (event.key === 'ArrowDown') next = (index + 1) % order.length;
    else if (event.key === 'ArrowUp') next = (index + order.length - 1) % order.length;
    else if (event.key === 'Home') next = 0;
    else if (event.key === 'End') next = order.length - 1;
    else return;
    event.preventDefault();
    chooseTab(order[next]!, true);
  }
</script>

<section
  class="settings-embedded"
  class:system-settings={system}
  aria-labelledby={prefix + 'settings-heading'}
>
  <header class:visually-hidden={system}>
    <h2 id={prefix + 'settings-heading'} data-view-heading tabindex="-1">
      {$i18n.t(heading)}
    </h2>
  </header>
  <div class="settings-layout">
    <div
      class="settings-tabs"
      role="tablist"
      tabindex="-1"
      aria-label={$i18n.t(heading)}
      aria-orientation="vertical"
      onkeydown={onTabKeydown}
    >
      {#if system}
        <button
          type="button"
          aria-expanded={connectionsOpen}
          aria-controls="ai-connection-tabs"
          onclick={() => (connectionsOpen = !connectionsOpen)}>{$i18n.t('ai.connections')}</button
        >
        <div id="ai-connection-tabs" hidden={!connectionsOpen}>
          {#each ['reply', 'embedding'] as child (child)}
            <button
              class="connection-child"
              type="button"
              role="tab"
              id={'admin-settings-tab-' + child}
              aria-selected={connection === child}
              aria-controls="admin-settings-llm"
              tabindex={connection === child ? 0 : -1}
              onclick={() => (connection = child as 'reply' | 'embedding')}
              >{$i18n.t(child === 'reply' ? 'ai.reply' : 'embedding.heading')}</button
            >
          {/each}
        </div>
      {:else}
        <button
          id={prefix + 'settings-tab-' + (system ? 'llm' : 'appearance')}
          type="button"
          role="tab"
          aria-selected={system || selected === 'appearance'}
          aria-controls={prefix + 'settings-' + (system ? 'llm' : 'appearance')}
          tabindex={selected === 'appearance' || system ? 0 : -1}
          onclick={() => chooseTab('appearance')}
        >
          <span>{$i18n.t(system ? 'nav.llm' : 'theme.display')}</span>
        </button>
      {/if}
      {#if !system}
        <button
          id="settings-tab-account"
          type="button"
          role="tab"
          aria-selected={selected === 'account'}
          aria-controls="settings-account"
          tabindex={selected === 'account' ? 0 : -1}
          onclick={() => chooseTab('account')}
        >
          <span>{$i18n.t('settings.account')}</span>
        </button>
      {/if}
    </div>
    {#if system}
      <div
        id="admin-settings-llm"
        role="tabpanel"
        tabindex="0"
        aria-labelledby={'admin-settings-tab-' + connection}
      >
        {@render children?.()}
      </div>
    {:else}
      <div
        id="settings-appearance"
        role="tabpanel"
        tabindex="0"
        aria-labelledby="settings-tab-appearance"
        hidden={selected !== 'appearance'}
      >
        <ThemeSelector {theme} />
        <div class="language-setting">
          <label for="account-language">{$i18n.t('language.label')}</label>
          <LanguageSelector id="account-language" />
        </div>
      </div>
      <div
        id="settings-account"
        role="tabpanel"
        tabindex="0"
        aria-labelledby="settings-tab-account"
        hidden={selected !== 'account'}
      >
        {#if active && selected === 'account'}
          <ChangePasswordForm {csrfToken} {active} {onexpired} />
        {/if}
      </div>
    {/if}
  </div>
</section>

<style>
  .visually-hidden {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: 0;
    overflow: hidden;
    clip-path: inset(50%);
  }
  .settings-embedded {
    --radius: 12px;
    --settings-accent: #258dff;
    display: flex;
    flex: 1;
    flex-direction: column;
    min-width: 0;
    min-height: 100%;
    padding: clamp(16px, 2.5vw, 32px);
    color: var(--ink);
  }
  header {
    flex: none;
    margin: 0 0 20px;
  }
  h2 {
    margin: 0;
    font-size: 24px;
    line-height: 1.25;
  }
  .settings-layout {
    display: grid;
    flex: 1;
    grid-template-columns: 220px minmax(0, 1fr);
    align-items: stretch;
    gap: 16px;
  }
  .settings-tabs {
    display: flex;
    flex-direction: column;
    padding: 8px;
    border-left: 1px solid var(--border);
    background: transparent;
  }
  .settings-tabs .connection-child {
    margin-left: 18px;
    width: calc(100% - 18px);
  }
  .settings-tabs button {
    position: relative;
    display: flex;
    align-items: center;
    gap: 12px;
    min-height: 46px;
    padding: 11px 14px;
    border: 0;
    border-radius: 4px;
    background: transparent;
    color: var(--ink);
    text-align: left;
    font: inherit;
    font-weight: 500;
    cursor: pointer;
  }
  /* Preview only the hovered tab; restore the selected tab when the pointer leaves. */
  .settings-tabs:not(:has(button:hover)) button[aria-selected='true'],
  .settings-tabs button:hover {
    background: var(--soft);
  }
  .settings-tabs:not(:has(button:hover)) button[aria-selected='true']::before,
  .settings-tabs button:hover::before {
    position: absolute;
    inset: 0 auto 0 -8px;
    width: 3px;
    border-radius: 2px;
    background: var(--settings-accent);
    content: '';
  }
  button:focus-visible {
    outline: 2px solid var(--focus-color, var(--accent));
    outline-offset: 2px;
  }
  [role='tabpanel'] {
    align-self: start;
    min-width: 0;
    max-width: 760px;
    padding: 24px;
    border: 0;
    background: transparent;
  }
  #settings-appearance {
    display: grid;
    gap: 16px;
  }
  .language-setting {
    max-width: 360px;
    margin-top: 24px;
  }
  .language-setting > label {
    display: block;
    margin-bottom: 12px;
    font-weight: 600;
  }
  :global(.settings-embedded .llm-panel) {
    width: 100%;
    margin: 0;
    padding: 0;
    border: 0;
    background: transparent;
  }
  .system-settings .settings-tabs button {
    border-radius: 2px;
  }
  #ai-connection-tabs {
    position: relative;
    margin-left: 18px;
    padding-left: 10px;
    border-left: 1px solid var(--border);
  }
  #ai-connection-tabs::after {
    position: absolute;
    left: -1px;
    bottom: 0;
    width: 10px;
    border-bottom: 1px solid var(--border);
    content: '';
  }
  .settings-tabs #ai-connection-tabs .connection-child {
    margin-left: 0;
    width: 100%;
  }
  .system-settings .settings-tabs button[aria-expanded] {
    background: transparent;
  }
  @media (max-width: 640px) {
    .settings-layout {
      grid-template-columns: minmax(0, 1fr);
      grid-template-rows: auto 1fr;
      gap: 16px;
    }
    [role='tabpanel'] {
      padding: 8px 0;
    }
  }
</style>
