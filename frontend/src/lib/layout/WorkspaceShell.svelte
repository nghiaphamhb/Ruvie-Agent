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
  let sidebarWidth = $state(264);
  let resizing = $state(false);
  let startX = 0;
  let startWidth = 264;
  function setWidth(value: number) {
    sidebarWidth = Math.round(Math.max(220, Math.min(480, window.innerWidth - 320, value)));
  }
  /** Capture the pointer so releasing outside the divider always ends resizing. */
  function startResize(event: PointerEvent) {
    if (event.button !== 0) return;
    event.preventDefault();
    startX = event.clientX;
    startWidth = sidebarWidth;
    resizing = true;
    (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
  }
  function resizeKey(event: KeyboardEvent) {
    const values: Record<string, number> = {
      ArrowLeft: sidebarWidth - 16,
      ArrowRight: sidebarWidth + 16,
      Home: 220,
      End: 480,
    };
    if (event.key in values) {
      event.preventDefault();
      setWidth(values[event.key]);
    }
  }
</script>

<div
  class="workspace workspace-shell"
  data-theme={theme}
  class:collapsed
  class:resizing
  style:--expanded-sidebar-width={`${sidebarWidth}px`}
>
  <a class="skip-link" href="#workspace-main">{$i18n.t('workspace.skip')}</a>
  <aside class="workspace-sidebar" aria-label={$i18n.t('workspace.sidebar')}>
    {@render sidebar()}
  </aside>
  {#if !collapsed}
    <!-- A focusable ARIA window splitter supports keyboard resizing. -->
    <!-- svelte-ignore a11y_no_noninteractive_tabindex, a11y_no_noninteractive_element_interactions -->
    <div
      class="sidebar-resizer"
      role="separator"
      tabindex="0"
      aria-label={$i18n.t('workspace.resizeSidebar')}
      aria-orientation="vertical"
      aria-valuemin="220"
      aria-valuemax="480"
      aria-valuenow={sidebarWidth}
      onpointerdown={startResize}
      onpointermove={(event) => {
        if (resizing) setWidth(startWidth + event.clientX - startX);
      }}
      onpointerup={() => {
        resizing = false;
      }}
      onpointercancel={() => {
        resizing = false;
      }}
      onlostpointercapture={() => {
        resizing = false;
      }}
      onkeydown={resizeKey}
    ></div>
  {/if}
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
