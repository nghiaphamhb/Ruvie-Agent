<script lang="ts">
  import { i18n } from '../i18n/index.ts';
  import { message as uiMessage, type UiMessage } from '../i18n/messages.ts';
  import { onDestroy, onMount } from 'svelte';
  import {
    LlmApiError, getLlmConnection, getModels, saveLlmConnection, deleteLlmConnection,
    type LlmConnection, type ModelsResult, type ConnectionInput
  } from '../llm-api.ts';

  let { csrfToken, disabled = false, onexpired, onbusychange, onmodelschange }: {
    csrfToken: string;
    disabled?: boolean;
    onexpired: () => void;
    onbusychange: (busy: boolean) => void;
    onmodelschange: (result: ModelsResult | null) => void;
  } = $props();
  let connection = $state<LlmConnection | null>(null);
  let baseUrl = $state('');
  let apiKey = $state('');
  let clearKey = $state(false);
  let loading = $state(false);
  let error = $state<UiMessage | null>(null);
  let notice = $state<UiMessage | null>(null);
  // Invalidate pending responses when this account's form is removed.
  let sequence = 0;
  const normalizeUrl = (url: string) => url.trim().replace(/\/+$/, '');
  let samePersonalUrl = $derived(connection?.source === 'personal' && normalizeUrl(baseUrl) === connection.base_url);

  /** Reload metadata/catalog; saved keys never return to the browser. */
  async function reload(current: number) {
    onmodelschange(null);
    const result = await getLlmConnection();
    if (current !== sequence) return;
    connection = result;
    baseUrl = result.base_url ?? '';
    apiKey = '';
    clearKey = false;

    if (result.source !== 'none') {
      const models = await getModels();
      if (current === sequence) onmodelschange(models);
    }
  }

  /** Serialize form operations and ignore responses from an unmounted login session. */
  async function run(action: (current: number) => Promise<void>, initial = false) {
    if ((!initial && disabled) || loading) return;
    const current = ++sequence;
    loading = true;
    onbusychange(true);
    error = null;
    notice = null;
    try { await action(current); }
    catch (failure) {
      if (current !== sequence) return;
      if (failure instanceof LlmApiError && failure.status === 401) { onexpired(); return; }
      error = failure instanceof LlmApiError ? failure.uiMessage : uiMessage('llm.errors.read');
    } finally {
      if (current === sequence) { loading = false; onbusychange(false); }
    }
  }

  function save(event: SubmitEvent) {
    event.preventDefault();
    if (!baseUrl.trim()) return;
    // Omission preserves a same-URL personal key; only an explicit action sends empty key.
    const input: ConnectionInput = { base_url: normalizeUrl(baseUrl) };
    if (clearKey) input.api_key = '';
    else if (apiKey.trim()) input.api_key = apiKey.trim();
    void run(async (current) => {
      const result = await saveLlmConnection(csrfToken, input);
      if (current !== sequence) return;
      onmodelschange(result);
      apiKey = '';
      clearKey = false;
      const metadata = await getLlmConnection();
      if (current !== sequence) return;
      connection = metadata;
      baseUrl = metadata.base_url ?? '';
      notice = uiMessage('llm.saved');
    });
  }

  function disconnect() {
    void run(async (current) => {
      await deleteLlmConnection(csrfToken);
      if (current !== sequence) return;
      await reload(current);
      if (current === sequence) notice = uiMessage('llm.removed');
    });
  }

  // Login may still be loading projects; metadata loading starts independently.
  onMount(() => { void run(reload, true); });
  onDestroy(() => { sequence += 1; apiKey = ''; });
</script>

<!-- URL/key form presentation adapted from AddConnectionModal.svelte; active F006 requests stay server-side. -->
<section class="llm-panel" aria-labelledby="llm-heading" aria-busy={loading}>
  <h2 id="llm-heading">{$i18n.t('nav.llm')}</h2>
  <form onsubmit={save}>
    <fieldset disabled={disabled || loading}>
      <div class="fields">
        <label for="llm-url">{$i18n.t('llm.url')}
          <input id="llm-url" type="url" required value={baseUrl} placeholder="https://example.com/v1"
            oninput={(event) => { baseUrl = event.currentTarget.value; apiKey = ''; clearKey = false; }} />
        </label>
        <label for="llm-key">{$i18n.t('llm.key')}
          <input id="llm-key" type="password" autocomplete="off" bind:value={apiKey}
            oninput={() => { clearKey = false; }} aria-describedby="key-help" />
        </label>
      </div>
      <p id="key-help" class="help">{clearKey ? $i18n.t('llm.keyClearHelp') : samePersonalUrl && connection?.has_api_key ? $i18n.t('llm.keyKeepHelp') : $i18n.t('llm.keyHelp')}</p>
      <div class="actions">
        <button class="primary" type="submit">{loading ? $i18n.t('llm.processing') : $i18n.t('llm.connect')}</button>
        <button type="button" onclick={disconnect} disabled={connection?.source !== 'personal'}>{$i18n.t('llm.disconnect')}</button>
        <button type="button" onclick={() => { clearKey = true; apiKey = ''; }} disabled={!samePersonalUrl || !connection?.has_api_key || clearKey}>{$i18n.t('llm.clearKey')}</button>
        <button type="button" onclick={() => { void run(reload); }}>{$i18n.t('common.reload')}</button>
      </div>
    </fieldset>
  </form>
  <p class="status" role="status">{loading ? $i18n.t('llm.checking') : $i18n.message(notice) || (connection?.source === 'personal' ? $i18n.t('llm.source.personal') : connection?.source === 'server' ? $i18n.t('llm.source.server') : $i18n.t('llm.source.none'))}</p>
  {#if error}<p class="error" role="alert">{$i18n.message(error)}</p>{/if}
</section>

<style>
  .llm-panel { flex: none; width: min(calc(100% - 48px), var(--form-width)); margin: 24px auto; padding: calc(3 * var(--space)); border: 1px solid var(--border); border-radius: var(--radius); background: var(--surface); }
  h2 { margin: 0 0 12px; font-size: 20px; }
  fieldset { margin: 0; padding: 0; border: 0; min-width: 0; }
  .fields { display: grid; grid-template-columns: 1fr; gap: 16px; }
  label { display: grid; gap: 6px; padding: calc(1.5 * var(--space)); border-radius: var(--radius); background: var(--paper); color: var(--muted); font-size: 13px; }
  input { width: 100%; min-width: 0; min-height: 44px; padding: 9px 12px; border: 0; border-radius: var(--radius); background: transparent; color: var(--ink); }
  .actions { display: flex; flex-wrap: wrap; gap: 8px; }
  button { min-height: 44px; padding: 8px 12px; border: 1px solid var(--border); border-radius: var(--radius); background: var(--surface); color: var(--ink); }
  .primary { background: var(--accent); color: var(--surface); }
  :is(input, button):focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  :is(input, button):disabled { opacity: .65; }
  .help, .status, .error { margin: 10px 0; font-size: 13px; line-height: 1.5; overflow-wrap: anywhere; }
  .help { color: var(--muted); }
  .status { margin-bottom: 0; }
  .error { color: var(--error); }
</style>
