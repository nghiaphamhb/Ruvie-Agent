<script lang="ts">
  import { tick } from 'svelte';
  import { i18n } from '../../i18n/index.ts';
  import type { ChatTurn } from './chat-turn.ts';
  import type { ModelsResult } from '../llm/llm-api.ts';
  import ChatWelcome from './ChatWelcome.svelte';
  import ChatConversation from './ChatConversation.svelte';
  import ChatComposer from './ChatComposer.svelte';
  let {
    name,
    turns,
    draft,
    visible,
    disabled,
    busy = false,
    onstop = () => {},
    onretry = () => {},
    modelDisabled,
    modelLoading,
    catalog,
    oninput,
    onsubmit,
    onattach,
  }: {
    busy?: boolean;
    onstop?: () => void;
    onretry?: (id: number, modelId?: string) => void;
    name: string;
    turns: ChatTurn[];
    draft: string;
    visible: boolean;
    disabled: boolean;
    modelDisabled: boolean;
    modelLoading: boolean;
    catalog: ModelsResult | null;
    oninput: (value: string) => void;
    onsubmit: (event: SubmitEvent) => void;
    onattach: () => void;
  } = $props();
  const suggestions = [
    { label: 'chat.suggestDiagnose', prompt: 'chat.promptDiagnose' },
    { label: 'chat.suggestInstall', prompt: 'chat.promptInstall' },
    { label: 'chat.suggestGuide', prompt: 'chat.promptGuide' },
  ] as const;
  async function suggest(value: string) {
    oninput(value);
    await tick();
    document.getElementById('question')?.focus();
  }
</script>

<section class="chat-page" class:empty={turns.length === 0} aria-label={$i18n.t('nav.chat')}>
  {#if turns.length === 0}<div class="welcome-wrap">
      <ChatWelcome {name} />
    </div>{:else}<ChatConversation
      {turns}
      {visible}
      {busy}
      {catalog}
      {onretry}
      retryDisabled={modelLoading || (modelDisabled && !busy)}
    />{/if}
  <div class="chat-composer-wrap">
    <ChatComposer {draft} {disabled} {busy} {onstop} {oninput} {onsubmit} {onattach} />
    <p class="chat-input-hint">{$i18n.t('chat.inputHint')}</p>
  </div>
  {#if turns.length === 0}
    <div
      class="chat-suggestions"
      class:concealed={draft.trim().length > 0}
      inert={draft.trim().length > 0}
      aria-hidden={draft.trim().length > 0}
    >
      <p>✧ {$i18n.t('workspace.suggestions')}</p>
      {#each suggestions as item (item.label)}<button
          type="button"
          onclick={() => suggest($i18n.t(item.prompt))}>{$i18n.t(item.label)}</button
        >{/each}
    </div>
  {/if}
</section>

<style>
  .chat-page {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-width: 0;
    min-height: 0;
    padding: 12px 24px 20px;
    overflow: hidden;
    scrollbar-width: thin;
    scrollbar-color: var(--border) transparent;
  }
  .chat-page.empty {
    justify-content: flex-start;
    padding-top: max(24px, calc((100dvh - 620px) / 2));
    overflow-y: auto;
    overscroll-behavior: contain;
  }
  .welcome-wrap {
    flex: none;
  }
  .chat-composer-wrap {
    flex: none;
    width: min(100%, 900px);
    margin: 20px auto 0;
  }
  .chat-suggestions {
    flex: none;
    width: min(100%, 700px);
    margin: 24px auto 0;
    opacity: 1;
    visibility: visible;
    transition:
      opacity 150ms ease,
      visibility 150ms;
  }
  .chat-suggestions.concealed {
    opacity: 0;
    visibility: hidden;
    pointer-events: none;
  }
  @media (prefers-reduced-motion: reduce) {
    .chat-suggestions {
      transition: none;
    }
  }
  .chat-suggestions p {
    margin: 0 0 8px;
    color: var(--muted);
    font-size: 14px;
  }
  .chat-suggestions button {
    display: block;
    min-height: 44px;
    max-width: 100%;
    padding: 8px 12px;
    text-align: left;
    color: var(--ink);
    border: 0;
    border-radius: 10px;
    background: transparent;
    font-size: 16px;
    line-height: 1.5;
  }
  .chat-suggestions button:hover {
    background: var(--soft);
  }
  @media (max-width: 600px) {
    .chat-page {
      padding: 12px 16px 16px;
    }
    .chat-page.empty {
      justify-content: flex-start;
      padding-top: 24px;
    }
  }
  @media (max-height: 600px) {
    .chat-page.empty {
      padding-top: 12px;
    }
  }
  .chat-input-hint {
    margin: 8px 12px 0;
    color: var(--muted);
    font-size: 12px;
    line-height: 1.5;
    text-align: center;
  }
</style>
