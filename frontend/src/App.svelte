<script lang="ts">
  import { onDestroy, onMount, tick } from 'svelte';
  import { ChatApiError, streamChat, type Citation } from './lib/chat-api';
  import { AuthApiError, getAuthSession, login, logout, type AuthUser } from './lib/auth-api';
  import {
    DocumentsApiError, getRevisionStatus, listProjects, uploadDocument,
    type ProjectSummary, type RevisionStatus
  } from './lib/documents-api';

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
  let conversation = $state<HTMLDivElement | undefined>(undefined);
  let followOutput = true;
  let nextTurnId = 1;
  let activeRequest: AbortController | null = null;
  let compositionEndedAt = 0;
  let authLoading = $state(true);
  let authBusy = $state(false);
  let authUser = $state<AuthUser | null>(null);
  let csrfToken = $state('');
  let email = $state('');
  let password = $state('');
  let authError = $state('');
  let projects = $state<ProjectSummary[]>([]);
  let projectsLoading = $state(false);
  let projectsError = $state('');
  let selectedProjectId = $state('');
  let uploadTitle = $state('');
  let uploadSoftware = $state('');
  let uploadSoftwareVersion = $state('');
  let selectedFile = $state<File | null>(null);
  let uploadBusy = $state(false);
  let uploadError = $state('');
  let uploadStatus = $state<RevisionStatus | null>(null);
  let uploadTimedOut = $state(false);
  let statusRefreshing = $state(false);
  let uploadSequence = 0;

  onMount(async () => {
    try {
      const current = await getAuthSession();
      authUser = current?.user ?? null;
      csrfToken = current?.csrf_token ?? '';
      if (current) await loadProjects();
    } catch (error) {
      authError = error instanceof AuthApiError ? error.message : 'Không thể kiểm tra phiên đăng nhập.';
    } finally {
      authLoading = false;
    }
  });

  async function submitLogin(event: SubmitEvent) {
    event.preventDefault();
    if (authBusy) return;
    authBusy = true;
    authError = '';
    try {
      const result = await login(email.trim(), password);
      authUser = result.user;
      csrfToken = result.csrf_token;
      password = '';
      await loadProjects();
    } catch (error) {
      authError = error instanceof AuthApiError ? error.message : 'Không thể đăng nhập.';
    } finally {
      authBusy = false;
    }
  }

  async function signOut() {
    authBusy = true;
    authError = '';
    try {
      await logout(csrfToken);
      authUser = null;
      csrfToken = '';
      turns = [];
      uploadSequence += 1;
      projects = [];
      selectedProjectId = '';
      uploadStatus = null;
    } catch (error) {
      authError = error instanceof AuthApiError ? error.message : 'Không thể đăng xuất.';
    } finally {
      authBusy = false;
    }
  }

  async function loadProjects() {
    projectsLoading = true;
    projectsError = '';
    try {
      projects = await listProjects();
    } catch {
      projectsError = 'Không thể tải danh sách project. Hãy thử tải lại trang.';
    } finally {
      projectsLoading = false;
    }
  }

  async function submitUpload(event: SubmitEvent) {
    event.preventDefault();
    if (uploadBusy || !selectedFile || !selectedProjectId) return;
    uploadBusy = true;
    uploadError = '';
    uploadStatus = null;
    uploadTimedOut = false;
    const sequence = ++uploadSequence;
    try {
      const result = await uploadDocument(csrfToken, {
        project_id: selectedProjectId,
        title: uploadTitle,
        software: uploadSoftware,
        software_version: uploadSoftwareVersion,
        file: selectedFile
      });
      uploadStatus = { revision_id: result.revision_id, status: result.status, error_code: null };
      const deadline = Date.now() + 5 * 60 * 1000;
      while (sequence === uploadSequence && Date.now() < deadline) {
        await new Promise((resolve) => setTimeout(resolve, 2000));
        if (sequence !== uploadSequence) return;
        const status = await getRevisionStatus(result.revision_id);
        uploadStatus = status;
        if (status.status === 'ready' || status.status === 'failed') return;
      }
      if (sequence === uploadSequence) uploadTimedOut = true;
    } catch (error) {
      uploadError = error instanceof DocumentsApiError && error.status === 404
        ? 'Không tìm thấy project hoặc tài liệu được phép truy cập.'
        : 'Không thể tải lên hoặc kiểm tra trạng thái tài liệu.';
    } finally {
      uploadBusy = false;
    }
  }

  async function refreshUploadStatus() {
    if (!uploadStatus || statusRefreshing) return;
    statusRefreshing = true;
    uploadError = '';
    try {
      uploadStatus = await getRevisionStatus(uploadStatus.revision_id);
    } catch {
      uploadError = 'Không thể làm mới trạng thái tài liệu.';
    } finally {
      statusRefreshing = false;
    }
  }

  function uploadStatusLabel(status: RevisionStatus['status']) {
    return { pending: 'Đang chờ xử lý', running: 'Đang xử lý', ready: 'Sẵn sàng', failed: 'Xử lý thất bại' }[status];
  }

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

  onDestroy(() => { activeRequest?.abort(); uploadSequence += 1; });
</script>

<svelte:head>
  <title>Ruvie Agent — Tra cứu tài liệu</title>
  <meta name="description" content="Đặt câu hỏi và nhận câu trả lời kèm nguồn tài liệu bạn được phép đọc." />
</svelte:head>

<div class="app-shell">
  <header class="topbar">
    <div class="brand" aria-label="Ruvie Agent">
      <span class="brand-mark" aria-hidden="true">R</span>
      <span>Ruvie <strong>Agent</strong></span>
    </div>
    {#if authUser}
      <div class="account-actions"><span class="topbar-note">{authUser.display_name}</span><button class="logout-button" type="button" onclick={signOut} disabled={authBusy}>Đăng xuất</button></div>
    {:else}<span class="topbar-note">Tra cứu tài liệu</span>{/if}
  </header>

  {#if authLoading}
    <main class="auth-state" aria-live="polite">Đang kiểm tra phiên đăng nhập…</main>
  {:else if !authUser}
    <main class="auth-layout">
      <form class="auth-card" onsubmit={submitLogin}>
        <span class="welcome-mark" aria-hidden="true">R</span>
        <p class="eyebrow">RUVIE AGENT</p>
        <h1>Đăng nhập</h1>
        <p class="auth-description">Sử dụng tài khoản được cấp để truy cập tài liệu trong project của bạn.</p>
        {#if authError}<p class="auth-error" role="alert">{authError}</p>{/if}
        <label for="email">Email</label>
        <input id="email" type="email" autocomplete="username" required maxlength="320" bind:value={email} />
        <label for="password">Mật khẩu</label>
        <input id="password" type="password" autocomplete="current-password" required bind:value={password} />
        <button class="auth-submit" type="submit" disabled={authBusy}>{authBusy ? 'Đang đăng nhập…' : 'Đăng nhập'}</button>
      </form>
    </main>
  {:else}
  <main class="chat-layout">
    <section class="upload-panel" aria-labelledby="upload-heading">
      <div class="upload-heading">
        <div><p class="eyebrow">TÀI LIỆU PROJECT</p><h2 id="upload-heading">Tải tài liệu lên</h2></div>
        <p>Hỗ trợ PDF và văn bản UTF-8, tối đa 25 MiB.</p>
      </div>
      {#if projectsError}<p class="upload-error" role="alert">{projectsError} <button type="button" onclick={loadProjects}>Thử lại</button></p>{/if}
      {#if !projectsLoading && projects.length === 0 && !projectsError}
        <p class="upload-note">Bạn chưa tham gia project nào.</p>
      {:else}
        <form class="upload-form" onsubmit={submitUpload}>
          <label>Project
            <select required bind:value={selectedProjectId} disabled={projectsLoading || uploadBusy}>
              <option value="" disabled>{projectsLoading ? 'Đang tải project…' : 'Chọn project'}</option>
              {#each projects as project (project.id)}<option value={project.id}>{project.name} · {project.code}</option>{/each}
            </select>
          </label>
          <label>Tên tài liệu<input required maxlength="500" bind:value={uploadTitle} disabled={uploadBusy} /></label>
          <label>Phần mềm<input required maxlength="255" bind:value={uploadSoftware} disabled={uploadBusy} /></label>
          <label>Phiên bản<input required maxlength="255" bind:value={uploadSoftwareVersion} disabled={uploadBusy} /></label>
          <label class="upload-file">File<input required type="file" accept=".pdf,.txt,application/pdf,text/plain" onchange={(event) => (selectedFile = (event.currentTarget as HTMLInputElement).files?.[0] ?? null)} disabled={uploadBusy} /></label>
          <button class="upload-submit" type="submit" disabled={uploadBusy || projectsLoading || !projects.length || !selectedFile || !selectedProjectId}>{uploadBusy ? 'Đang tải lên…' : 'Tải lên'}</button>
        </form>
      {/if}
      {#if uploadStatus}
        <div class="upload-status" aria-live="polite">
          <span>{uploadStatusLabel(uploadStatus.status)}</span>
          {#if uploadStatus.status === 'failed' && uploadStatus.error_code}<span>Mã lỗi: {uploadStatus.error_code}</span>{/if}
          {#if (uploadTimedOut || uploadError) && uploadStatus.status !== 'ready' && uploadStatus.status !== 'failed'}{#if uploadTimedOut}<span>Việc xử lý vẫn tiếp tục ở máy chủ.</span>{/if}<button type="button" onclick={refreshUploadStatus} disabled={statusRefreshing}>{statusRefreshing ? 'Đang làm mới…' : 'Làm mới trạng thái'}</button>{/if}
        </div>
      {/if}
      {#if uploadError}<p class="upload-error" role="alert">{uploadError}</p>{/if}
    </section>
    <div class="conversation" bind:this={conversation} onscroll={handleScroll}>
      {#if turns.length === 0}
        <div class="welcome">
          <span class="welcome-mark" aria-hidden="true">R</span>
          <p class="eyebrow">RUVIE AGENT</p>
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
                  <div class="assistant-name">Ruvie Agent</div>
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
  {/if}
</div>
