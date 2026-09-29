<script lang="ts">
  import { onDestroy, tick } from 'svelte';
  import { ChatApiError, streamChat, type Citation } from './lib/chat-api';

  type ChatTurn = {
    id: number;
    question: string;
    answer: string;
    citations: Citation[];
    status: 'loading' | 'streaming' | 'completed' | 'error';
    error: string;
  };

  let draft = $state('');
  let turns = $state<ChatTurn[]>([]);
  let busy = $state(false);
  let conversation: HTMLDivElement;
  let followOutput = true;
  let nextTurnId = 1;
  let activeRequest: AbortController | null = null;
  let compositionEndedAt = 0;

  function handleScroll() {
    if (conversation) {
      followOutput = conversation.scrollHeight - conversation.scrollTop - conversation.clientHeight < 80;
    }
  }

  async function scrollToLatest() {
    await tick();
    if (followOutput && conversation) conversation.scrollTop = conversation.scrollHeight;
  }

  function handleInputKeydown(event: KeyboardEvent) {
    if (event.key !== 'Enter' || event.shiftKey || event.isComposing || event.timeStamp - compositionEndedAt < 40) return;
    event.preventDefault();
    (event.currentTarget as HTMLTextAreaElement).form?.requestSubmit();
  }

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    const message = draft.trim();
    if (!message || busy) return;

    const turn: ChatTurn = {
      id: nextTurnId++, question: message, answer: '', citations: [], status: 'loading', error: ''
    };
    turns.push(turn);
    const activeTurn = turns[turns.length - 1];
    draft = '';
    busy = true;
    followOutput = true;
    activeRequest = new AbortController();
    void scrollToLatest();

    try {
      await streamChat(message, (received) => {
        if (received.type === 'delta') {
          activeTurn.answer += received.text;
          activeTurn.status = 'streaming';
        } else if (received.type === 'citations') {
          activeTurn.citations = received.citations;
        } else {
          activeTurn.status = 'completed';
        }
        void scrollToLatest();
      }, activeRequest.signal);
    } catch (error) {
      if (!activeRequest.signal.aborted) {
        activeTurn.status = 'error';
        activeTurn.citations = [];
        activeTurn.error = error instanceof ChatApiError ? error.message : 'Không thể hoàn tất câu trả lời.';
        void scrollToLatest();
      }
    } finally {
      activeRequest = null;
      busy = false;
    }
  }

  onDestroy(() => activeRequest?.abort());
</script>

<svelte:head>
  <title>Ruvie Assistant — Tra cứu tài liệu</title>
  <meta name="description" content="Đặt câu hỏi và nhận câu trả lời kèm nguồn tài liệu bạn được phép đọc." />
</svelte:head>

<div class="app-shell">
  <header class="topbar">
    <div class="brand" aria-label="Ruvie Assistant">
      <span class="brand-mark" aria-hidden="true">R</span>
      <span>Ruvie <strong>Assistant</strong></span>
    </div>
    <span class="topbar-note">Tra cứu tài liệu</span>
  </header>

  <main class="chat-layout">
    <div class="conversation" bind:this={conversation} onscroll={handleScroll}>
      {#if turns.length === 0}
        <div class="welcome">
          <span class="welcome-mark" aria-hidden="true">R</span>
          <p class="eyebrow">RUVIE ASSISTANT</p>
          <h1>Bạn muốn tìm hiểu điều gì?</h1>
          <p>Đặt câu hỏi về tài liệu bạn được phép đọc. Câu trả lời sẽ xuất hiện dần cùng danh sách nguồn tham khảo.</p>
        </div>
      {:else}
        <section class="turn-list" aria-label="Hội thoại">
          {#each turns as turn (turn.id)}
            <article class="turn">
              <div class="user-row">
                <div class="user-message">{turn.question}</div>
              </div>
              <div class="assistant-row">
                <span class="assistant-mark" aria-hidden="true">R</span>
                <div class="assistant-content">
                  <div class="assistant-name">Ruvie Assistant</div>
                  {#if turn.answer}
                    <div class="answer">{turn.answer}</div>
                  {/if}
                  {#if turn.status === 'loading'}
                    <p class="response-status" aria-live="polite"><span class="status-dot" aria-hidden="true"></span>Đang tìm câu trả lời…</p>
                  {:else if turn.status === 'streaming'}
                    <p class="response-status" aria-live="polite"><span class="status-dot" aria-hidden="true"></span>Đang trả lời…</p>
                  {:else if turn.status === 'error'}
                    <p class="response-error" role="alert">{turn.error}</p>
                  {/if}

                  {#if turn.status === 'completed' && turn.citations.length > 0}
                    <details class="sources">
                      <summary>{turn.citations.length} nguồn tham khảo</summary>
                      <ol>
                        {#each turn.citations as citation (citation.citation_id)}
                          <li>
                            <div class="source-title">{citation.title}</div>
                            <dl>
                              <div><dt>Document</dt><dd>{citation.document_id}</dd></div>
                              <div><dt>Revision</dt><dd>{citation.revision_id}</dd></div>
                              <div><dt>Chunk</dt><dd>{citation.chunk_id} · #{citation.ordinal}</dd></div>
                              <div><dt>Vị trí</dt><dd>{citation.start_offset}–{citation.end_offset}</dd></div>
                              <div><dt>Source hash</dt><dd>{citation.source_hash}</dd></div>
                              <div><dt>Phần mềm</dt><dd>{citation.software} {citation.software_version}</dd></div>
                            </dl>
                          </li>
                        {/each}
                      </ol>
                    </details>
                  {/if}
                </div>
              </div>
            </article>
          {/each}
        </section>
      {/if}
    </div>

    <div class="composer-area">
      <form class="composer" onsubmit={submit}>
        <label for="question">Câu hỏi của bạn</label>
        <div class="composer-input">
          <textarea
            id="question"
            rows="2"
            placeholder="Hỏi về tài liệu của bạn…"
            bind:value={draft}
            onkeydown={handleInputKeydown}
            oncompositionend={(event) => (compositionEndedAt = event.timeStamp)}
          ></textarea>
          <button type="submit" disabled={busy || !draft.trim()} aria-label="Gửi câu hỏi" title="Gửi câu hỏi">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="m5 12 14-7-4 14-3-6-7-1Z" />
              <path d="m12 13 7-8" />
            </svg>
          </button>
        </div>
      </form>
      <p class="composer-hint">Enter để gửi · Shift+Enter để xuống dòng · Mỗi câu hỏi được xử lý độc lập. Lịch sử chỉ giữ trong trang này.</p>
    </div>
  </main>
</div>
