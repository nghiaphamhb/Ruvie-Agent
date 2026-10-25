<script lang="ts">
  import { tick, type Snippet } from 'svelte';
  import { i18n } from '../i18n/index.ts';
  let {
    open,
    title,
    onclose,
    children,
    className = '',
    closeDisabled = false,
    dismissOnBackdrop = false,
  }: {
    open: boolean;
    title: string;
    onclose: () => void;
    children: Snippet;
    className?: string;
    closeDisabled?: boolean;
    dismissOnBackdrop?: boolean;
  } = $props();
  let dialog: HTMLDialogElement;
  let trigger: HTMLElement | null = null;
  $effect(() => {
    if (open && !dialog.open) {
      trigger = document.activeElement as HTMLElement;
      dialog.showModal();
      void tick().then(() => {
        if (open)
          (
            dialog.querySelector<HTMLElement>('[data-dialog-initial-focus]') ??
            dialog.querySelector<HTMLElement>('[data-dialog-heading]')
          )?.focus();
      });
    } else if (!open && dialog.open) {
      dialog.close();
      if (trigger?.isConnected) trigger.focus();
    }
  });
  $effect(() => {
    if (!open) return;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = overflow;
    };
  });
  function key(event: KeyboardEvent) {
    if (event.key !== 'Tab') return;
    const controls = [
      ...dialog.querySelectorAll<HTMLElement>(
        'button,input,select,textarea,summary,a[href],[tabindex]',
      ),
    ].filter(
      (el) => el.tabIndex >= 0 && !el.matches(':disabled') && el.getClientRects().length > 0,
    );
    const first = controls[0],
      last = controls.at(-1);
    if (
      event.shiftKey &&
      (document.activeElement === first ||
        document.activeElement === dialog.querySelector('[data-dialog-heading]'))
    ) {
      event.preventDefault();
      last?.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first?.focus();
    }
  }
</script>

<dialog
  bind:this={dialog}
  class={'surface-dialog ' + className}
  aria-label={title}
  onkeydown={key}
  onclick={(event) => {
    if (!dismissOnBackdrop || closeDisabled || event.target !== dialog) return;
    const rect = dialog.getBoundingClientRect();
    if (
      event.clientX < rect.left ||
      event.clientX > rect.right ||
      event.clientY < rect.top ||
      event.clientY > rect.bottom
    )
      onclose();
  }}
  oncancel={(event) => {
    event.preventDefault();
    event.stopPropagation();
    if (!closeDisabled) onclose();
  }}
  onclose={() => {
    if (open) onclose();
  }}
>
  <header>
    <h2 data-dialog-heading tabindex="-1">{title}</h2>
    <button
      type="button"
      aria-label={$i18n.t('ux.close')}
      disabled={closeDisabled}
      onclick={onclose}>×</button
    >
  </header>
  {@render children()}
</dialog>

<style>
  dialog {
    width: min(760px, calc(100vw - 32px));
    max-height: calc(100dvh - 32px);
    padding: 24px;
    overflow: auto;
    border: 1px solid var(--border);
    border-radius: 16px;
    background: var(--surface);
    color: var(--ink);
  }
  dialog::backdrop {
    background: #010c1dcc;
    backdrop-filter: blur(4px);
  }
  header {
    position: relative;
    display: flex;
    align-items: center;
    min-height: 44px;
    padding-right: 44px;
    margin-bottom: 20px;
  }
  h2 {
    margin: 0;
    font-size: 20px;
    overflow-wrap: anywhere;
  }
  button {
    position: absolute;
    top: 0;
    right: 0;
    display: grid;
    place-items: center;
    width: 44px;
    height: 44px;
    padding: 0;
    border: 0;
    border-radius: 8px;
    background: transparent;
    color: var(--ink);
    font-size: 24px;
  }
  button:hover {
    background: var(--soft);
  }
  button:disabled {
    opacity: 0.55;
    cursor: wait;
  }
</style>
