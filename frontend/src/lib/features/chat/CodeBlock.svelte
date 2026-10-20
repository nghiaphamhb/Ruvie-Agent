<script lang="ts">
  import { i18n } from '../../i18n/index.ts';
  import { copyText } from './copy.ts';
  let { code, language }: { code: string; language: string } = $props();
  let collapsed = $state(false);
</script>

<div class="code-block">
  <div class="code-toolbar">
    <span>{language || $i18n.t('chat.code')}</span>
    <div>
      <button type="button" onclick={() => copyText(code)} aria-label={$i18n.t('chat.copyCode')}
        >{$i18n.t('chat.copyCode')}</button
      >
      <button
        type="button"
        aria-expanded={!collapsed}
        onclick={() => {
          collapsed = !collapsed;
        }}>{collapsed ? $i18n.t('chat.expandCode') : $i18n.t('chat.collapseCode')}</button
      >
    </div>
  </div>
  <!-- svelte-ignore a11y_no_noninteractive_tabindex (Long code must be keyboard-scrollable.) -->
  <pre hidden={collapsed} role="region" aria-label={$i18n.t('chat.code')} tabindex="0"><code
      >{code}</code
    ></pre>
</div>

<style>
  .code-block {
    min-width: 0;
    max-width: 100%;
    margin: 16px 0;
    border: 1px solid var(--border);
    border-radius: 14px;
    overflow: hidden;
    background: var(--paper);
  }
  .code-toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
    padding: 4px 10px;
    background: var(--soft);
    font-size: 13px;
  }
  button {
    min-height: 44px;
    padding: 8px;
    border: 0;
    border-radius: 8px;
    color: var(--ink);
    background: transparent;
  }
  button:hover {
    background: var(--surface);
  }
  pre {
    max-width: 100%;
    overflow: auto;
    margin: 0;
    padding: 16px;
    line-height: 1.65;
    font-size: 13px;
    white-space: pre;
  }
  code {
    font-family: ui-monospace, Consolas, monospace;
  }
</style>
