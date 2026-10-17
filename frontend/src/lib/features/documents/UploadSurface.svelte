<script lang="ts">
  import {tick,type Snippet} from 'svelte';
  import {i18n} from '../../i18n/index.ts';
  import SurfaceDialog from '../../shared/SurfaceDialog.svelte';
  let {open,inlineVisible,inlineTarget,onclose,children}:{open:boolean;inlineVisible:boolean;inlineTarget:HTMLElement|undefined;onclose:()=>void;children:Snippet}=$props();
  let container:HTMLDivElement,dialogTarget:HTMLDivElement;
  // Move the mounted form, retaining the browser's File input and its focusable controls.
  $effect(()=>{
    const target=open?dialogTarget:inlineTarget;
    if(container&&target&&container.parentNode!==target)target.appendChild(container);
    if(open)void tick().then(()=>{if(open)container?.querySelector<HTMLElement>('select,input,button')?.focus();});
  });
</script>
<SurfaceDialog {open} title={$i18n.t('upload.dialog')} className="upload-dialog" {onclose}>
  <div bind:this={dialogTarget}></div>
</SurfaceDialog>
<div bind:this={container} hidden={!open&&!inlineVisible} class="upload-content">{@render children()}</div>
<style>
  .upload-content{min-width:0;}
  :global(.upload-dialog .upload-panel){width:100%;padding:0;margin:0;border:0;background:transparent;}
</style>
