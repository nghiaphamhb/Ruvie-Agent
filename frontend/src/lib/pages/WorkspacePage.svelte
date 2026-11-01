<script lang="ts">
  import { i18n } from '../i18n/index.ts';
  import { toast } from 'svelte-sonner';
  import ModelSelector from '../features/llm/ModelSelector.svelte';
  import type { UiMessage } from '../i18n/messages.ts';
  import { onDestroy, onMount, tick, untrack } from 'svelte';
  import { getAuthSession, type AuthUser } from '../features/auth/auth-api.ts';
  import { startPresence } from '../features/auth/presence.ts';
  import { message } from '../i18n/messages.ts';
  import AdminPage from './AdminPage.svelte';
  import { createChatState } from '../features/chat/chat-state.svelte.ts';
  import { createDocumentsState } from '../features/documents/documents-state.svelte.ts';
  import { createLlmState } from '../features/llm/llm-state.svelte.ts';
  import { createOrganizationLlmState } from '../features/llm/organization-llm-state.svelte.ts';
  import { createEmbeddingState } from '../features/embedding/embedding-state.svelte.ts';
  import EmbeddingConnectionForm from '../features/embedding/EmbeddingConnectionForm.svelte';
  import LlmConnectionForm from '../features/llm/LlmConnectionForm.svelte';
  import ProjectsPage from '../features/documents/ProjectsPage.svelte';
  import DocumentsPage from '../features/documents/DocumentsPage.svelte';
  import DocumentUploadPanel from '../features/documents/DocumentUploadPanel.svelte';
  import DocumentSearchPage from '../features/documents/DocumentSearchPage.svelte';
  import UploadSurface from '../features/documents/UploadSurface.svelte';
  import FeaturePlaceholder from '../shared/FeaturePlaceholder.svelte';
  import AppSidebar, { type WorkspaceView } from '../layout/AppSidebar.svelte';
  import WorkspaceShell from '../layout/WorkspaceShell.svelte';
  import SettingsPanel from '../features/settings/SettingsPanel.svelte';
  import { createThemeState } from '../features/settings/theme.ts';
  import ChatControlsPanel from '../features/chat/ChatControlsPanel.svelte';
  import ConversationList from '../features/chat/ConversationList.svelte';
  import SurfaceDialog from '../shared/SurfaceDialog.svelte';
  import ChatPage from '../features/chat/ChatPage.svelte';
  let {
    authUser,
    csrfToken,
    authBusy,
    authError,
    onlogout,
    onexpired,
  }: {
    authUser: AuthUser;
    csrfToken: string;
    authBusy: boolean;
    authError: UiMessage | null;
    onlogout: () => void;
    onexpired: (notice?: UiMessage) => void;
  } = $props();
  let activeView = $state<WorkspaceView>('chat'),
    sidebarCollapsed = $state(false);
  let retainedAdminView = $state<'admin-users' | 'admin-settings' | null>(null);
  let accountName = $state(untrack(() => authUser.display_name));
  let controlsOpen = $state(false),
    uploadOpen = $state(false);
  let uploadInline = $state<HTMLDivElement>();
  const viewLabels = {
    chat: 'nav.chat',
    search: 'workspace.search',
    notes: 'workspace.notes',
    workspace: 'workspace.library',
    projects: 'workspace.projects',
    documents: 'nav.documents',
    folders: 'workspace.folders',
    history: 'workspace.conversations',
    settings: 'workspace.settings',
    'admin-users': 'admin.users',
    'admin-settings': 'admin.systemSettings',
  } as const;
  let adminRevoked = $state(false);
  const canAdmin = $derived(authUser.system_role === 'admin' && !adminRevoked);
  let navigationNotice = $state<UiMessage | null>(null);
  // Navigation reads can finish after logout or a newer Back/Forward action.
  let navigationGeneration = 0,
    viewRestoreSequence = 0;
  let chatNotice = $state<{ key: 'chat.configureModel' | 'chat.modelsLoading'; id: number } | null>(
    null,
  );
  let noticeId = 0;
  function showChatNotice(key: 'chat.configureModel' | 'chat.modelsLoading') {
    chatNotice = { key, id: ++noticeId };
  }
  $effect(() => {
    const notice = chatNotice;
    if (!notice) return;
    toast.error($i18n.t(notice.key), {
      id: 'chat-model-notice',
      onDismiss: () => {
        chatNotice = null;
      },
      onAutoClose: () => {
        chatNotice = null;
      },
    });
  });
  onDestroy(() => toast.dismiss('chat-model-notice'));
  function submitChat(event: SubmitEvent) {
    event.preventDefault();
    if (authBusy || chat.busy || !chat.draft.trim()) return;
    if (llm.loading || llm.modelBusy) {
      showChatNotice('chat.modelsLoading');
      return;
    }
    void chat.submit();
  }
  let selectedModel = $derived(
    llm.catalog?.selection_required
      ? undefined
      : llm.catalog?.models.find((model) => model.id === llm.catalog?.selected_model_id),
  );
  let expired = false,
    workspaceDisposed = false;
  let presence: ReturnType<typeof startPresence> | undefined;
  const sessionCsrf = untrack(() => csrfToken);
  const theme = createThemeState(untrack(() => authUser.id));
  const llm = createLlmState({
    csrfToken: sessionCsrf,
    onexpired: clearSession,
    isLocked: () => chat.busy || authBusy,
  });
  const organizationLlm = createOrganizationLlmState({
    csrfToken: sessionCsrf,
    onexpired: clearSession,
    onforbidden: () => {
      void lostAdminAccess();
    },
    onapplied: () => {
      void llm.reloadConnection();
    },
  });
  let aiConnection = $state<'reply' | 'embedding'>('reply');
  const embedding = createEmbeddingState({
    csrfToken: sessionCsrf,
    onexpired: clearSession,
    onforbidden: () => {
      void lostAdminAccess();
    },
    onapplied: () => {},
  });
  const chat = createChatState({
    csrfToken: sessionCsrf,
    onaccepted: (id) => setConversationUrl(id, 'replace'),
    onexpired: clearSession,
    getCatalog: () => llm.catalog,
    isLocked: () => llm.loading || llm.modelBusy || authBusy,
    onMissingModel: () => showChatNotice('chat.configureModel'),
    onModelUnavailable: () => {
      void llm.reloadModels();
    },
  });
  const documents = createDocumentsState({ csrfToken: sessionCsrf, onexpired: clearSession });
  /** Invalidate all request owners before App removes this account's workspace. */
  function dispose() {
    workspaceDisposed = true;
    finishSwitch(false);
    presence?.dispose();
    navigationGeneration++;
    viewRestoreSequence++;
    chat.dispose();
    documents.dispose();
    llm.dispose();
    organizationLlm.dispose();
    embedding.dispose();
    theme.dispose();
  }
  function clearSession(notice?: UiMessage) {
    if (expired) return;
    expired = true;
    dispose();
    onexpired(notice);
  }
  onMount(() => {
    presence = startPresence(sessionCsrf, clearSession);
    const updateAccount = (event: Event) => {
      const user = (
        event as CustomEvent<{
          id: string;
          display_name: string;
          system_role: 'user' | 'admin';
          password_changed?: boolean;
        }>
      ).detail;
      if (user?.id !== authUser.id) return;
      if (user.password_changed) {
        clearSession();
        return;
      }
      if (typeof user.display_name === 'string') accountName = user.display_name;
      if (user.system_role === 'user' && authUser.system_role === 'admin') lostAdminAccess();
    };
    window.addEventListener('ruvie:account-updated', updateAccount);
    void restoreView(false);
    void documents.loadProjects();
    void llm.initialize();
    void chat.loadList();
    return () => window.removeEventListener('ruvie:account-updated', updateAccount);
  });
  onDestroy(dispose);
  function toggleSidebar() {
    sidebarCollapsed = !sidebarCollapsed;
  }
  function openSettings() {
    void selectView('settings');
  }
  function closeControls() {
    controlsOpen = false;
    document.querySelector<HTMLButtonElement>('.chat-controls-trigger')?.focus();
  }
  /** View query selects presentation only; fresh server identity gates admin mounting. */
  async function selectView(
    view: WorkspaceView,
    mode: 'push' | 'replace' = 'push',
    moveFocus = true,
    restoring = false,
  ) {
    if (expired || workspaceDisposed) return;
    if (!restoring) viewRestoreSequence++;
    const current = ++navigationGeneration;
    navigationNotice = null;
    if (view === 'admin-users' || view === 'admin-settings') {
      if (!canAdmin) {
        view = 'chat';
        mode = 'replace';
        navigationNotice = message('admin.errors.admin_required');
      } else {
        try {
          const session = await getAuthSession();
          if (current !== navigationGeneration || expired) return;
          if (!session || session.user.id !== authUser.id || session.csrf_token !== sessionCsrf) {
            clearSession();
            return;
          }
          if (session.user.system_role !== 'admin') {
            adminRevoked = true;
            view = 'chat';
            mode = 'replace';
            navigationNotice = message('admin.errors.admin_required');
          }
        } catch {
          if (current !== navigationGeneration || expired) return;
          view = 'chat';
          mode = 'replace';
          navigationNotice = message('admin.errors.sessionCheck');
        }
      }
    }
    const url = new URL(window.location.href);
    if (view === 'chat') url.searchParams.delete('view');
    else url.searchParams.set('view', view);
    if (url.href !== window.location.href) {
      if (mode === 'replace') history.replaceState({}, '', url);
      else history.pushState({}, '', url);
    }
    // Personal settings preserve an open admin form; other destinations dispose it.
    if (view === 'admin-users' || view === 'admin-settings') retainedAdminView = view;
    else if (view !== 'settings') retainedAdminView = null;
    activeView = view;
    uploadOpen = false;
    await tick();
    if (!moveFocus || current !== navigationGeneration || expired) return;
    const heading = [
      ...document.querySelectorAll<HTMLElement>(
        '.view-panel:not([hidden]) [data-view-heading],.view-panel:not([hidden]) #question',
      ),
    ].find((element) => element.getClientRects().length > 0);
    heading?.focus();
  }
  function setConversationUrl(id: string, mode: 'push' | 'replace' = 'push') {
    const url = new URL(window.location.href);
    if (id) url.searchParams.set('conversation', id);
    else url.searchParams.delete('conversation');
    if (url.href !== window.location.href) {
      if (mode === 'push') history.pushState({}, '', url);
      else history.replaceState({}, '', url);
    }
  }
  let switchConfirm = $state(false);
  let resolveSwitch: ((proceed: boolean) => void) | null = null;
  function finishSwitch(proceed: boolean) {
    switchConfirm = false;
    resolveSwitch?.(proceed);
    resolveSwitch = null;
  }
  async function maySwitch() {
    if (workspaceDisposed || expired) return false;
    if (!chat.busy) return true;
    if (resolveSwitch) return false;
    const proceed = await new Promise<boolean>((resolve) => {
      resolveSwitch = resolve;
      switchConfirm = true;
    });
    if (!proceed) return false;
    await chat.stop();
    return !chat.busy && !expired && !workspaceDisposed;
  }
  async function openConversation(id: string) {
    if (id === chat.conversationId) {
      await selectView('chat');
      return;
    }
    if (!(await maySwitch())) return;
    const url = new URL(window.location.href);
    url.searchParams.delete('view');
    url.searchParams.set('conversation', id);
    history.pushState({}, '', url);
    await selectView('chat');
    await chat.open(id);
  }
  async function restoreView(moveFocus = true) {
    const current = ++viewRestoreSequence;
    const params = new URL(window.location.href).searchParams;
    const query = params.get('view'),
      id = params.get('conversation');
    const view = query && Object.hasOwn(viewLabels, query) ? (query as WorkspaceView) : 'chat';
    if (id !== chat.conversationId) {
      if (!(await maySwitch())) {
        if (current !== viewRestoreSequence || workspaceDisposed) return;
        setConversationUrl(chat.conversationId ?? '', 'replace');
        await selectView(activeView, 'replace', false, true);
        return;
      }
      if (current !== viewRestoreSequence || workspaceDisposed) return;
      if (id) await chat.open(id);
      else chat.reset();
    }
    if (current !== viewRestoreSequence || workspaceDisposed) return;
    setConversationUrl(chat.conversationId ?? '', 'replace');
    await selectView(view, 'replace', moveFocus, true);
  }
  async function lostAdminAccess() {
    let session;
    try {
      session = await getAuthSession();
    } catch {
      navigationNotice = message('admin.errors.sessionCheck');
      return;
    }
    if (!session || session.user.id !== authUser.id || session.csrf_token !== sessionCsrf) {
      clearSession();
      return;
    }
    if (session.user.system_role === 'admin') {
      navigationNotice = message('admin.errors.admin_required');
      return;
    }
    adminRevoked = true;
    await selectView('chat', 'replace');
    navigationNotice = message('admin.errors.admin_required');
  }
  async function newChat() {
    if (!(await maySwitch())) return;
    chat.reset();
    const url = new URL(window.location.href);
    url.searchParams.delete('conversation');
    url.searchParams.delete('view');
    if (url.href !== window.location.href) history.pushState({}, '', url);
    await selectView('chat');
    document.getElementById('question')?.focus();
  }
  async function selectProject(id: string) {
    if (!documents.projects.some((project) => project.id === id)) return;
    documents.selectedProjectId = id;
    await selectView('documents');
  }
</script>

<svelte:window
  onpopstate={() => {
    void restoreView();
  }}
/>
<WorkspaceShell
  theme={$theme.resolved}
  collapsed={sidebarCollapsed}
  oncontrols={() => {
    controlsOpen = !controlsOpen;
  }}
>
  {#snippet toolbar()}
    {#if activeView === 'chat'}
      {#if llm.catalog?.models.length}
        <div class="chat-model-shortcut">
          <ModelSelector
            toolbar
            id="chat-model"
            catalog={llm.catalog}
            loading={llm.loading || llm.modelBusy}
            disabled={chat.busy || authBusy}
            error={llm.modelError}
            onselect={llm.chooseModel}
            onreload={llm.reloadModels}
          />
        </div>
      {:else}
        <button
          class="chat-model-shortcut"
          type="button"
          disabled={llm.loading || llm.modelBusy}
          onclick={() => (canAdmin ? selectView('admin-settings') : llm.reloadConnection())}
          title={canAdmin
            ? (selectedModel?.name ?? $i18n.t('chat.modelNotSelected'))
            : $i18n.t('model.connectFirst')}
          aria-label={$i18n.t('chat.configureModelLabel', {
            model: selectedModel?.name ?? $i18n.t('chat.modelNotSelected'),
          })}
        >
          <span
            >{llm.loading || llm.modelBusy
              ? $i18n.t('chat.modelsLoadingLabel')
              : (selectedModel?.name ?? $i18n.t('chat.modelNotSelected'))}</span
          >
          {#if !selectedModel}<span aria-hidden="true">+</span>{/if}
        </button>
      {/if}
    {/if}
  {/snippet}
  {#snippet sidebar()}<AppSidebar
      {activeView}
      {accountName}
      {canAdmin}
      busy={authBusy}
      collapsed={sidebarCollapsed}
      onselect={selectView}
      onnewchat={() => {
        void newChat();
      }}
      ontoggle={toggleSidebar}
      onsettings={() => openSettings()}
      {onlogout}
      >{#snippet conversations()}<ConversationList
          state={chat}
          onselect={openConversation}
        />{/snippet}</AppSidebar
    >{/snippet}
  {#if authError}<p class="auth-error" role="alert">{$i18n.message(authError)}</p>{/if}
  {#if navigationNotice}<p role="alert">{$i18n.message(navigationNotice)}</p>{/if}
  {#if retainedAdminView && canAdmin}
    <div class="view-panel" hidden={activeView === 'settings'}>
      <AdminPage
        actorUserId={authUser.id}
        csrfToken={sessionCsrf}
        onexpired={clearSession}
        onforbidden={lostAdminAccess}
        view={retainedAdminView}
        active={activeView !== 'settings'}
        onselect={(view) => selectView(view, 'push', false)}
      >
        {#snippet settings()}
          <SettingsPanel
            {theme}
            system
            active={activeView === 'admin-settings' && canAdmin}
            bind:connection={aiConnection}
          >
            <div hidden={aiConnection !== 'reply'}>
              <LlmConnectionForm
                state={organizationLlm}
                visible={aiConnection === 'reply'}
                active={activeView === 'admin-settings' && canAdmin}
                disabled={chat.busy || authBusy}
              />
            </div>
            <div hidden={aiConnection !== 'embedding'}>
              <EmbeddingConnectionForm
                state={embedding}
                active={activeView === 'admin-settings' && canAdmin}
                visible={aiConnection === 'embedding'}
                disabled={chat.busy || authBusy}
              />
            </div>
          </SettingsPanel>
        {/snippet}
      </AdminPage>
    </div>
  {/if}
  <div class="view-panel" hidden={activeView !== 'settings'}>
    <SettingsPanel
      {theme}
      csrfToken={sessionCsrf}
      active={activeView === 'settings'}
      onexpired={(notice) => {
        clearSession(notice);
      }}
    />
  </div>
  <SurfaceDialog
    open={switchConfirm}
    title={$i18n.t('history.switchTitle')}
    onclose={() => finishSwitch(false)}
  >
    <p>{$i18n.t('history.switchText')}</p>
    <button class="history-control" data-dialog-initial-focus onclick={() => finishSwitch(false)}
      >{$i18n.t('history.cancel')}</button
    >
    <button class="history-control" onclick={() => finishSwitch(true)}
      >{$i18n.t('history.stopSwitch')}</button
    >
  </SurfaceDialog>
  <div class="view-panel" hidden={activeView !== 'history'}>
    <h1 data-history-heading tabindex="-1">{$i18n.t('workspace.conversations')}</h1>
    <ConversationList state={chat} onselect={openConversation} />
  </div>
  <div class="view-panel chat-view" hidden={activeView !== 'chat'}>
    {#if chat.loading}<p role="status">{$i18n.t('history.loading')}</p>{/if}
    {#if chat.historyError}<p role="alert">{$i18n.t('history.error')}</p>{/if}
    {#if chat.historyError && chat.conversationId}<button
        disabled={chat.loading}
        onclick={() => chat.open(chat.conversationId!)}>{$i18n.t('history.refresh')}</button
      >{/if}
    <ChatPage
      name={accountName}
      hasOlder={!!chat.olderCursor}
      olderLoading={chat.loading}
      onolder={() => chat.open(chat.conversationId!, true)}
      turns={chat.turns}
      draft={chat.draft}
      busy={chat.busy}
      visible={activeView === 'chat'}
      catalog={llm.catalog}
      disabled={chat.busy || chat.loading || authBusy}
      modelDisabled={chat.busy || authBusy}
      modelLoading={llm.modelBusy || llm.loading}
      oninput={(value) => {
        chat.draft = value;
      }}
      onsubmit={submitChat}
      onstop={chat.stop}
      onretry={chat.retry}
      onattach={() => {
        uploadOpen = true;
      }}
    />
  </div>
  <div class="view-panel" hidden={activeView !== 'documents'}>
    <DocumentsPage><div bind:this={uploadInline}></div></DocumentsPage>
  </div>
  <div class="view-panel" hidden={activeView !== 'projects'}>
    <ProjectsPage
      projects={documents.projects}
      loading={documents.projectsLoading}
      error={documents.projectsError}
      onreload={documents.loadProjects}
      onselect={selectProject}
    />
  </div>
  <div class="view-panel" hidden={activeView !== 'search'}>
    <DocumentSearchPage state={documents} />
  </div>
  {#if !['history', 'chat', 'documents', 'projects', 'search', 'settings', 'admin-users', 'admin-settings'].includes(activeView)}<div
      class="view-panel"
    >
      <FeaturePlaceholder view={activeView} title={viewLabels[activeView]} />
    </div>{/if}
  <UploadSurface
    open={uploadOpen}
    inlineVisible={activeView === 'documents'}
    inlineTarget={uploadInline}
    onclose={() => {
      uploadOpen = false;
    }}
  >
    <DocumentUploadPanel
      projects={documents.projects}
      projectsLoading={documents.projectsLoading}
      projectsError={documents.projectsError}
      bind:selectedProjectId={documents.selectedProjectId}
      bind:uploadTitle={documents.uploadTitle}
      bind:uploadSoftware={documents.uploadSoftware}
      bind:uploadSoftwareVersion={documents.uploadSoftwareVersion}
      bind:selectedFile={documents.selectedFile}
      uploadBusy={documents.uploadBusy}
      uploadError={documents.uploadError}
      uploadStatus={documents.uploadStatus}
      uploadTimedOut={documents.uploadTimedOut}
      statusRefreshing={documents.statusRefreshing}
      onsubmit={documents.submitUpload}
      onrefresh={documents.refreshUploadStatus}
      onprojectsreload={documents.loadProjects}
    />
  </UploadSurface>
  <ChatControlsPanel
    open={controlsOpen}
    modelName={llm.catalog?.models.find((item) => item.id === llm.catalog?.selected_model_id)
      ?.name ?? ''}
    onclose={closeControls}
  />
</WorkspaceShell>
