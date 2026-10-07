<script lang="ts">
  import { tick } from 'svelte';
  import type { ModelsResult } from '../llm-api.ts';

  let { catalog, loading, disabled, error, onselect, onreload }: {
    catalog: ModelsResult | null;
    loading: boolean;
    disabled: boolean;
    error: string;
    onselect: (id: string) => Promise<boolean>;
    onreload: () => void;
  } = $props();
  let trigger: HTMLButtonElement;
  let menu: HTMLDivElement;
  let searchInput: HTMLInputElement;
  let open = $state(false);
  let search = $state('');
  let activeIndex = $state(-1);
  let position = $state({ top: 0, left: 8, width: 320, maxHeight: 320 });
  let items = $derived(catalog?.models ?? []);
  let selectedName = $derived(items.find((item) => item.id === catalog?.selected_model_id)?.name);
  // Plain substring search is enough for one provider's id/name catalog.
  let filtered = $derived(items.filter((item) => `${item.name} ${item.id}`.toLowerCase().includes(search.trim().toLowerCase())));

  /** Position the native popover above/below the trigger without clipping on mobile. */
  function toggleOpen() {
    if (disabled || loading || !items.length) return;
    if (open) { menu.hidePopover(); return; }
    const rect = trigger.getBoundingClientRect();
    const below = innerHeight - rect.bottom - 8;
    const above = rect.top - 8;
    const height = Math.min(320, Math.max(below, above));
    const width = Math.min(420, innerWidth - 16);
    position = {
      top: below >= height ? rect.bottom + 4 : Math.max(8, rect.top - height - 4),
      left: Math.max(8, Math.min(rect.left, innerWidth - width - 8)),
      width, maxHeight: height
    };
    search = '';
    activeIndex = -1;
    menu.showPopover();
    searchInput.focus();
  }

  /** Save through the parent; its confirmed ID determines the tick and next chat. */
  async function pick(id: string) {
    if (disabled || loading) return;
    await onselect(id);
    await tick();
    if (!disabled && !loading) { menu.hidePopover(); trigger.focus(); }
  }

  async function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape') {
      event.preventDefault();
      menu.hidePopover();
      trigger.focus();
    } else if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      if (!filtered.length) return;
      const step = event.key === 'ArrowDown' ? 1 : -1;
      activeIndex = activeIndex < 0 ? (step === 1 ? 0 : filtered.length - 1) : (activeIndex + step + filtered.length) % filtered.length;
      await tick();
      document.getElementById(`model-option-${activeIndex}`)?.scrollIntoView({ block: 'nearest' });
    } else if (event.key === 'Enter') {
      event.preventDefault();
      const item = filtered[activeIndex < 0 ? 0 : activeIndex];
      if (item) void pick(item.id);
    }
  }

  // ponytail: native popover handles outside clicks and overlay placement without a library.
  $effect(() => { if (disabled || loading) menu?.hidePopover(); });
</script>

<div class="model-selector" aria-busy={loading}>
  <div class="controls">
    <button class="trigger" type="button" bind:this={trigger} onclick={toggleOpen}
      aria-label="Chọn model" aria-haspopup="listbox" aria-expanded={open}
      disabled={disabled || loading || !items.length}>Model: {selectedName ?? 'Chọn model'} <span aria-hidden="true">⌄</span></button>
    <button type="button" aria-label="Tải lại model" onclick={onreload} disabled={disabled || loading}>Tải lại</button>
  </div>
  {#if loading}<p role="status">Đang kiểm tra model…</p>
  {:else if catalog?.selection_required}<p role="status">Model đã lưu không còn khả dụng. Hãy chọn lại model.</p>
  {:else if !items.length && !error}<p role="status">Kết nối LLM để lấy danh sách model.</p>{/if}
  {#if error}<p class="error" role="alert">{error}</p>{/if}
</div>

<div class="menu" id="model-menu" popover="auto" bind:this={menu}
  ontoggle={(event) => { open = event.newState === 'open'; }}
  style:top={`${position.top}px`} style:left={`${position.left}px`}
  style:width={`${position.width}px`} style:max-height={`${position.maxHeight}px`}>
  <label for="model-search">Tìm model</label>
  <input id="model-search" bind:this={searchInput} bind:value={search} type="search" role="combobox"
    aria-label="Tìm model" aria-controls="model-list" aria-expanded={open} aria-autocomplete="list"
    aria-activedescendant={activeIndex >= 0 ? `model-option-${activeIndex}` : undefined}
    oninput={() => { activeIndex = -1; }} onkeydown={handleKeydown} disabled={disabled || loading} />
  {#if open}
    <div class="options" id="model-list" role="listbox" aria-label="Danh sách model">
      {#each filtered as item, index (item.id)}
        <button id={`model-option-${index}`} type="button" role="option"
          aria-selected={item.id === catalog?.selected_model_id} class:active={index === activeIndex}
          onclick={() => { void pick(item.id); }} disabled={disabled || loading}>
          <span>{item.name}<small>{item.id}</small></span>
          {#if item.id === catalog?.selected_model_id}<span aria-hidden="true">✓</span>{/if}
        </button>
      {/each}
    </div>
    {#if !filtered.length}<p role="status">Không có model phù hợp.</p>{/if}
  {/if}
</div>

<style>
  .model-selector { margin-bottom: 12px; }
  .controls { display: flex; gap: 8px; }
  button, input { min-height: 44px; border: 1px solid var(--border); border-radius: 9px; background: var(--surface); color: var(--ink); }
  button { padding: 8px 12px; }
  .trigger { display: flex; align-items: center; justify-content: space-between; gap: 12px; min-width: 0; max-width: 100%; text-align: left; overflow-wrap: anywhere; }
  :is(button, input):focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  button:disabled { opacity: .65; }
  .menu { position: fixed; inset: auto; margin: 0; padding: 12px; border: 1px solid var(--border); border-radius: 12px; background: var(--surface); color: var(--ink); box-shadow: 0 8px 24px #0002; overflow: auto; }
  label { display: block; margin-bottom: 6px; font-size: 13px; }
  input { width: 100%; padding: 8px 10px; }
  .options { margin-top: 8px; max-height: 220px; overflow-y: auto; }
  .options button { display: flex; justify-content: space-between; align-items: center; gap: 10px; width: 100%; border: 0; text-align: left; overflow-wrap: anywhere; }
  .options button:hover, .options button.active, .options button[aria-selected="true"] { background: var(--soft); }
  small { display: block; color: var(--muted); font-size: 12px; }
  p { margin: 8px 0 0; font-size: 13px; line-height: 1.5; }
  .error { color: #9a3530; }
</style>
