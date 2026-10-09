<script lang="ts">
  import { i18n } from '../i18n/index.ts';
  import type { Citation } from '../chat-api';
  let { citations }: { citations: Citation[] } = $props();
  let expanded = $state(false);
</script>
<!-- Source-count pill/numbered names from chat/Messages/Citations.svelte.
     Native details replaces the modal; metadata comes only from active SSE. -->
<details class="sources" bind:open={expanded}>
  <summary aria-expanded={expanded}>{$i18n.t('citations.count', {count: citations.length})}</summary>
  <ol>
    {#each citations as citation, index (citation.citation_id)}
      <li>
        <span class="source-number" aria-hidden="true">{index + 1}</span><div class="source-title">{citation.title}</div>
        <dl>
          <div><dt>{$i18n.t('citations.citation')}</dt><dd>{citation.citation_id}</dd></div>
          <div><dt>{$i18n.t('citations.document')}</dt><dd>{citation.document_id}</dd></div>
          <div><dt>{$i18n.t('citations.revision')}</dt><dd>{citation.revision_id}</dd></div>
          <div><dt>{$i18n.t('citations.chunk')}</dt><dd>{citation.chunk_id} · #{citation.ordinal}</dd></div>
          <div><dt>{$i18n.t('citations.offset')}</dt><dd>{citation.start_offset}–{citation.end_offset}</dd></div>
          <div><dt>{$i18n.t('citations.hash')}</dt><dd>{citation.source_hash}</dd></div>
          <div><dt>{$i18n.t('upload.software')}</dt><dd>{citation.software} {citation.software_version}</dd></div>
        </dl>
      </li>
    {/each}
  </ol>
</details>

<style>
  .sources { margin-top: 16px; color: var(--ink); }
  .sources summary { border-radius: 999px; width: fit-content; padding: 8px 12px; border: 1px solid var(--border); background: var(--surface); color: var(--accent); font-size: 13px; font-weight: 650; cursor: pointer; }
  .sources ol { margin: 13px 0 0; padding: 0; list-style: none; display: grid; gap: 10px; }
  .sources li { padding: 13px 15px; border: 1px solid var(--border); border-radius: var(--radius); background: var(--surface); }
  .source-title { font-size: 14px; font-weight: 650; display: inline; }
  .sources dl { display: grid; gap: 5px; margin: 9px 0 0; font-size: 12px; line-height: 1.5; }
  .sources dl > div { display: grid; grid-template-columns: 95px minmax(0, 1fr); gap: 8px; }
  .sources dt { color: var(--muted); }
  .sources dd { margin: 0; overflow-wrap: anywhere; }
  .source-number { display: inline-grid; place-items: center; min-width: 24px; height: 24px; border-radius: var(--radius); background: var(--soft); font-size: 12px; margin-right: 8px; }
</style>
