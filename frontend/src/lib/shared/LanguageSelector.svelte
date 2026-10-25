<script lang="ts">
  import { i18n, languages, setLocale } from '../i18n/index.ts';
  let { id }: { id: string } = $props();
</script>

<div class="language-selector">
  <label for={id} class="sr-only">{$i18n.t('language.label')}</label>
  <svg
    class="language-icon"
    xmlns="http://www.w3.org/2000/svg"
    width="20"
    height="20"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.8"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <path
      d="M9 4V3a1 1 0 0 1 1-1h11a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1h-1v3l-3-3h-3M6 8H3a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h1v3l3-3h6a1 1 0 0 0 1-1v-2M5 17l3-7 3 7M6 15h4M12 6h7M15.5 4v2M13 6c.5 2 2 4 5 5M18 6c-.5 2-2 4-5 5"
    />
  </svg>
  <select {id} value={$i18n.locale} onchange={(event) => void setLocale(event.currentTarget.value)}>
    {#each languages as language (language.code)}
      <option value={language.code}>{language.title}</option>
    {/each}
  </select>
</div>

<style>
  :global(.workspace-shell) .language-selector {
    --language-bg: var(--surface);
    --language-ink: var(--ink);
    --language-border: var(--border);
    --language-hover: var(--soft);
    color-scheme: var(--control-color-scheme);
  }
  .language-selector {
    position: relative;
    display: block;
    min-width: 0;
  }
  select {
    width: 100%;
    min-width: 0;
    min-height: 44px;
    padding: 8px 12px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--surface);
    color: var(--ink);
  }
  select:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    margin: -1px;
    padding: 0;
    overflow: hidden;
    clip-path: inset(50%);
    white-space: nowrap;
  }
  select {
    appearance: none;
    padding: 8px 14px 8px 42px;
    border-radius: 8px;
    background: var(--language-bg, rgba(0, 52, 101, 0.35));
    color: var(--language-ink, white);
    border-color: var(--language-border, rgba(255, 255, 255, 0.18));
    font-size: 14px;
  }
  select:hover {
    background: var(--language-hover, rgba(0, 52, 101, 0.5));
  }
  select option {
    background: var(--language-bg, white);
    color: var(--language-ink, #073b65);
  }
  .language-icon {
    position: absolute;
    left: 14px;
    top: 50%;
    transform: translateY(-50%);
    color: var(--language-ink, white);
    pointer-events: none;
  }
  @supports (appearance: base-select) {
    select,
    select::picker(select) {
      appearance: base-select;
    }

    select {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }
    select::picker-icon {
      display: none;
    }
    select::picker(select) {
      margin-top: 8px;
      padding: 6px;
      border: 1px solid var(--language-border, rgba(255, 255, 255, 0.2));
      border-radius: 16px;
      background: var(--language-bg, #074675);
      color: var(--language-ink, white);
      box-shadow: 0 12px 32px rgba(0, 22, 48, 0.28);
      font: inherit;
    }
    select option {
      display: flex;
      align-items: center;
      gap: 8px;
      min-height: 40px;
      padding: 8px 10px;
      border-radius: 10px;
      background: transparent;
      color: var(--language-ink, white);
      cursor: pointer;
    }
    select option:hover,
    select option:focus {
      background: var(--language-hover, rgba(255, 255, 255, 0.12));
    }
    select option:checked {
      background: var(--language-hover, rgba(255, 255, 255, 0.2));
    }
    select option::checkmark {
      color: var(--language-ink, white);
    }
  }
</style>
