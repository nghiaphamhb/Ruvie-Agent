<script lang="ts">
  import {tick,type Snippet} from 'svelte';
  import {i18n} from '../i18n/index.ts';
  let {open,title,onclose,children,className=''}:{open:boolean;title:string;onclose:()=>void;children:Snippet;className?:string}=$props();
  let dialog:HTMLDialogElement;let trigger:HTMLElement|null=null;
  $effect(()=>{
    if(open&&!dialog.open){trigger=document.activeElement as HTMLElement;dialog.showModal();void tick().then(()=>{if(open)dialog.querySelector<HTMLElement>('[data-dialog-heading]')?.focus();});}
    else if(!open&&dialog.open){dialog.close();if(trigger?.isConnected)trigger.focus();}
  });
  function key(event:KeyboardEvent){
    if(event.key!=='Tab')return;
    const controls=[...dialog.querySelectorAll<HTMLElement>('button,input,select,textarea,summary,a[href],[tabindex]')].filter(el=>el.tabIndex>=0&&!el.matches(':disabled')&&el.getClientRects().length>0);
    const first=controls[0],last=controls.at(-1);
    if(event.shiftKey&&(document.activeElement===first||document.activeElement===dialog.querySelector('[data-dialog-heading]'))){event.preventDefault();last?.focus();}
    else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus();}
  }
</script>
<dialog bind:this={dialog} class={'surface-dialog '+className} aria-label={title} onkeydown={key}
  oncancel={event=>{event.preventDefault();event.stopPropagation();onclose();}} onclose={()=>{if(open)onclose();}}>
  <header><h2 data-dialog-heading tabindex="-1">{title}</h2><button type="button" aria-label={$i18n.t('ux.close')} onclick={onclose}>×</button></header>
  {@render children()}
</dialog>
<style>
  dialog{width:min(760px,calc(100vw - 32px));max-height:calc(100dvh - 32px);padding:24px;overflow:auto;border:1px solid var(--border);border-radius:12px;background:var(--surface);color:var(--ink);}
  dialog::backdrop{background:#010c1dcc;backdrop-filter:blur(4px);}
  header{position:relative;display:flex;align-items:center;min-height:44px;padding-right:44px;margin-bottom:16px;}
  h2{margin:0;font-size:21px;overflow-wrap:anywhere;}button{position:absolute;top:-12px;right:-12px;display:grid;place-items:center;width:44px;height:44px;padding:0;border:0;border-radius:8px;background:var(--surface);color:var(--ink);font-size:24px;}
  button:hover{background:var(--soft);}
  @media(max-width:600px){dialog{padding:16px;}button{top:-4px;right:-4px;}}
</style>
