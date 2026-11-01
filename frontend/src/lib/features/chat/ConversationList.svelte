<script lang="ts">
  import { tick } from 'svelte';
  import { i18n } from '../../i18n/index.ts';
  import SurfaceDialog from '../../shared/SurfaceDialog.svelte';
  import type { createChatState } from './chat-state.svelte.ts';
  import type { Conversation } from './conversation-api.ts';
  let {
    state: owner,
    onselect,
  }: { state: ReturnType<typeof createChatState>; onselect: (id: string) => void } = $props();
  let selected = $state<Conversation | null>(null),
    action = $state<'rename' | 'delete'>('rename'),
    title = $state(''),
    saving = $state(false),
    failed = $state(false);
  function edit(item: Conversation, kind: 'rename' | 'delete', event: MouseEvent) {
    const menu = (event.currentTarget as HTMLElement).closest('details');
    menu?.removeAttribute('open');
    menu?.querySelector<HTMLElement>('summary')?.focus();
    selected = item;
    action = kind;
    title = item.title;
    failed = false;
  }
  async function save(event: SubmitEvent) {
    event.preventDefault();
    if (
      !selected ||
      saving ||
      (action === 'rename' &&
        (Array.from(title.trim()).length < 1 || Array.from(title.trim()).length > 120))
    )
      return;
    saving = true;
    failed = false;
    const success =
      action === 'rename'
        ? await owner.rename(selected.id, title, selected.version)
        : await owner.remove(selected.id);
    saving = false;
    if (success) {
      selected = null;
      await tick();
      if (action === 'delete')
        [...document.querySelectorAll<HTMLElement>('[data-history-heading],#question')]
          .find((element) => element.getClientRects().length > 0)
          ?.focus();
    } else {
      failed = true;
      // Conflict requires a fresh displayed version before another explicit submission.
      selected = owner.conversations.find((item) => item.id === selected?.id) ?? selected;
      title = selected.title;
    }
  }
</script>

<div class="conversation-list" aria-label={$i18n.t('workspace.conversations')}>
  {#if owner.listLoading}<p role="status">{$i18n.t('history.loading')}</p>{/if}
  {#if owner.listError}<p role="alert">{$i18n.t('history.error')}</p>
    <button onclick={() => owner.loadList()}>{$i18n.t('history.refresh')}</button>
  {:else if !owner.listLoading && !owner.conversations.length}<p>
      {$i18n.t('workspace.emptyConversations')}
    </p>{/if}
  {#each owner.conversations as item (item.id)}
    <div class="history-row">
      <button
        class="chat-link"
        aria-current={owner.conversationId === item.id ? 'page' : undefined}
        title={item.title}
        onclick={() => onselect(item.id)}>{item.title}</button
      >
      <details>
        <summary aria-label={$i18n.t('history.actions', { title: item.title })}>⋯</summary>
        <div class="row-actions">
          <button onclick={(event) => edit(item, 'rename', event)}
            >{$i18n.t('history.rename')}</button
          >
          <button onclick={(event) => edit(item, 'delete', event)}
            >{$i18n.t('history.delete')}</button
          >
        </div>
      </details>
      <span class="pin-placeholder" title={$i18n.t('history.pinSoon')}>
        <button class="pin-button" type="button" disabled aria-label={$i18n.t('history.pinSoon')}>
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.5"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <path d="m16 3 5 5-4 1-3 5v3l-2 2-7-7 2-2h3l5-3 1-4ZM9 15l-6 6" />
          </svg>
        </button>
      </span>
    </div>
  {/each}
  {#if owner.listCursor}<button disabled={owner.listLoading} onclick={() => owner.loadList(true)}
      >{$i18n.t('history.more')}</button
    >{/if}
</div>
<SurfaceDialog
  open={selected !== null}
  title={$i18n.t(action === 'rename' ? 'history.rename' : 'history.delete')}
  closeDisabled={saving}
  onclose={() => {
    selected = null;
  }}
>
  <form onsubmit={save}>
    {#if action === 'rename'}<label
        >{$i18n.t('history.title')}<input
          data-dialog-initial-focus
          bind:value={title}
          required
          maxlength="240"
          disabled={saving}
        /></label
      >
    {:else}<p>{$i18n.t('history.confirmDelete', { title: selected?.title ?? '' })}</p>{/if}
    {#if failed}<p role="alert">{$i18n.t('history.writeError')}</p>{/if}
    <div class="dialog-actions">
      <button
        type="button"
        disabled={saving}
        onclick={() => {
          selected = null;
        }}>{$i18n.t('history.cancel')}</button
      ><button
        disabled={saving ||
          (action === 'rename' && (!title.trim() || Array.from(title.trim()).length > 120))}
        >{$i18n.t(action === 'rename' ? 'history.save' : 'history.delete')}</button
      >
    </div>
  </form>
</SurfaceDialog>

<style>
  .conversation-list {
    display: grid;
    gap: 4px;
    min-width: 0;
  }
  .history-row {
    display: flex;
    align-items: center;
    min-width: 0;
    gap: 0;
    border-radius: 6px;
  }
  .history-row:hover,
  .history-row:focus-within,
  .history-row:has([aria-current='page']) {
    background: var(--soft);
  }
  .history-row > button:hover,
  .history-row summary:hover,
  .history-row > button[aria-current='page'] {
    background: transparent;
  }
  button,
  summary {
    cursor: pointer;
    color: var(--ink);
    background: transparent;
    border: 0;
    border-radius: 8px;
    padding: 10px;
    min-height: 44px;
    min-width: 44px;
  }
  button:hover,
  summary:hover,
  button[aria-current='page'] {
    background: var(--soft);
  }
  .chat-link {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    text-align: left;
  }
  .history-row summary,
  .history-row .pin-button {
    box-sizing: border-box;
    display: grid;
    place-items: center;
    width: 28px;
    min-width: 28px;
    padding: 4px;
  }
  .pin-placeholder {
    display: flex;
    flex: none;
  }
  .pin-button {
    display: grid;
    place-items: center;
    opacity: 0.45;
    cursor: default;
  }
  .pin-button:hover {
    background: transparent;
  }
  details {
    position: relative;
  }
  summary {
    list-style: none;
  }
  .row-actions {
    position: absolute;
    right: 0;
    z-index: 2;
    display: grid;
    padding: 4px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
  }
  p {
    color: var(--muted);
  }
  label {
    display: grid;
    gap: 8px;
  }
  input {
    padding: 10px;
    background: var(--surface);
    color: var(--ink);
    border: 1px solid var(--border);
    border-radius: 8px;
  }
  .dialog-actions {
    display: flex;
    justify-content: end;
    gap: 8px;
    margin-top: 16px;
  }
</style>
