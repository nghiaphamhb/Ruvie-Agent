<script lang="ts">
  import { i18n } from '../i18n/index.ts';
  let { view, title }: { view: string; title: string } = $props();
  let selected = $state('Models');
  const sections = ['Models', 'Knowledge', 'Prompts', 'Tools', 'Skills'];
  /** Library tabs only expose a deferred UI; they never fetch or persist data. */
  function tabKey(event: KeyboardEvent, index: number) {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const next =
      event.key === 'Home'
        ? 0
        : event.key === 'End'
          ? 4
          : (index + (event.key === 'ArrowRight' ? 1 : -1) + 5) % 5;
    selected = sections[next];
    document.getElementById('library-tab-' + next)?.focus();
  }
</script>

<section class="feature-placeholder" aria-labelledby="view-heading">
  <h1 id="view-heading" data-view-heading tabindex="-1">{$i18n.t(title)}</h1>
  {#if view === 'search'}
    <!-- SearchModal/SearchInput layout adapted without the legacy chat APIs. -->
    <label
      >{$i18n.t('workspace.search')}<input
        type="search"
        disabled
        placeholder={$i18n.t('workspace.searchPlaceholder')}
      /></label
    >
  {:else if view === 'notes'}
    <label
      >{$i18n.t('workspace.notes')}<textarea
        disabled
        rows="5"
        placeholder={$i18n.t('workspace.notesPlaceholder')}></textarea></label
    >
  {:else if view === 'workspace'}
    <!-- Library sections from references/routes/(app)/workspace/+layout.svelte. -->
    <div role="tablist" aria-label={$i18n.t('workspace.library')}>
      {#each sections as item, index (item)}<button
          id={'library-tab-' + index}
          role="tab"
          type="button"
          aria-selected={selected === item}
          tabindex={selected === item ? 0 : -1}
          aria-controls="library-panel"
          onclick={() => (selected = item)}
          onkeydown={(event) => tabKey(event, index)}>{item}</button
        >{/each}
    </div>
    <div
      id="library-panel"
      role="tabpanel"
      tabindex="0"
      aria-labelledby={'library-tab-' + sections.indexOf(selected)}
    >
      <h2>{selected}</h2>
      <p>{$i18n.t('workspace.deferred')}</p>
    </div>
  {/if}
  {#if view !== 'workspace'}<p>{$i18n.t('workspace.deferred')}</p>{/if}
</section>

<style>
  section {
    max-width: 900px;
    margin: 0 auto;
    padding: 24px;
  }
  h1 {
    margin: 0 0 24px;
    font-size: 24px;
  }
  h2 {
    font-size: 18px;
    font-weight: 500;
  }
  p {
    line-height: 1.6;
    color: var(--muted);
  }
  label {
    display: grid;
    gap: 12px;
    max-width: 700px;
    color: var(--muted);
  }
  input,
  textarea {
    min-width: 0;
    min-height: 44px;
    padding: 14px;
    border: 1px solid var(--border);
    border-radius: 16px;
    color: var(--ink);
    background: var(--surface);
    resize: vertical;
    opacity: 1;
  }
  input::placeholder,
  textarea::placeholder {
    color: var(--muted);
  }
  [role='tablist'] {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
  button {
    min-height: 44px;
    padding: 12px;
    border: 0;
    border-radius: 12px;
    background: transparent;
    color: var(--ink);
  }
  button[aria-selected='true'] {
    background: var(--soft);
  }
  [role='tabpanel'] {
    padding-top: 24px;
  }
</style>
