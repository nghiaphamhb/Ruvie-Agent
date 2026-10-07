<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import {
    LlmApiError, getLlmConnection, getModels, saveLlmConnection, deleteLlmConnection,
    type LlmConnection, type ModelsResult, type ConnectionInput
  } from '../llm-api.ts';

  let { csrfToken, disabled = false, onexpired, onbusychange }: {
    csrfToken: string;
    disabled?: boolean;
    onexpired: () => void;
    onbusychange: (busy: boolean) => void;
  } = $props();
  let connection = $state<LlmConnection | null>(null);
  let catalog = $state<ModelsResult | null>(null);
  let baseUrl = $state('');
  let apiKey = $state('');
  let clearKey = $state(false);
  let loading = $state(false);
  let error = $state('');
  let notice = $state('');
  // Invalidate pending responses when this account's form is removed.
  let sequence = 0;
  const normalizeUrl = (url: string) => url.trim().replace(/\/+$/, '');
  let samePersonalUrl = $derived(connection?.source === 'personal' && normalizeUrl(baseUrl) === connection.base_url);

  /** Reload metadata/catalog; saved keys never return to the browser. */
  async function reload(current: number) {
    const result = await getLlmConnection();
    if (current !== sequence) return;
    connection = result;
    baseUrl = result.base_url ?? '';
    apiKey = '';
    clearKey = false;
    catalog = null;
    if (result.source !== 'none') {
      const models = await getModels();
      if (current === sequence) catalog = models;
    }
  }

  /** Serialize form operations and ignore responses from an unmounted login session. */
  async function run(action: (current: number) => Promise<void>, initial = false) {
    if ((!initial && disabled) || loading) return;
    const current = ++sequence;
    loading = true;
    onbusychange(true);
    error = '';
    notice = '';
    try { await action(current); }
    catch (failure) {
      if (current !== sequence) return;
      if (failure instanceof LlmApiError && failure.status === 401) { onexpired(); return; }
      error = failure instanceof LlmApiError ? failure.message : 'Không thể đọc kết nối. Hãy thử lại.';
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
      catalog = result;
      apiKey = '';
      clearKey = false;
      const metadata = await getLlmConnection();
      if (current !== sequence) return;
      connection = metadata;
      baseUrl = metadata.base_url ?? '';
      notice = 'Đã lưu kết nối.';
    });
  }

  function disconnect() {
    void run(async (current) => {
      await deleteLlmConnection(csrfToken);
      if (current !== sequence) return;
      await reload(current);
      if (current === sequence) notice = 'Đã gỡ kết nối riêng.';
    });
  }

  // Login may still be loading projects; metadata loading starts independently.
  onMount(() => { void run(reload, true); });
  onDestroy(() => { sequence += 1; apiKey = ''; });
</script>

<section class="llm-panel" aria-labelledby="llm-heading" aria-busy={loading}>
  <h2 id="llm-heading">Kết nối LLM</h2>
  <form onsubmit={save}>
    <fieldset disabled={disabled || loading}>
      <div class="fields">
        <label for="llm-url">Base URL
          <input id="llm-url" type="url" required value={baseUrl} placeholder="https://example.com/v1"
            oninput={(event) => { baseUrl = event.currentTarget.value; apiKey = ''; clearKey = false; }} />
        </label>
        <label for="llm-key">API key (tùy chọn)
          <input id="llm-key" type="password" autocomplete="off" bind:value={apiKey}
            oninput={() => { clearKey = false; }} aria-describedby="key-help" />
        </label>
      </div>
      <p id="key-help" class="help">{clearKey ? 'Key sẽ được xóa khi bấm Kết nối.' : samePersonalUrl && connection?.has_api_key ? 'Đã lưu key. Để trống để giữ key hiện tại.' : 'Chỉ nhập key khi dịch vụ yêu cầu.'}</p>
      <div class="actions">
        <button class="primary" type="submit">{loading ? 'Đang xử lý…' : 'Kết nối'}</button>
        <button type="button" onclick={disconnect} disabled={connection?.source !== 'personal'}>Gỡ kết nối</button>
        <button type="button" onclick={() => { clearKey = true; apiKey = ''; }} disabled={!samePersonalUrl || !connection?.has_api_key || clearKey}>Xóa key đã lưu</button>
        <button type="button" onclick={() => { void run(reload); }}>Tải lại</button>
      </div>
    </fieldset>
  </form>
  <p class="status" role="status">{loading ? 'Đang kiểm tra kết nối…' : notice || (connection?.source === 'personal' ? 'Đang dùng kết nối riêng.' : connection?.source === 'server' ? 'Đang dùng kết nối máy chủ.' : 'Chưa có kết nối LLM.')}</p>
  {#if catalog}
    <p class="help">Model: {catalog.models.find((model) => model.id === catalog?.selected_model_id)?.name ?? 'Cần chọn lại model'} · {catalog.models.length} model</p>
  {/if}
  {#if error}<p class="error" role="alert">{error}</p>{/if}
</section>

<style>
  .llm-panel { flex: none; margin: 16px 24px 0; padding: 18px; border: 1px solid var(--border); border-radius: 14px; background: var(--surface); }
  h2 { margin: 0 0 12px; font-size: 16px; }
  fieldset { margin: 0; padding: 0; border: 0; min-width: 0; }
  .fields { display: grid; grid-template-columns: 2fr 1fr; gap: 12px; }
  label { display: grid; gap: 6px; font-size: 13px; }
  input { width: 100%; min-width: 0; min-height: 44px; padding: 9px 12px; border: 1px solid var(--border); border-radius: 8px; background: var(--paper); color: var(--ink); }
  .actions { display: flex; flex-wrap: wrap; gap: 8px; }
  button { min-height: 44px; padding: 8px 12px; border: 1px solid var(--border); border-radius: 8px; background: var(--surface); color: var(--ink); }
  .primary { background: var(--accent); color: var(--surface); }
  :is(input, button):focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  :is(input, button):disabled { opacity: .65; }
  .help, .status, .error { margin: 10px 0; font-size: 13px; line-height: 1.5; overflow-wrap: anywhere; }
  .help { color: var(--muted); }
  .status { margin-bottom: 0; }
  .error { color: #9a3530; }
  @media (max-width: 600px) { .llm-panel { margin: 12px 12px 0; padding: 14px; } .fields { grid-template-columns: 1fr; } }
</style>
