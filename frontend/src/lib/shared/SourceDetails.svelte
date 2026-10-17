<script lang="ts">
  import {i18n} from '../i18n/index.ts';
  import type {Citation} from '../features/chat/chat-api.ts';
  let {citation,text}:{citation:Citation;text?:string}=$props();
</script>
<p class="source-name">{citation.title}</p><p class="source-version">{citation.software} {citation.software_version}</p>
{#if text!==undefined}<p class="excerpt">{text}</p>{/if}
<details><summary>{$i18n.t('citations.details')}</summary><dl>
  <div><dt>{$i18n.t('citations.citation')}</dt><dd>{citation.citation_id}</dd></div>
  <div><dt>{$i18n.t('citations.document')}</dt><dd>{citation.document_id}</dd></div>
  <div><dt>{$i18n.t('citations.revision')}</dt><dd>{citation.revision_id}</dd></div>
  <div><dt>{$i18n.t('citations.chunk')}</dt><dd>{citation.chunk_id} · #{citation.ordinal}</dd></div>
  <div><dt>{$i18n.t('citations.offset')}</dt><dd>{citation.start_offset}–{citation.end_offset}</dd></div>
  <div><dt>{$i18n.t('citations.hash')}</dt><dd>{citation.source_hash}</dd></div>
</dl></details>
<style>
  p{overflow-wrap:anywhere;line-height:1.65;}.source-name{font-weight:650;}.source-version{color:var(--muted);}.excerpt{white-space:pre-wrap;padding:16px;background:var(--soft);border-radius:12px;}
  summary{min-height:44px;padding:12px 0;cursor:pointer;color:var(--accent);}
  dl{font-size:13px;display:grid;gap:10px;}dl div{display:grid;grid-template-columns:110px minmax(0,1fr);gap:12px;}dt{color:var(--muted);}dd{margin:0;overflow-wrap:anywhere;}
  @media(max-width:400px){dl div{grid-template-columns:1fr;gap:4px;}}
</style>
