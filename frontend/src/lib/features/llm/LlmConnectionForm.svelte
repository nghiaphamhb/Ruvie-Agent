<script lang="ts">
  import {i18n} from '../../i18n/index.ts';
  import type {createLlmState} from './llm-state.svelte.ts';
  let {state,disabled=false}:{state:ReturnType<typeof createLlmState>;disabled?:boolean}=$props();
</script>
<!-- The workspace owns requests; this form only edits that session's connection draft. -->
<section class="llm-panel" aria-labelledby="llm-heading" aria-busy={state.loading}>
  <h2 id="llm-heading">{$i18n.t('nav.llm')}</h2>
  <form onsubmit={state.save}><fieldset disabled={disabled||state.loading||state.modelBusy}>
    <div class="fields">
      <label for="llm-url">{$i18n.t('llm.url')}<input id="llm-url" type="url" required bind:value={state.baseUrl} placeholder="https://example.com/v1"/></label>
      <label for="llm-key">{$i18n.t('llm.key')}<input id="llm-key" type="password" autocomplete="off" bind:value={state.apiKey} aria-describedby="key-help"/></label>
    </div>
    <p id="key-help" class="help">{state.clearKey?$i18n.t('llm.keyClearHelp'):state.samePersonalUrl&&state.connection?.has_api_key?$i18n.t('llm.keyKeepHelp'):$i18n.t('llm.keyHelp')}</p>
    <div class="actions">
      <button class="primary" type="submit">{state.loading?$i18n.t('llm.processing'):$i18n.t('llm.connect')}</button>
      <button type="button" onclick={state.disconnect} disabled={state.connection?.source!=='personal'}>{$i18n.t('llm.disconnect')}</button>
      <button type="button" onclick={()=>{state.clearKey=true;}} disabled={!state.samePersonalUrl||!state.connection?.has_api_key||state.clearKey}>{$i18n.t('llm.clearKey')}</button>
      <button type="button" onclick={state.reloadConnection}>{$i18n.t('common.reload')}</button>
    </div>
  </fieldset></form>
  <p class="status" role="status">{state.loading?$i18n.t('llm.checking'):$i18n.message(state.notice)||(state.connection?.source==='personal'?$i18n.t('llm.source.personal'):state.connection?.source==='server'?$i18n.t('llm.source.server'):$i18n.t('llm.source.none'))}</p>
  {#if state.error}<p class="error" role="alert">{$i18n.message(state.error)}</p>{/if}
</section>
<style>
  .llm-panel{flex:none;width:min(calc(100% - 48px),var(--form-width));margin:24px auto;padding:calc(3 * var(--space));border:1px solid var(--border);border-radius:var(--radius);background:var(--surface);}
  h2{margin:0 0 12px;font-size:20px;}fieldset{margin:0;padding:0;border:0;min-width:0;}
  .fields{display:grid;gap:16px;}label{display:grid;gap:6px;padding:calc(1.5 * var(--space));border-radius:var(--radius);background:var(--paper);color:var(--muted);font-size:13px;}
  input{width:100%;min-width:0;min-height:44px;padding:9px 12px;border:0;border-radius:var(--radius);background:transparent;color:var(--ink);}
  .actions{display:flex;flex-wrap:wrap;gap:8px;}button{min-height:44px;padding:8px 12px;border:1px solid var(--border);border-radius:var(--radius);background:var(--surface);color:var(--ink);}
  .primary{background:var(--accent);color:var(--surface);}:is(input,button):focus-visible{outline:2px solid var(--accent);outline-offset:2px;}:is(input,button):disabled{opacity:.65;}
  .help,.status,.error{margin:10px 0;font-size:13px;line-height:1.5;overflow-wrap:anywhere;}.help{color:var(--muted);}.status{margin-bottom:0;}.error{color:var(--error);}
</style>
