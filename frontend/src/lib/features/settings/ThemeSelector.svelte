<script lang="ts">
  import { i18n } from '../../i18n/index.ts';
  import type { createThemeState } from './theme.ts';
  let { theme }: { theme: ReturnType<typeof createThemeState> } = $props();
  const options = [
    { value: 'system', label: 'theme.system', path: 'M3 4h18v12H3ZM8 21h8M12 16v5' },
    {
      value: 'light',
      label: 'theme.light',
      path: 'M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6 7 7M17 17l1.4 1.4M5.6 18.4 7 17M17 7l1.4-1.4M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0',
    },
    {
      value: 'dark',
      label: 'theme.dark',
      path: 'M20.5 14A8.5 8.5 0 0 1 10 3.5 8.5 8.5 0 1 0 20.5 14Z',
    },
  ] as const;
</script>

<fieldset>
  <legend>{$i18n.t('theme.background')}</legend>
  <div class="segments">
    {#each options as option (option.value)}
      <label class:selected={$theme.preference === option.value}>
        <input
          type="radio"
          name="workspace-theme"
          value={option.value}
          checked={$theme.preference === option.value}
          onchange={() => theme.select(option.value)}
        />
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.6"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"><path d={option.path} /></svg
        >
        <span>{$i18n.t(option.label)}</span>
      </label>
    {/each}
  </div>
</fieldset>

<style>
  fieldset {
    margin: 0;
    padding: 0;
    border: 0;
    min-width: 0;
    max-width: 440px;
  }
  legend {
    padding: 0;
    margin-bottom: 12px;
    font-size: 15px;
    font-weight: 600;
    color: var(--ink);
  }
  .segments {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 4px;
    padding: 4px;
    background: var(--paper);
    border: 1px solid var(--border);
    border-radius: 12px;
  }
  label {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    min-height: 48px;
    padding: 8px;
    border: 1px solid transparent;
    border-radius: 8px;
    color: var(--muted);
    cursor: pointer;
    font-size: 14px;
  }
  label:hover {
    color: var(--ink);
  }
  label.selected {
    background: var(--soft);
    color: var(--ink);
    border-color: var(--border);
  }
  label:has(input:focus-visible) {
    outline: 2px solid var(--focus-color, var(--accent));
    outline-offset: 2px;
  }
  input {
    position: absolute;
    width: 1px;
    height: 1px;
    opacity: 0;
  }
  svg {
    width: 18px;
    height: 18px;
    flex: none;
  }
</style>
