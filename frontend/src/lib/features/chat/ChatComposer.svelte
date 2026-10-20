<script lang="ts">
  import { tick, onDestroy } from 'svelte';
  import { i18n } from '../../i18n/index.ts';
  import WorkspaceIcon from '../../shared/WorkspaceIcon.svelte';
  let {
    draft,
    disabled,
    busy = false,
    oninput,
    onsubmit,
    onattach,
    onstop = () => {},
    onexpand = () => {},
  }: {
    draft: string;
    disabled: boolean;
    busy?: boolean;
    oninput: (value: string) => void;
    onsubmit: (event: SubmitEvent) => void;
    onattach: () => void;
    onstop?: () => void;
    onexpand?: (expanded: boolean) => void;
  } = $props();
  let expanded = $state(false);
  let textarea: HTMLTextAreaElement;
  function handleInputKeydown(event: KeyboardEvent) {
    // Some IMEs report the confirmation key as 229 after compositionend.
    if (event.key !== 'Enter' || event.shiftKey || event.isComposing || event.keyCode === 229)
      return;
    event.preventDefault();
    if (!busy) (event.currentTarget as HTMLTextAreaElement).form?.requestSubmit();
  }
  let composer: HTMLFormElement;
  let animations: Animation[] = [];
  onDestroy(() => animations.forEach((animation) => animation.cancel()));
  $effect(() => {
    void draft;
    if (!textarea || !composer) return;
    const previous = composer.getBoundingClientRect();
    const buttons = [...composer.querySelectorAll<HTMLButtonElement>('button')];
    const positions = buttons.map((button) => button.getBoundingClientRect());
    textarea.style.height = 'auto';
    const height = Math.min(180, Math.max(24, textarea.scrollHeight));
    textarea.style.height = height + 'px';
    expanded = height > 24;
    onexpand(height > 24);
    let cancelled = false;
    void tick().then(() => {
      if (cancelled) return;
      animations.forEach((animation) => animation.cancel());
      animations = [];
      if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
      const next = composer.getBoundingClientRect();
      const timing = { duration: 200, easing: 'cubic-bezier(.2,.8,.2,1)' };

      buttons.forEach((button, index) => {
        if (!button.isConnected) return;
        const target = button.getBoundingClientRect();
        const x = positions[index].left - previous.left - (target.left - next.left);
        const y = positions[index].top - previous.top - (target.top - next.top);
        if (x || y)
          animations.push(
            button.animate(
              [{ transform: `translate(${x}px,${y}px)` }, { transform: 'translate(0,0)' }],
              timing,
            ),
          );
      });
      if (previous.height !== next.height) {
        animations.push(
          composer.animate(
            [{ height: previous.height + 'px' }, { height: next.height + 'px' }],
            timing,
          ),
        );
      }
    });
    return () => {
      cancelled = true;
    };
  });
</script>

<div class="composer-area">
  <form bind:this={composer} class="composer" class:expanded {onsubmit}>
    <label class="sr-only" for="question">{$i18n.t('chat.question')}</label>
    <textarea
      bind:this={textarea}
      id="question"
      rows="1"
      placeholder={$i18n.t('workspace.questionPlaceholder')}
      value={draft}
      oninput={(event) => oninput(event.currentTarget.value)}
      onkeydown={handleInputKeydown}></textarea>
    <div class="composer-actions">
      <button
        class="attach-trigger"
        type="button"
        aria-label={$i18n.t('workspace.attach')}
        title={$i18n.t('workspace.attach')}
        onclick={onattach}><WorkspaceIcon name="plus" /></button
      >

      {#if busy}<button
          class="stop-button"
          type="button"
          aria-label={$i18n.t('chat.stop')}
          title={$i18n.t('chat.stop')}
          onclick={onstop}
          ><svg viewBox="0 0 16 16" aria-hidden="true"
            ><rect x="4" y="4" width="8" height="8" rx="1" fill="currentColor" /></svg
          ></button
        >
      {:else}<button
          class="send-button"
          type="submit"
          disabled={disabled || !draft.trim()}
          aria-label={$i18n.t('chat.send')}
          title={$i18n.t('chat.send')}
          ><svg viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"
            ><path
              d="M8 14a.75.75 0 0 1-.75-.75V4.56L4.03 7.78a.75.75 0 0 1-1.06-1.06l4.5-4.5a.75.75 0 0 1 1.06 0l4.5 4.5a.75.75 0 0 1-1.06 1.06L8.75 4.56v8.69A.75.75 0 0 1 8 14Z"
            /></svg
          ></button
        >{/if}
    </div>
  </form>
</div>

<style>
  .composer-area {
    flex: none;
    padding: 0;
    width: 100%;
  }
  .composer {
    display: grid;
    grid-template-columns: 44px minmax(0, 1fr) 44px;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    border: 1px solid var(--border);
    border-radius: 30px;
    overflow: hidden;
    background: color-mix(in srgb, var(--surface) 65%, transparent);
  }
  textarea {
    grid-column: 2;
    grid-row: 1;
    display: block;
    width: 100%;
    padding: 0;
    min-height: 24px;
    max-height: min(180px, 30dvh);
    scrollbar-width: thin;
    scrollbar-color: var(--border) transparent;
    overscroll-behavior: contain;
    resize: none;
    overflow-y: auto;
    border: 0;
    outline: 0;
    background: transparent;
    color: var(--ink);
    font-size: 16px;
    line-height: 1.5;
  }
  textarea::placeholder {
    color: var(--muted);
  }
  .composer:focus-within {
    border-color: #7196bc;
  }
  .composer-actions {
    display: contents;
  }
  .attach-trigger {
    grid-column: 1;
    grid-row: 1;
  }
  .send-button,
  .stop-button {
    grid-column: 3;
    grid-row: 1;
  }
  .composer.expanded textarea {
    grid-column: 1 / -1;
    grid-row: 1;
    margin: 8px 0;
  }
  .composer.expanded .attach-trigger,
  .composer.expanded .send-button,
  .composer.expanded .stop-button {
    grid-row: 2;
  }
  button {
    display: grid;
    place-items: center;
    flex: none;
    width: 44px;
    height: 44px;
    border: 0;
    border-radius: 50%;
  }
  .attach-trigger {
    color: var(--ink);
    background: transparent;
  }
  .attach-trigger:hover {
    background: var(--soft);
  }
  .send-button,
  .stop-button {
    color: #073b65;
    background: #f0f6fc;
  }
  .send-button:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }
  svg {
    width: 20px;
    height: 20px;
  }
  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    overflow: hidden;
    clip-path: inset(50%);
  }
</style>
