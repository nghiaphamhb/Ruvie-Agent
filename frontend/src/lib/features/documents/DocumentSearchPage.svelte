<script lang="ts">
  import {i18n} from '../../i18n/index.ts';
  import type {createDocumentsState} from './documents-state.svelte.ts';
  import SourceDetails from '../../shared/SourceDetails.svelte';
  let {state:documents}:{state:ReturnType<typeof createDocumentsState>}=$props();
  let selected=$state<number|null>(null);
  $effect(()=>{documents.results;selected=null;});
  function resultKey(event:KeyboardEvent,index:number){
    if(event.isComposing||!['ArrowDown','ArrowUp','Home','End'].includes(event.key))return;
    event.preventDefault();const count=documents.results.length;
    const next=event.key==='Home'?0:event.key==='End'?count-1:(index+(event.key==='ArrowDown'?1:-1)+count)%count;
    document.getElementById('search-result-'+next)?.focus();
  }
</script>
<section class="search-page">
  <h1 data-view-heading tabindex="-1">{$i18n.t('search.heading')}</h1><p>{$i18n.t('search.help')}</p>
  <form onsubmit={event=>{event.preventDefault();void documents.search();}}>
    <label for="document-query">{$i18n.t('search.query')}</label><div class="search-form-row">
      <input id="document-query" type="search" bind:value={documents.query} required onkeydown={event=>{if(event.key==='Enter'&&event.isComposing)event.preventDefault();}}/>
      <button type="submit" disabled={!documents.query.trim()}>{$i18n.t('search.submit')}</button>
    </div>
  </form>
  {#if documents.searchLoading}<p role="status">{$i18n.t('search.loading')}</p>{/if}
  {#if documents.searchError}<p role="alert">{$i18n.message(documents.searchError)} <button type="button" onclick={()=>documents.search()}>{$i18n.t('common.retry')}</button></p>{/if}
  {#if documents.searched&&!documents.searchLoading&&!documents.searchError&&!documents.results.length}<p>{$i18n.t('search.empty')}</p>{/if}
  <div class="search-layout">
    <ol class="search-results">{#each documents.results as result,index}<li>
      <button id={'search-result-'+index} type="button" aria-pressed={selected===index} onkeydown={event=>resultKey(event,index)} onclick={()=>{selected=index;}}>
        <strong>{result.citation.title}</strong><small>{result.citation.software} {result.citation.software_version}</small><span>{result.text.slice(0,240)}</span>
      </button>
    </li>{/each}</ol>
    {#if selected!==null&&documents.results[selected]}<div class="search-detail"><SourceDetails citation={documents.results[selected].citation} text={documents.results[selected].text}/></div>{/if}
  </div>
</section>
<style>
  section{width:min(100%,1100px);margin:0 auto;padding:24px;min-width:0;}h1{font-size:24px;}p{color:var(--muted);line-height:1.6;}
  label{display:block;margin-bottom:8px;}.search-form-row{display:flex;gap:10px;}input{flex:1;min-width:0;min-height:44px;padding:12px 14px;border:1px solid var(--border);border-radius:12px;color:var(--ink);background:var(--surface);font-size:16px;}
  button{min-height:44px;padding:10px 14px;border:1px solid var(--border);border-radius:12px;background:var(--surface);color:var(--ink);}button:disabled{opacity:.55;}
  .search-layout{display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-top:24px;min-width:0;}
  ol{list-style:none;padding:0;margin:0;display:grid;align-content:start;gap:12px;min-width:0;}li{min-width:0;}li button{display:block;width:100%;text-align:left;overflow-wrap:anywhere;padding:16px;}
  li button[aria-pressed="true"]{border-color:var(--accent);background:var(--soft);}strong,small,span{display:block;}small{margin:8px 0;color:var(--muted);}span{line-height:1.6;font-size:14px;}
  .search-detail{min-width:0;padding:16px;border:1px solid var(--border);border-radius:16px;background:var(--surface);}
  @media(max-width:700px){.search-layout{grid-template-columns:1fr;}section{padding:16px;}}
</style>
