<script module lang="ts">
  export type WorkspaceView='chat'|'search'|'notes'|'workspace'|'projects'|'documents'|'folders'|'history';
</script>
<script lang="ts">
  import {i18n} from '../i18n/index.ts';
  import logo from '../assets/brand/ruvie-logo.png';
  import WorkspaceIcon from '../shared/WorkspaceIcon.svelte';
  import AccountMenu from './AccountMenu.svelte';
  // Brand, navigation sections and account positioning adapted from references/layout/Sidebar.svelte.
  let {activeView,accountName,busy,collapsed,onselect,onnewchat,ontoggle,onsettings,onlogout}: {
    activeView:WorkspaceView;accountName:string;busy:boolean;collapsed:boolean;
    onselect:(view:WorkspaceView)=>void;onnewchat:()=>void;ontoggle:()=>void;onsettings:()=>void;onlogout:()=>void;
  }=$props();
  const items=[{id:'chat',label:'workspace.newChat'},{id:'search',label:'workspace.search'},{id:'notes',label:'workspace.notes'},
    {id:'workspace',label:'workspace.library'},{id:'projects',label:'workspace.projects'},{id:'documents',label:'nav.documents'}] as const;
</script>
<nav class="sidebar-nav" class:nav-collapsed={collapsed} aria-label={$i18n.t('nav.main')}>
  <div class="sidebar-heading">
    <button class="sidebar-brand" type="button" aria-label={$i18n.t('nav.chat')} onclick={()=>onselect('chat')}><img class="brand-full" src={logo} alt="" /><img class="brand-mark" src="/favicon.svg" alt="" /></button>
    <button class="sidebar-collapse" type="button" aria-label={$i18n.t(collapsed?'workspace.openSidebar':'workspace.collapseSidebar')} onclick={ontoggle}><WorkspaceIcon name="collapse"/></button>
  </div>
  <div class="sidebar-links">
    {#each items as item}
      <button type="button" aria-label={$i18n.t(item.label)} aria-current={activeView===item.id?'page':undefined} title={$i18n.t(item.label)}
        onclick={()=>item.id==='chat'?onnewchat():onselect(item.id)}><WorkspaceIcon name={item.id}/><span class="nav-label">{$i18n.t(item.label)}</span></button>
    {/each}
  </div>
  <div class="sidebar-sections" inert={collapsed} aria-hidden={collapsed}>
    <div class="section-heading"><span>{$i18n.t('workspace.folders')}</span><button type="button" aria-label={$i18n.t('workspace.addFolder')} onclick={()=>onselect('folders')}><WorkspaceIcon name="plus" size={18}/></button></div>
    <p>{$i18n.t('workspace.emptyFolders')}</p>
    <div class="section-heading"><span>{$i18n.t('workspace.conversations')}</span><button type="button" aria-label={$i18n.t('workspace.conversationMenu')} onclick={()=>onselect('history')}><WorkspaceIcon name="dots" size={18}/></button></div>
    <p>{$i18n.t('workspace.emptyConversations')}</p>
  </div>
  <div class="sidebar-account"><AccountMenu name={accountName} {busy} {collapsed} {onsettings} {onlogout}/></div>
</nav>
<style>
  .sidebar-nav{display:flex;flex-direction:column;height:100%;padding:12px;gap:16px;}
  .sidebar-heading{display:flex;align-items:center;justify-content:space-between;gap:6px;min-height:48px;}
  .sidebar-brand{min-width:0;padding:8px;border:0;background:transparent;}
  .sidebar-brand img{width:144px;max-width:100%;height:auto;filter:brightness(0) invert(1);}
  .sidebar-collapse{flex:none;display:grid;place-items:center;width:44px;height:44px;padding:8px;border:0;background:transparent;color:var(--ink);border-radius:10px;}
  .sidebar-links{display:grid;gap:4px;}
  .sidebar-links button{display:flex;align-items:center;gap:14px;min-height:48px;width:100%;padding:12px 14px;border:0;border-radius:8px;background:transparent;color:var(--ink);text-align:left;font-size:15px;}
  button:not(.sidebar-brand):hover,.sidebar-links button[aria-current="page"]{background:var(--soft);}
  .sidebar-sections{border-top:1px solid var(--border);padding:16px 8px;color:var(--muted);font-size:14px;}
  .section-heading{display:flex;align-items:center;justify-content:space-between;gap:8px;}
  .section-heading button{display:grid;place-items:center;min-width:44px;min-height:44px;background:transparent;color:var(--muted);border:0;border-radius:10px;}
  .sidebar-sections p{margin:8px 0 22px;font-size:13px;line-height:1.5;}
  .sidebar-account{margin-top:auto;}
  .sidebar-nav{overflow-x:clip;}
  .sidebar-heading{position:relative;transition:min-height 200ms cubic-bezier(.2,.8,.2,1);}
  .sidebar-brand{position:relative;flex:1;height:48px;text-align:left;}
  .sidebar-brand img{position:absolute;left:8px;top:50%;transform:translateY(-50%);max-width:none;transition:opacity 160ms ease;}
  .sidebar-brand .brand-mark{width:36px;filter:none;opacity:0;}
  .sidebar-collapse{position:absolute;right:0;top:2px;transition:transform 200ms cubic-bezier(.2,.8,.2,1);}
  .nav-collapsed .sidebar-heading{min-height:96px;align-items:flex-start;}
  .nav-collapsed .sidebar-collapse{transform:translateY(48px);}
  .nav-collapsed .brand-full{opacity:0;}
  .nav-collapsed .brand-mark{opacity:1;}
  .sidebar-links button :global(svg){flex-shrink:0;}
  .nav-label{white-space:nowrap;transition:opacity 140ms ease,transform 200ms ease;}
  .nav-collapsed .nav-label{opacity:0;transform:translateX(-6px);}
  .sidebar-sections{max-height:320px;overflow:hidden;transition:opacity 140ms ease,max-height 200ms ease,padding 200ms ease;}
  .nav-collapsed .sidebar-sections{opacity:0;visibility:hidden;max-height:0;padding:0;border-top:0;}
  @media(prefers-reduced-motion:reduce){.sidebar-heading,.sidebar-brand img,.sidebar-collapse,.nav-label,.sidebar-sections{transition:none;}}
</style>
