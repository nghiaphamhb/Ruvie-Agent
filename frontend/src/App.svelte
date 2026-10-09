<script lang="ts">
  import { i18n } from './lib/i18n/index.ts';
  import { message as uiMessage, type UiMessage } from './lib/i18n/messages.ts';
  import { onDestroy, onMount, tick } from 'svelte';
  import LanguageSelector from './lib/components/LanguageSelector.svelte';
  import LlmConnectionForm from './lib/components/LlmConnectionForm.svelte';
  import ModelSelector from './lib/components/ModelSelector.svelte';
  import ChatConversation from './lib/components/ChatConversation.svelte';
  import ChatComposer from './lib/components/ChatComposer.svelte';
  import DocumentUploadPanel from './lib/components/DocumentUploadPanel.svelte';
  import LoginForm from './lib/components/LoginForm.svelte';
  import AppNavigation from './lib/components/AppNavigation.svelte';
  import { LlmApiError, getModels, selectLlmModel, type ModelsResult } from './lib/llm-api';
  import { ChatApiError, streamChat } from './lib/chat-api';
  import { AuthApiError, getAuthSession, login, logout, type AuthUser } from './lib/auth-api';
  import {
    DocumentsApiError, getRevisionStatus, listProjects, uploadDocument,
    type ProjectSummary, type RevisionStatus
  } from './lib/documents-api';

  import type { ChatTurn } from './lib/chat-turn';

  let activeView = $state<'chat' | 'documents' | 'llm'>('chat');
  const viewLabels = { chat: 'nav.chat', documents: 'nav.documents', llm: 'nav.llm' } as const;
  /** Change only visibility; requests and account state survive navigation. */
  async function selectView(view: 'chat' | 'documents' | 'llm') {
    activeView = view;
    await tick();
    document.querySelector<HTMLElement>('#view-heading')?.focus();
  }

  let draft = $state('');
  let turns = $state<ChatTurn[]>([]);
  let busy = $state(false);
  let llmBusy = $state(false);
  // One confirmed catalog is shared by the form, selector and chat.
  let catalog = $state<ModelsResult | null>(null);
  let modelBusy = $state(false);
  let modelError = $state<UiMessage | null>(null);
  let modelReady = $derived(Boolean(catalog && !catalog.selection_required && catalog.models.some((model) => model.id === catalog.selected_model_id)));
  let sessionSequence = 0;
  let nextTurnId = 1;
  let activeRequest: AbortController | null = null;
  let authLoading = $state(true);
  let authBusy = $state(false);
  let authUser = $state<AuthUser | null>(null);
  let csrfToken = $state('');
  let authError = $state<UiMessage | null>(null);
  let projects = $state<ProjectSummary[]>([]);
  let projectsLoading = $state(false);
  let projectsError = $state<UiMessage | null>(null);
  let selectedProjectId = $state('');
  let uploadTitle = $state('');
  let uploadSoftware = $state('');
  let uploadSoftwareVersion = $state('');
  let selectedFile = $state<File | null>(null);
  let uploadBusy = $state(false);
  let uploadError = $state<UiMessage | null>(null);
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
      authError = error instanceof AuthApiError ? error.uiMessage : uiMessage('auth.errors.session');
    } finally {
      authLoading = false;
    }
  });

  /** Authenticate supplied credentials; cookie/CSRF stay in the active API contract. */
  async function submitLogin(email: string, password: string): Promise<boolean> {
    if (authBusy) return false;
    authBusy = true;
    authError = null;
    try {
      const result = await login(email.trim(), password);
      authUser = result.user;
      csrfToken = result.csrf_token;
      await loadProjects();
      return Boolean(authUser);
    } catch (error) {
      authError = error instanceof AuthApiError ? error.uiMessage : uiMessage('auth.errors.login');
      return false;
    } finally {
      authBusy = false;
    }
  }

  /** Drop account data and invalidate responses from the previous login session. */
  function clearSession() {
    sessionSequence += 1;
    activeView = 'chat';
    activeRequest?.abort();
    activeRequest = null;
    busy = false;
    llmBusy = false;
    catalog = null;
    modelBusy = false;
    modelError = null;
    authUser = null;
    csrfToken = '';
    turns = [];
    draft = '';
    uploadSequence += 1;
    projects = [];
    projectsLoading = false;
    projectsError = null;
    selectedProjectId = '';
    uploadTitle = '';
    uploadSoftware = '';
    uploadSoftwareVersion = '';
    selectedFile = null;
    uploadBusy = false;
    uploadError = null;
    uploadStatus = null;
    uploadTimedOut = false;
    statusRefreshing = false;
  }

  /** End the cookie session; a protected 401 also discards local account data. */
  async function signOut() {
    authBusy = true;
    authError = null;
    try {
      await logout(csrfToken);
      clearSession();
    } catch (error) {
      if (error instanceof AuthApiError && error.status === 401) {clearSession(); return;}
      authError = error instanceof AuthApiError ? error.uiMessage : uiMessage('auth.errors.logout');
    } finally {
      authBusy = false;
    }
  }

  async function loadProjects() {
    const sequence = sessionSequence;
    projectsLoading = true;
    projectsError = null;
    try {
      const result = await listProjects();
      if (sequence === sessionSequence) projects = result;
    } catch (error) {
      if (sequence !== sessionSequence) return;
      if (error instanceof DocumentsApiError && error.status === 401) { clearSession(); return; }
      projectsError = uiMessage('upload.errors.projects');
    } finally {
      if (sequence === sessionSequence) projectsLoading = false;
    }
  }

  /** Upload once, then poll at 2-second intervals for at most five minutes. */
  async function submitUpload(event: SubmitEvent) {
    event.preventDefault();
    if (uploadBusy || statusRefreshing || !authUser || !selectedFile || !selectedProjectId) return;
    uploadBusy = true;
    uploadError = null;
    uploadStatus = null;
    uploadTimedOut = false;
    const sequence = ++uploadSequence;
    const session = sessionSequence;
    // Both the upload and login session must still own every response/finally.
    const isCurrent = () => sequence === uploadSequence && session === sessionSequence;
    try {
      const result = await uploadDocument(csrfToken, {
        project_id: selectedProjectId, title: uploadTitle,
        software: uploadSoftware, software_version: uploadSoftwareVersion, file: selectedFile
      });
      if (!isCurrent()) return;
      uploadStatus = {revision_id: result.revision_id, status: result.status, error_code: null};
      const deadline = Date.now() + 5 * 60 * 1000;
      while (isCurrent() && Date.now() < deadline) {
        await new Promise(resolve => setTimeout(resolve, 2000));
        if (!isCurrent()) return;
        if (Date.now() >= deadline) break;
        const status = await getRevisionStatus(result.revision_id);
        if (!isCurrent()) return;
        uploadStatus = status;
        if (status.status === 'ready' || status.status === 'failed') return;
      }
      if (isCurrent()) uploadTimedOut = true;
    } catch (error) {
      if (!isCurrent()) return;
      if (error instanceof DocumentsApiError && error.status === 401) {clearSession(); return;}
      uploadError = error instanceof DocumentsApiError && error.status === 404
        ? uiMessage('upload.errors.notFound')
        : uiMessage('upload.errors.upload');
    } finally {
      if (isCurrent()) uploadBusy = false;
    }
  }

  /** Refresh only the current revision; stale success/error cannot restore account data. */
  async function refreshUploadStatus() {
    if (!authUser || !uploadStatus || statusRefreshing || uploadBusy) return;
    const sequence = uploadSequence;
    const session = sessionSequence;
    const isCurrent = () => sequence === uploadSequence && session === sessionSequence;
    const revisionId = uploadStatus.revision_id;
    statusRefreshing = true;
    uploadError = null;
    try {
      const status = await getRevisionStatus(revisionId);
      if (isCurrent()) uploadStatus = status;
    } catch (error) {
      if (!isCurrent()) return;
      if (error instanceof DocumentsApiError && error.status === 401) {clearSession(); return;}
      uploadError = error instanceof DocumentsApiError && error.status === 404
        ? uiMessage('upload.errors.notFound')
        : uiMessage('upload.errors.refresh');
    } finally {
      if (isCurrent()) statusRefreshing = false;
    }
  }

  /** Publish a verified catalog from the connection form; no browser persistence. */
  function updateModels(result: ModelsResult | null) {
    catalog = result;
    modelError = null;
  }

  /** GET a fresh catalog; a failed refresh blocks chat until a valid model is known. */
  async function reloadModels() {
    if (!authUser || busy || llmBusy || modelBusy || authBusy) return;
    const sequence = sessionSequence;
    modelBusy = true;
    catalog = null;
    modelError = null;
    try {
      const result = await getModels();
      if (sequence === sessionSequence) catalog = result;
    } catch (error) {
      if (sequence !== sessionSequence) return;
      if (error instanceof LlmApiError && error.status === 401) { clearSession(); return; }
      modelError = error instanceof LlmApiError ? error.uiMessage : uiMessage('model.errors.load');
    } finally {
      if (sequence === sessionSequence) modelBusy = false;
    }
  }

  /** PATCH the selected ID; failed saves keep the previous confirmed model. */
  async function chooseModel(id: string): Promise<boolean> {
    if (!authUser || busy || llmBusy || modelBusy || authBusy || !catalog) return false;
    if (id === catalog.selected_model_id) return true;
    const sequence = sessionSequence;
    modelBusy = true;
    modelError = null;
    try {
      const result = await selectLlmModel(csrfToken, id);
      if (sequence !== sessionSequence) return false;
      catalog = { ...catalog, selected_model_id: result.selected_model_id, selection_required: false };
      return true;
    } catch (error) {
      if (sequence !== sessionSequence) return false;
      if (error instanceof LlmApiError && error.status === 401) { clearSession(); return false; }
      modelError = error instanceof LlmApiError ? error.uiMessage : uiMessage('model.errors.save');
      return false;
    } finally {
      if (sequence === sessionSequence) modelBusy = false;
    }
  }

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    const message = draft.trim();
    if (!message || busy || llmBusy || modelBusy || authBusy || !modelReady) return;
    const modelId = catalog!.selected_model_id!;
    let reloadAfterChat = false;
    const sequence = sessionSequence;

    const turn: ChatTurn = {
      id: nextTurnId++, question: message, answer: '', citations: [], status: 'loading', error: null
    };
    turns.push(turn);
    const activeTurn = turns[turns.length - 1];
    draft = '';
    busy = true;
    const controller = new AbortController();
    activeRequest = controller;

    try {
      await streamChat(message, (received) => {
        if (sequence !== sessionSequence) return;
        if (received.type === 'delta') {
          activeTurn.answer += received.text;
          activeTurn.status = 'streaming';
        } else if (received.type === 'citations') {
          activeTurn.citations = received.citations;
        } else {
          activeTurn.status = 'completed';
        }
      }, controller.signal, modelId);
    } catch (error) {
      if (sequence !== sessionSequence) return;
      if (error instanceof ChatApiError && error.code === 'auth_required') { clearSession(); return; }
      if (error instanceof ChatApiError && error.code === 'model_unavailable') {
        catalog = null;
        reloadAfterChat = true;
      }
      if (!controller.signal.aborted) {
        activeTurn.status = 'error';
        activeTurn.citations = [];
        activeTurn.error = error instanceof ChatApiError ? error.uiMessage : uiMessage('chat.errors.complete');
      }
    } finally {
      if (sequence === sessionSequence) {
        activeRequest = null;
        busy = false;
        if (reloadAfterChat) void reloadModels();
      }
    }
  }

  onDestroy(() => { sessionSequence += 1; activeRequest?.abort(); uploadSequence += 1; });
</script>

<svelte:head>
  <title>{$i18n.t('page.title')}</title>
  <meta name="description" content={$i18n.t('page.description')} />
</svelte:head>

<div class="app-shell">
  {#if !authUser}
    <header class="topbar"><div class="brand"><span class="brand-mark" aria-hidden="true">R</span><span>Ruvie Agent</span></div><LanguageSelector id="login-language" /></header>
  {/if}

  {#if authLoading}
    <main class="auth-state" aria-live="polite">{$i18n.t('auth.checking')}</main>
  {:else if !authUser}
    <main class="auth-layout">
      <LoginForm busy={authBusy} error={authError} onlogin={submitLogin} />
    </main>
  {:else}
  <div class="workspace">
    <AppNavigation {activeView} accountName={authUser.display_name} busy={authBusy} onselect={selectView} onlogout={signOut} />
    <main class="workspace-content">
      <header class="workspace-header">
        <h1 id="view-heading" tabindex="-1">{$i18n.t(viewLabels[activeView])}</h1>
        <div hidden={activeView !== 'chat'}>
          <ModelSelector {catalog} loading={modelBusy || llmBusy}
            disabled={busy || authBusy || activeView !== 'chat'} error={modelError} onselect={chooseModel} onreload={reloadModels} />
        </div>
      </header>
      {#if authError}<p class="auth-error" role="alert">{$i18n.message(authError)}</p>{/if}
      <div class="view-panel" hidden={activeView !== 'documents'}>
        <DocumentUploadPanel {projects} {projectsLoading} {projectsError}
          bind:selectedProjectId bind:uploadTitle bind:uploadSoftware bind:uploadSoftwareVersion bind:selectedFile
          {uploadBusy} {uploadError} {uploadStatus} {uploadTimedOut} {statusRefreshing}
          onsubmit={submitUpload} onrefresh={refreshUploadStatus} onprojectsreload={loadProjects} />
      </div>
      <div class="view-panel" hidden={activeView !== 'llm'}>
    {#key authUser.id + csrfToken}
      <LlmConnectionForm {csrfToken} disabled={busy || modelBusy || authBusy}
        onexpired={clearSession} onbusychange={(value) => { llmBusy = value; }} onmodelschange={updateModels} />
    {/key}
      </div>
      <section class="view-panel chat-view" aria-label={$i18n.t('nav.chat')} hidden={activeView !== 'chat'}>
        {#if !modelReady && !llmBusy && !modelBusy}
          <div class="connection-prompt"><button type="button" onclick={() => selectView('llm')}>{$i18n.t('nav.llm')}</button></div>
        {/if}
    <ChatConversation {turns} visible={activeView === 'chat'} />
    <ChatComposer {draft} disabled={busy || llmBusy || modelBusy || authBusy || !modelReady}
      oninput={(value) => { draft = value; }} onsubmit={submit} />

      </section>
    </main>
  </div>
  {/if}
</div>
