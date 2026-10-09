<script lang="ts">
  import { i18n, languages, setLocale } from '../i18n/index.ts';
  let { id }: { id: string } = $props();
</script>

<div class="language-selector">
  <label for={id}>{$i18n.t('language.label')}</label>
  <select {id} value={$i18n.locale} onchange={(event) => void setLocale(event.currentTarget.value)}>
    {#each languages as language (language.code)}
      <option value={language.code}>{language.title}</option>
    {/each}
  </select>
</div>

<style>
  .language-selector { display: grid; gap: 6px; min-width: 0; }
  label { color: var(--muted); font-size: 12px; }
  select { width: 100%; min-width: 0; min-height: 44px; padding: 8px 12px; border: 1px solid var(--border); border-radius: var(--radius); background: var(--surface); color: var(--ink); }
  select:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
</style>
