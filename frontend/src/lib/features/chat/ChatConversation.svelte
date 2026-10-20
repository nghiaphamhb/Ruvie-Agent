<script lang="ts">
  import { i18n } from '../../i18n/index.ts';
  import { tick, onMount } from 'svelte';
  import type { ChatTurn } from './chat-turn.ts';
  import type { ModelsResult } from '../llm/llm-api.ts';
  import CitationSources from './CitationSources.svelte';
  import AnswerContent from './AnswerContent.svelte';
  import { copyText } from './copy.ts';
  let {
    turns,
    visible,
    busy = false,
    retryDisabled = false,
    catalog = null,
    onretry = () => {},
  }: {
    turns: ChatTurn[];
    visible: boolean;
    busy?: boolean;
    retryDisabled?: boolean;
    catalog?: ModelsResult | null;
    onretry?: (id: number, modelId?: string) => void;
  } = $props();
  let conversation: HTMLDivElement;
  let turnList: HTMLElement;
  onMount(() => {
    const observer = new ResizeObserver(() => {
      if (visible && followOutput && conversation)
        conversation.scrollTop = conversation.scrollHeight;
    });
    observer.observe(turnList);
    return () => observer.disconnect();
  });
  let followOutput = $state(true),
    readingPosition = 0,
    lastTurnId = 0;
  function handleScroll() {
    if (!visible) return;
    readingPosition = conversation.scrollTop;
    followOutput = conversation.scrollHeight - readingPosition - conversation.clientHeight < 80;
  }
  function toBottom() {
    followOutput = true;
    conversation.scrollTop = conversation.scrollHeight;
  }
  $effect(() => {
    const shown = visible;
    turns.map((turn) => turn.id + ':' + turn.answer + ':' + turn.status).join('|');
    const newest = turns.at(-1)?.id ?? 0;
    if (newest !== lastTurnId) {
      lastTurnId = newest;
      followOutput = true;
    }
    if (!shown) return;
    void tick().then(() => {
      if (!visible || !conversation) return;
      conversation.scrollTop = followOutput ? conversation.scrollHeight : readingPosition;
    });
  });
</script>

<div class="conversation-region">
  <div class="conversation" bind:this={conversation} onscroll={handleScroll}>
    <section bind:this={turnList} class="turn-list" aria-label={$i18n.t('chat.conversation')}>
      {#each turns as turn (turn.id)}<article class="turn">
          <div class="user-row"><div class="user-message">{turn.question}</div></div>
          <div class="assistant-row">
            <span class="assistant-mark" aria-hidden="true">R</span>
            <div class="assistant-content">
              <div class="assistant-name">Ruvie Agent</div>
              {#if turn.answer}<div class="answer">
                  <AnswerContent content={turn.answer} />
                </div>{/if}
              {#if turn.status === 'loading' || turn.status === 'streaming'}<p
                  class="response-status"
                  aria-live="polite"
                >
                  <span class="status-dot" aria-hidden="true"></span>{$i18n.t(
                    turn.status === 'loading' ? 'chat.loading' : 'chat.streaming',
                  )}
                </p>
              {:else if turn.status === 'stopped'}<p class="response-stopped" role="status">
                  {$i18n.t('chat.stopped')}
                </p>{/if}
              {#if turn.error}<p class="response-error" role="alert">
                  {$i18n.message(turn.error)}
                </p>{/if}
              {#if turn.status === 'completed' && turn.citations.length}<CitationSources
                  citations={turn.citations}
                />{/if}
              <div class="message-actions">
                {#if turn.answer}<button type="button" onclick={() => copyText(turn.answer)}
                    >{$i18n.t('chat.copy')}</button
                  >{/if}
                {#if ['completed', 'error', 'stopped'].includes(turn.status)}
                  <button
                    type="button"
                    disabled={busy || retryDisabled}
                    onclick={() => onretry(turn.id)}
                    >{$i18n.t(
                      turn.status === 'completed' ? 'chat.regenerate' : 'chat.retry',
                    )}</button
                  >
                  {#if turn.error?.key === 'chat.retryModel' && catalog?.selected_model_id}<button
                      type="button"
                      disabled={busy || retryDisabled}
                      onclick={() => onretry(turn.id, catalog?.selected_model_id ?? undefined)}
                      >{$i18n.t('chat.retrySelected')}</button
                    >{/if}
                {/if}
              </div>
            </div>
          </div>
        </article>{/each}
    </section>
  </div>
  {#if !followOutput}<button class="jump-bottom" type="button" onclick={toBottom}
      >{$i18n.t('chat.latest')} ↓</button
    >{/if}
</div>

<style>
  .conversation-region {
    position: relative;
    display: flex;
    flex: 1;
    min-height: min(220px, 50dvh);
    min-width: 0;
  }
  .conversation {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    overscroll-behavior: contain;
    scroll-padding-bottom: 24px;
  }
  .turn-list {
    width: min(100%, var(--content-width));
    margin: 0 auto;
    padding: 36px 24px 56px;
  }
  .turn + .turn {
    margin-top: 44px;
  }
  .user-row {
    display: flex;
    justify-content: flex-end;
  }
  .user-message {
    max-width: min(82%, 640px);
    padding: 12px 17px;
    border-radius: var(--radius);
    background: var(--soft);
    line-height: 1.55;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }
  .assistant-row {
    display: flex;
    align-items: flex-start;
    gap: 14px;
    margin-top: 26px;
  }
  .assistant-content {
    flex: 1;
    min-width: 0;
    padding-top: 3px;
  }
  .assistant-name {
    margin-bottom: 9px;
    font-size: 13px;
    font-weight: 700;
  }
  .answer {
    font-size: 15px;
    min-width: 0;
  }
  .response-status {
    display: flex;
    align-items: center;
    gap: 9px;
    margin: 9px 0 0;
    color: var(--muted);
    font-size: 13px;
  }
  .response-stopped {
    color: var(--muted);
    font-size: 13px;
  }
  .response-error {
    margin: 10px 0 0;
    padding: 10px 13px;
    border: 1px solid var(--error-border);
    border-radius: var(--radius);
    background: var(--error-bg);
    color: var(--error);
    font-size: 13px;
    line-height: 1.5;
  }
  .message-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 12px;
  }
  button {
    min-height: 44px;
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 8px 12px;
    background: var(--surface);
    color: var(--ink);
    font-size: 13px;
  }
  button:disabled {
    opacity: 0.55;
  }
  .jump-bottom {
    position: absolute;
    bottom: 14px;
    left: 50%;
    transform: translateX(-50%);
    box-shadow: 0 4px 16px #0004;
    white-space: nowrap;
  }
  @media (max-width: 600px) {
    .turn-list {
      padding: 20px 0 48px;
    }
    .assistant-row {
      gap: 10px;
    }
  }
</style>
