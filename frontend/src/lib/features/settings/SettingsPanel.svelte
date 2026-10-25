<script lang="ts">
  import { type Snippet } from 'svelte';
  import { i18n } from '../../i18n/index.ts';
  import ThemeSelector from './ThemeSelector.svelte';
  import type { createThemeState } from './theme.ts';
  import LanguageSelector from '../../shared/LanguageSelector.svelte';
  let {
    theme,
    system = false,
    children,
  }: {
    theme: ReturnType<typeof createThemeState>;
    system?: boolean;
    children?: Snippet;
  } = $props();
  const prefix = $derived(system ? 'admin-' : '');
  const tab = $derived(system ? 'llm' : 'appearance');
  const heading = $derived(system ? 'admin.systemSettings' : 'workspace.settings');
</script>

<section class="settings-embedded" aria-labelledby={prefix + 'settings-heading'}>
  <header>
    <h2 id={prefix + 'settings-heading'} data-view-heading tabindex="-1">
      {$i18n.t(heading)}
    </h2>
  </header>
  <div class="settings-layout">
    <div
      class="settings-tabs"
      role="tablist"
      aria-label={$i18n.t(heading)}
      aria-orientation="vertical"
    >
      <button
        id={prefix + 'settings-tab-' + tab}
        type="button"
        role="tab"
        aria-selected="true"
        aria-controls={prefix + 'settings-' + tab}
      >
        <span>{$i18n.t(system ? 'nav.llm' : 'theme.display')}</span>
      </button>
    </div>
    <div
      id={prefix + 'settings-' + tab}
      role="tabpanel"
      tabindex="0"
      aria-labelledby={prefix + 'settings-tab-' + tab}
    >
      {#if system}
        {@render children?.()}
      {:else}
        <ThemeSelector {theme} />
        <div class="language-setting">
          <label for="account-language">{$i18n.t('language.label')}</label>
          <LanguageSelector id="account-language" />
        </div>
      {/if}
    </div>
  </div>
</section>

<style>
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
    grid-template-columns: minmax(140px, 0.32fr) minmax(0, 1fr);
    align-items: stretch;
    gap: 24px;
  }
  .settings-tabs {
    display: flex;
    flex-direction: column;
    padding: 8px;
    border-left: 1px solid var(--border);
    background: transparent;
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
  .settings-tabs button[aria-selected='true'] {
    background: var(--soft);
  }
  .settings-tabs button[aria-selected='true']::before {
    position: absolute;
    inset: 0 auto 0 -8px;
    width: 3px;
    border-radius: 2px;
    background: var(--settings-accent);
    content: '';
  }
  .settings-tabs button:hover {
    background: var(--soft);
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
    gap: 24px;
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
</style>
