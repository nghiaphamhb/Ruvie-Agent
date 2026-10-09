<script lang="ts">
  import { i18n } from '../i18n/index.ts';
  import { tick } from 'svelte';
  import type { ChatTurn } from '../chat-turn';
  import CitationSources from './CitationSources.svelte';
  let { turns, visible }: { turns: ChatTurn[]; visible: boolean } = $props();
  let conversation: HTMLDivElement;
  let followOutput = true;
  let readingPosition = 0;
  let lastTurnId = 0;
  /** A hidden panel has no useful geometry; retain its last reading position. */
  function handleScroll() {
    if (!visible) return;
    readingPosition = conversation.scrollTop;
    followOutput = conversation.scrollHeight - readingPosition - conversation.clientHeight < 80;
  }
  $effect(() => {
    const shown = visible;
    const output = turns.map(turn => `${turn.id}:${turn.answer}:${turn.status}`).join('|');
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
<!-- Centered welcome adapted from chat/Placeholder.svelte; active SSE stays text. -->
<div class="conversation" bind:this={conversation} onscroll={handleScroll}>
  {#if turns.length === 0}
    <div class="welcome">
      <span class="welcome-mark" aria-hidden="true">R</span>
      <p class="eyebrow">RUVIE AGENT</p>
      <h1>{$i18n.t('chat.welcome')}</h1>
      <p>{$i18n.t('chat.description')}</p>
    </div>
  {:else}
    <section class="turn-list" aria-label={$i18n.t('chat.conversation')}>
      {#each turns as turn (turn.id)}
        <article class="turn">
          <div class="user-row">
            <div class="user-message">{turn.question}</div>
          </div>
          <div class="assistant-row">
            <span class="assistant-mark" aria-hidden="true">R</span>
            <div class="assistant-content">
              <div class="assistant-name">Ruvie Agent</div>
              {#if turn.answer}
                <div class="answer">{turn.answer}</div>
              {/if}
              {#if turn.status === 'loading'}
                <p class="response-status" aria-live="polite"><span class="status-dot" aria-hidden="true"></span>{$i18n.t('chat.loading')}</p>
              {:else if turn.status === 'streaming'}
                <p class="response-status" aria-live="polite"><span class="status-dot" aria-hidden="true"></span>{$i18n.t('chat.streaming')}</p>
              {:else if turn.status === 'error'}
                <p class="response-error" role="alert">{$i18n.message(turn.error)}</p>
              {/if}

              {#if turn.status === 'completed' && turn.citations.length > 0}
                <CitationSources citations={turn.citations} />
              {/if}
            </div>
          </div>
        </article>
      {/each}
    </section>
  {/if}
</div>

<style>
  /* Keep a readable scroll region when zoom/long headers leave little height.
     The surrounding panel scrolls to reach the composer instead of shrinking chat to zero. */
  .conversation { flex: 1; min-height: min(220px, 50dvh); overflow-y: auto; overscroll-behavior: contain; scroll-padding-bottom: 24px; }
  .welcome { width: min(100%, 680px); min-height: 100%; margin: 0 auto; padding: 48px 24px 104px; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; }
  .welcome h1 { margin: 0; font-size: clamp(28px, 4vw, 42px); line-height: 1.17; letter-spacing: -.04em; font-weight: 650; }
  .welcome > p:last-child { max-width: 560px; margin: 17px 0 0; color: var(--muted); font-size: 16px; line-height: 1.65; }
  .turn-list { width: min(100%, var(--content-width)); margin: 0 auto; padding: 36px 24px 56px; }
  .turn + .turn { margin-top: 44px; }
  .user-row { display: flex; justify-content: flex-end; }
  .user-message { max-width: min(82%, 640px); padding: 12px 17px; border-radius: var(--radius); background: var(--soft); color: var(--ink); line-height: 1.55; white-space: pre-wrap; overflow-wrap: anywhere; }
  .assistant-row { display: flex; align-items: flex-start; gap: 14px; margin-top: 26px; }
  .assistant-content { flex: 1; min-width: 0; padding-top: 3px; }
  .assistant-name { margin-bottom: 9px; font-size: 13px; font-weight: 700; }
  .answer { white-space: pre-wrap; overflow-wrap: anywhere; font-size: 15px; line-height: 1.75; }
  .response-status { display: flex; align-items: center; gap: 9px; margin: 9px 0 0; color: var(--muted); font-size: 13px; }
  .response-error { display: inline-block; margin: 10px 0 0; padding: 10px 13px; border: 1px solid var(--error-border); border-radius: var(--radius); background: var(--error-bg); color: var(--error); font-size: 13px; line-height: 1.5; }
</style>
