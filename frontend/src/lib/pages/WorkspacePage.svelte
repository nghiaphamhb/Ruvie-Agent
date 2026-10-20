<script lang="ts">
  import {i18n} from '../i18n/index.ts';
  import {toast} from 'svelte-sonner';
  import ModelSelector from '../features/llm/ModelSelector.svelte';
  import type {UiMessage} from '../i18n/messages.ts';
  import {onDestroy,onMount,tick,untrack} from 'svelte';
  import type {AuthUser} from '../features/auth/auth-api.ts';
  import {createChatState} from '../features/chat/chat-state.svelte.ts';
  import {createDocumentsState} from '../features/documents/documents-state.svelte.ts';
  import {createLlmState} from '../features/llm/llm-state.svelte.ts';
  import LlmConnectionForm from '../features/llm/LlmConnectionForm.svelte';
  import ProjectsPage from '../features/documents/ProjectsPage.svelte';
  import DocumentsPage from '../features/documents/DocumentsPage.svelte';
  import DocumentUploadPanel from '../features/documents/DocumentUploadPanel.svelte';
  import DocumentSearchPage from '../features/documents/DocumentSearchPage.svelte';
  import UploadSurface from '../features/documents/UploadSurface.svelte';
  import FeaturePlaceholder from '../shared/FeaturePlaceholder.svelte';
  import AppSidebar,{type WorkspaceView} from '../layout/AppSidebar.svelte';
  import WorkspaceShell from '../layout/WorkspaceShell.svelte';
  import SettingsModal from '../features/settings/SettingsModal.svelte';
  import {createThemeState} from '../features/settings/theme.ts';
  import ChatControlsPanel from '../features/chat/ChatControlsPanel.svelte';
  import ChatPage from '../features/chat/ChatPage.svelte';
  let {authUser,csrfToken,authBusy,authError,onlogout,onexpired}:{
    authUser:AuthUser;csrfToken:string;authBusy:boolean;authError:UiMessage|null;onlogout:()=>void;onexpired:()=>void;
  }=$props();
  let activeView=$state<WorkspaceView>('chat'),sidebarCollapsed=$state(false),sidebarMobileOpen=$state(false);
  let settingsOpen=$state(false),settingsTab=$state<'general'|'llm'|'appearance'>('general'),controlsOpen=$state(false),uploadOpen=$state(false);
  let uploadInline=$state<HTMLDivElement>();
  const viewLabels={chat:'nav.chat',search:'workspace.search',notes:'workspace.notes',workspace:'workspace.library',projects:'workspace.projects',documents:'nav.documents',folders:'workspace.folders',history:'workspace.conversations'} as const;
  let chatNotice=$state<{key:'chat.configureModel'|'chat.modelsLoading';id:number}|null>(null);
  let noticeId=0;
  function showChatNotice(key:'chat.configureModel'|'chat.modelsLoading'){chatNotice={key,id:++noticeId};}
  $effect(()=>{
    const notice=chatNotice;
    if(!notice)return;
    toast.error($i18n.t(notice.key),{id:'chat-model-notice',onDismiss:()=>{chatNotice=null;},onAutoClose:()=>{chatNotice=null;}});
  });
  onDestroy(()=>toast.dismiss('chat-model-notice'));
  function submitChat(event:SubmitEvent){
    event.preventDefault();
    if(authBusy||chat.busy||!chat.draft.trim())return;
    if(llm.loading||llm.modelBusy){showChatNotice('chat.modelsLoading');return;}
    void chat.submit();
  }
  let selectedModel=$derived(llm.catalog?.selection_required?undefined:llm.catalog?.models.find(model=>model.id===llm.catalog?.selected_model_id));
  let expired=false;
  const sessionCsrf=untrack(()=>csrfToken);
  const theme=createThemeState(untrack(()=>authUser.id));
  const llm=createLlmState({csrfToken:sessionCsrf,onexpired:clearSession,isLocked:()=>chat.busy||authBusy});
  const chat=createChatState({onexpired:clearSession,getCatalog:()=>llm.catalog,isLocked:()=>llm.loading||llm.modelBusy||authBusy,onMissingModel:()=>showChatNotice('chat.configureModel'),onModelUnavailable:()=>{void llm.reloadModels();}});
  const documents=createDocumentsState({csrfToken:sessionCsrf,onexpired:clearSession});
  /** Invalidate all request owners before App removes this account's workspace. */
  function dispose(){chat.dispose();documents.dispose();llm.dispose();theme.dispose();}
  function clearSession(){if(expired)return;expired=true;dispose();onexpired();}
  onMount(()=>{void documents.loadProjects();void llm.initialize();});
  onDestroy(dispose);
  async function toggleSidebar(){
    if(innerWidth<=800){sidebarMobileOpen=!sidebarMobileOpen;if(!sidebarMobileOpen){await tick();document.querySelector<HTMLButtonElement>('.sidebar-open')?.focus();}}
    else sidebarCollapsed=!sidebarCollapsed;
  }
  function resizeWorkspace(){if(innerWidth>800)sidebarMobileOpen=false;}
  function openSettings(tab:'general'|'llm'='general'){sidebarMobileOpen=false;settingsTab=tab;settingsOpen=true;}
  function closeControls(){controlsOpen=false;document.querySelector<HTMLButtonElement>('.chat-controls-trigger')?.focus();}
  async function closeSettings(){
    settingsOpen=false;await tick();
    document.querySelector<HTMLButtonElement>(innerWidth<=800?'.sidebar-open':'.account-trigger')?.focus();
  }
  async function selectView(view:WorkspaceView){
    activeView=view;sidebarMobileOpen=false;uploadOpen=false;await tick();
    document.querySelector<HTMLElement>('.view-panel:not([hidden]) [data-view-heading],.view-panel:not([hidden]) #question')?.focus();
  }
  async function newChat(){chat.reset();await selectView('chat');document.getElementById('question')?.focus();}
  async function selectProject(id:string){
    if(!documents.projects.some(project=>project.id===id))return;
    documents.selectedProjectId=id;await selectView('documents');
  }
</script>
<svelte:window onresize={resizeWorkspace}/>
<WorkspaceShell theme={$theme.resolved} collapsed={sidebarCollapsed} mobileOpen={sidebarMobileOpen} ontoggle={toggleSidebar} onclose={()=>{sidebarMobileOpen=false;}} oncontrols={()=>{controlsOpen=!controlsOpen;}}>
  {#snippet toolbar()}
    {#if activeView==='chat'}
      {#if llm.catalog?.models.length}
        <div class="chat-model-shortcut">
          <ModelSelector toolbar id="chat-model" catalog={llm.catalog} loading={llm.loading||llm.modelBusy} disabled={chat.busy||authBusy} error={llm.modelError} onselect={llm.chooseModel} onreload={llm.reloadModels}/>
        </div>
      {:else}
      <button class="chat-model-shortcut" type="button" onclick={()=>openSettings('llm')} title={selectedModel?.name??$i18n.t('chat.modelNotSelected')} aria-label={$i18n.t('chat.configureModelLabel',{model:selectedModel?.name??$i18n.t('chat.modelNotSelected')})}>
        <span>{llm.loading||llm.modelBusy?$i18n.t('chat.modelsLoadingLabel'):selectedModel?.name??$i18n.t('chat.modelNotSelected')}</span>
        {#if !selectedModel}<span aria-hidden="true">+</span>{/if}
      </button>
      {/if}
    {/if}
  {/snippet}
  {#snippet sidebar()}<AppSidebar {activeView} accountName={authUser.display_name} busy={authBusy} collapsed={sidebarCollapsed&&!sidebarMobileOpen}
    onselect={selectView} onnewchat={()=>{void newChat();}} ontoggle={toggleSidebar} onsettings={()=>openSettings()} onlogout={onlogout}/>{/snippet}
  {#if authError}<p class="auth-error" role="alert">{$i18n.message(authError)}</p>{/if}
  <div class="view-panel chat-view" hidden={activeView!=='chat'}>
    <ChatPage name={authUser.display_name} turns={chat.turns} draft={chat.draft} busy={chat.busy} visible={activeView==='chat'} catalog={llm.catalog}
      disabled={chat.busy||authBusy} modelDisabled={chat.busy||authBusy} modelLoading={llm.modelBusy||llm.loading}
      oninput={value=>{chat.draft=value;}} onsubmit={submitChat} onstop={chat.stop} onretry={chat.retry} onattach={()=>{uploadOpen=true;}}
/>
  </div>
  <div class="view-panel" hidden={activeView!=='documents'}><DocumentsPage><div bind:this={uploadInline}></div></DocumentsPage></div>
  <div class="view-panel" hidden={activeView!=='projects'}><ProjectsPage projects={documents.projects} loading={documents.projectsLoading} error={documents.projectsError} onreload={documents.loadProjects} onselect={selectProject}/></div>
  <div class="view-panel" hidden={activeView!=='search'}><DocumentSearchPage state={documents}/></div>
  {#if !['chat','documents','projects','search'].includes(activeView)}<div class="view-panel"><FeaturePlaceholder view={activeView} title={viewLabels[activeView]}/></div>{/if}
  <UploadSurface open={uploadOpen} inlineVisible={activeView==='documents'} inlineTarget={uploadInline} onclose={()=>{uploadOpen=false;}}>
    <DocumentUploadPanel projects={documents.projects} projectsLoading={documents.projectsLoading} projectsError={documents.projectsError}
      bind:selectedProjectId={documents.selectedProjectId} bind:uploadTitle={documents.uploadTitle} bind:uploadSoftware={documents.uploadSoftware}
      bind:uploadSoftwareVersion={documents.uploadSoftwareVersion} bind:selectedFile={documents.selectedFile}
      uploadBusy={documents.uploadBusy} uploadError={documents.uploadError} uploadStatus={documents.uploadStatus} uploadTimedOut={documents.uploadTimedOut}
      statusRefreshing={documents.statusRefreshing} onsubmit={documents.submitUpload} onrefresh={documents.refreshUploadStatus} onprojectsreload={documents.loadProjects}/>
  </UploadSurface>
  <ChatControlsPanel open={controlsOpen} modelName={llm.catalog?.models.find(item=>item.id===llm.catalog?.selected_model_id)?.name??''} onclose={closeControls}/>
  <SettingsModal {theme} open={settingsOpen} bind:tab={settingsTab} onclose={()=>{void closeSettings();}}>
    <LlmConnectionForm state={llm} disabled={chat.busy||authBusy}/>
    <ModelSelector catalog={llm.catalog} loading={llm.loading||llm.modelBusy} disabled={chat.busy||authBusy} error={llm.modelError} onselect={llm.chooseModel} onreload={llm.reloadModels}/>
  </SettingsModal>
</WorkspaceShell>
