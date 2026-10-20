<script lang="ts">
  import { i18n } from '../../i18n/index.ts';
  import type { Citation } from './chat-api.ts';
  import SourceDetails from '../../shared/SourceDetails.svelte';
  import SurfaceDialog from '../../shared/SurfaceDialog.svelte';
  let { citations }: { citations: Citation[] } = $props();
  let expanded = $state(false),
    selected = $state<Citation | null>(null);
</script>

<!-- Count/list/source panel adapted from references Citations.showSourceModal; metadata only. -->
<details class="sources" bind:open={expanded}>
  <summary aria-expanded={expanded}
    >{$i18n.t('citations.count', { count: citations.length })}</summary
  >
  <ol>
    {#each citations as citation, index (citation.citation_id)}<li>
        <span class="source-number" aria-hidden="true">{index + 1}</span>
        <div>
          <button
            class="source-title"
            type="button"
            onclick={() => {
              selected = citation;
            }}>{citation.title}</button
          ><small>{citation.software} {citation.software_version}</small>
        </div>
      </li>{/each}
  </ol>
</details>
<SurfaceDialog
  open={selected !== null}
  title={$i18n.t('citations.source')}
  className="source-dialog"
  onclose={() => {
    selected = null;
  }}
>
  {#if selected}<SourceDetails citation={selected} />{/if}
</SurfaceDialog>

<style>
  .sources {
    margin-top: 16px;
  }
  summary {
    min-height: 44px;
    width: fit-content;
    padding: 12px 14px;
    border: 1px solid var(--border);
    border-radius: 999px;
    background: var(--surface);
    color: var(--accent);
    font-size: 13px;
    cursor: pointer;
  }
  ol {
    list-style: none;
    margin: 12px 0 0;
    padding: 0;
    display: grid;
    gap: 8px;
  }
  li {
    display: flex;
    gap: 12px;
    padding: 10px 12px;
    border: 1px solid var(--border);
    border-radius: 12px;
    background: var(--surface);
  }
  li > span {
    padding-top: 12px;
    color: var(--muted);
  }
  li > div {
    min-width: 0;
  }
  button {
    min-height: 44px;
    border: 0;
    background: transparent;
    color: var(--ink);
    padding: 8px 0;
    text-align: left;
    overflow-wrap: anywhere;
  }
  button:hover {
    text-decoration: underline;
  }
  small {
    display: block;
    color: var(--muted);
  }
</style>
