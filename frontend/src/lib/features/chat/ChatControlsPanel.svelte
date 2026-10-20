<script lang="ts">
  import { tick } from 'svelte';
  import { i18n } from '../../i18n/index.ts';
  let { open, modelName, onclose }: { open: boolean; modelName: string; onclose: () => void } =
    $props();
  let closeButton = $state<HTMLButtonElement>();
  $effect(() => {
    if (open)
      void tick().then(() => {
        if (open) closeButton?.focus();
      });
  });
</script>

<svelte:window
  onkeydown={(event) => {
    if (open && event.key === 'Escape' && !event.defaultPrevented) onclose();
  }}
/>
{#if open}
  <aside
    class="chat-controls-panel"
    aria-labelledby="controls-heading"
    onfocusout={(event) => {
      if (open && !event.currentTarget.contains(event.relatedTarget as Node | null)) onclose();
    }}
  >
    <header>
      <h2 id="controls-heading">{$i18n.t('workspace.controls')}</h2>
      <button
        bind:this={closeButton}
        type="button"
        aria-label={$i18n.t('workspace.closeControls')}
        onclick={onclose}>×</button
      >
    </header>
    <p>{modelName || $i18n.t('model.connectFirst')}</p>
    <p class="muted">{$i18n.t('workspace.deferred')}</p>
  </aside>
{/if}

<style>
  aside {
    position: absolute;
    top: 56px;
    right: 16px;
    width: min(320px, calc(100% - 32px));
    padding: 20px;
    max-height: calc(100dvh - 80px);
    overflow: auto;
    z-index: 20;
    background: var(--surface);
    color: var(--ink);
    border: 1px solid var(--border);
    border-radius: 16px;
    box-shadow: 0 12px 32px #0005;
  }
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }
  h2 {
    font-size: 18px;
    margin: 0;
  }
  button {
    min-width: 44px;
    min-height: 44px;
    font-size: 24px;
    border: 0;
    background: transparent;
    color: inherit;
  }
  p {
    line-height: 1.5;
    overflow-wrap: anywhere;
  }
  .muted {
    color: var(--muted);
  }
</style>
