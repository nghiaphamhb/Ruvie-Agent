<script lang="ts">
  import {tick,type Snippet} from 'svelte';
  import {i18n} from '../i18n/index.ts';
  import WorkspaceIcon from '../shared/WorkspaceIcon.svelte';
  let {collapsed,mobileOpen,ontoggle,onclose,oncontrols,sidebar,children,toolbar}: {collapsed:boolean;mobileOpen:boolean;ontoggle:()=>void;onclose:()=>void;oncontrols:()=>void;sidebar:Snippet;children:Snippet;toolbar?:Snippet}=$props();
  let drawer:HTMLElement;let toggle:HTMLButtonElement;
  $effect(()=>{if(mobileOpen)void tick().then(()=>{if(mobileOpen)drawer?.querySelector<HTMLButtonElement>('button')?.focus();});});
  async function close(){onclose();await tick();toggle?.focus();}
  /** Keep keyboard focus within the mobile drawer; native dialogs manage their own focus. */
  function drawerKey(event:KeyboardEvent){
    if(!mobileOpen||event.defaultPrevented)return;
    if(event.key==='Escape'){event.preventDefault();close();}
    if(event.key==='Tab'){
      const controls=[...drawer.querySelectorAll<HTMLElement>('button:not(:disabled),a[href]')].filter(el=>el.getClientRects().length>0);
      const first=controls[0],last=controls.at(-1);
      if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus();}
      else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus();}
    }
  }
</script>
<div class="workspace workspace-shell" class:collapsed class:mobile-open={mobileOpen}>
  <a class="skip-link" href="#workspace-main">{$i18n.t('workspace.skip')}</a>
  <button class="sidebar-backdrop" class:backdrop-open={mobileOpen} disabled={!mobileOpen} tabindex="-1" type="button" aria-label={$i18n.t('workspace.closeSidebar')} onclick={close}></button>
  <aside class="workspace-sidebar" bind:this={drawer} role={mobileOpen?'dialog':undefined} aria-modal={mobileOpen?'true':undefined} aria-label={$i18n.t('workspace.sidebar')} onkeydown={drawerKey}>{@render sidebar()}</aside>
  <main inert={mobileOpen} class="workspace-content" id="workspace-main" tabindex="-1">
    <header class="workspace-toolbar">
      <button class="sidebar-open" bind:this={toggle} type="button" aria-label={$i18n.t('workspace.openSidebar')} onclick={ontoggle}><WorkspaceIcon name="collapse"/></button>
      {@render toolbar?.()}
      <button class="chat-controls-trigger" type="button" aria-label={$i18n.t('workspace.controls')} onclick={oncontrols}><WorkspaceIcon name="settings" size={24}/></button>
    </header>
    {@render children()}
  </main>
</div>
