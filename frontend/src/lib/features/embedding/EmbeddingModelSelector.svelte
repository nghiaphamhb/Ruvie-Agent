<script lang="ts">
  import { i18n } from '../../i18n/index.ts';
  import { toast } from 'svelte-sonner';
  import type { createEmbeddingState } from './embedding-state.svelte.ts';
  let { owner }: { owner: ReturnType<typeof createEmbeddingState> } = $props();
  let search = $state('');
  let dismissed = $state<string | null>(null);
  const filtered = $derived(
    owner.models.filter((m) => (m.id + ' ' + m.name).toLowerCase().includes(search.toLowerCase())),
  );
  const selected = $derived(owner.models.find((m) => m.id === owner.defaultModelId));
</script>

<label for="embedding-search">{$i18n.t('model.search')}</label>
<input id="embedding-search" type="search" bind:value={search} />
<div class="models">
  <table>
    <thead
      ><tr><th>{$i18n.t('embedding.heading')}</th><th>{$i18n.t('embedding.dimension')}</th></tr
      ></thead
    >
    <tbody
      >{#each filtered as model (model.id)}<tr
          ><td
            ><label title={!model.supported ? $i18n.t('embedding.unsupported') : model.id}
              ><input
                type="radio"
                name="embedding-model"
                value={model.id}
                checked={owner.defaultModelId === model.id}
                disabled={owner.busy}
                onchange={() => {
                  owner.selectModel(model.id);
                  if (!model.supported)
                    toast.error($i18n.t('embedding.unsupported'), { id: 'embedding-selection' });
                }}
              />{model.name}<small>{model.id}</small>{#if !model.available}<small
                  >{$i18n.t('llm.org.unavailable')}</small
                >{/if}</label
            >
            {#if !model.supported}<span class="hint"
                ><button
                  type="button"
                  class="hint-trigger"
                  aria-label={$i18n.t('embedding.unsupported')}
                  aria-describedby={'embedding-warning-' + encodeURIComponent(model.id)}
                  onfocus={() => (dismissed = null)}
                  onkeydown={(event) => {
                    if (event.key === 'Escape') dismissed = model.id;
                  }}>!</button
                ><span
                  class:hidden={dismissed === model.id}
                  id={'embedding-warning-' + encodeURIComponent(model.id)}
                  role="tooltip">{$i18n.t('embedding.unsupported')}</span
                ></span
              >{/if}
          </td><td>{model.dimension ?? $i18n.t('embedding.unknownDimension')}</td></tr
        >{/each}</tbody
    >
  </table>
  {#if !filtered.length}<p role="status">
      {$i18n.t(owner.models.length ? 'model.noMatch' : 'llm.org.empty')}
    </p>{/if}
</div>
{#if selected && !selected.supported}<p class="warning" role="status">
    {$i18n.t(selected.available ? 'embedding.unsupported' : 'llm.org.unavailable')}
  </p>{/if}

<style>
  .hint {
    position: relative;
    display: inline-block;
  }
  .hint-trigger {
    min-width: 44px;
    min-height: 44px;
    border: 0;
    background: transparent;
    color: var(--ink);
    cursor: help;
  }
  .hint [role='tooltip'] {
    display: none;
    position: absolute;
    z-index: 5;
    left: 0;
    bottom: 100%;
    width: 260px;
    padding: 12px;
    background: var(--surface);
    color: var(--ink);
    border: 1px solid var(--border);
    border-radius: 7px;
    font-size: 13px;
  }
  .hint:hover [role='tooltip']:not(.hidden),
  .hint:focus-within [role='tooltip']:not(.hidden) {
    display: block;
  }
  thead {
    position: sticky;
    top: 0;
    background: var(--surface);
    z-index: 1;
  }
  .models {
    max-height: 320px;
    overflow: auto;
    margin: 16px 0;
  }
  table {
    width: 100%;
    border-collapse: collapse;
  }
  th,
  td {
    text-align: left;
    padding: 12px;
    border-bottom: 1px solid var(--border);
  }
  label {
    display: block;
    cursor: pointer;
  }
  small {
    display: block;
    color: var(--muted);
    overflow-wrap: anywhere;
  }
  input[type='radio'] {
    margin-right: 10px;
    accent-color: var(--accent);
  }
  input[type='search'] {
    width: 100%;
    min-height: 44px;
    background: var(--paper);
    color: var(--ink);
    border: 1px solid var(--border);
    border-radius: 7px;
  }
  input:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
  .warning {
    color: var(--error);
    font-size: 13px;
  }
</style>
