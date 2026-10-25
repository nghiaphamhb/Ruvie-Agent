<script lang="ts">
  import { type Snippet } from 'svelte';
  import { i18n } from '../i18n/index.ts';
  import WorkspaceIcon from '../shared/WorkspaceIcon.svelte';
  let {
    theme = 'dark',
    collapsed,
    oncontrols,
    sidebar,
    children,
    toolbar,
  }: {
    theme?: 'light' | 'dark';
    collapsed: boolean;
    oncontrols: () => void;
    sidebar: Snippet;
    children: Snippet;
    toolbar?: Snippet;
  } = $props();
</script>

<div class="workspace workspace-shell" data-theme={theme} class:collapsed>
  <a class="skip-link" href="#workspace-main">{$i18n.t('workspace.skip')}</a>
  <aside class="workspace-sidebar" aria-label={$i18n.t('workspace.sidebar')}>
    {@render sidebar()}
  </aside>
  <main class="workspace-content" id="workspace-main" tabindex="-1">
    <header class="workspace-toolbar">
      {@render toolbar?.()}
      <button
        class="chat-controls-trigger"
        type="button"
        aria-label={$i18n.t('workspace.controls')}
        onclick={oncontrols}><WorkspaceIcon name="settings" size={24} /></button
      >
    </header>
    {@render children()}
  </main>
</div>
