<script lang="ts">
  import { i18n } from '../../i18n/index.ts';
  import type { UiMessage } from '../../i18n/messages.ts';
  import { tick } from 'svelte';
  import type { ModelsResult } from './llm-api.ts';

  let { catalog, loading, disabled, error, onselect, onreload, compact = false, toolbar = false, id = 'model' }: {
    toolbar?: boolean;
    id?: string;
    compact?: boolean;
    catalog: ModelsResult | null;
    loading: boolean;
    disabled: boolean;
    error: UiMessage | null;
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
  let filtered = $derived.by(() => {
    const matches = items.filter(item => `${item.name} ${item.id}`.toLowerCase().includes(search.trim().toLowerCase()));
    const selected = matches.find(item => item.id === catalog?.selected_model_id);
    return selected ? [selected, ...matches.filter(item => item !== selected)] : matches;
  });

  /** Position the native popover above/below the trigger inside the desktop viewport. */
  function toggleOpen() {
    if (disabled || loading || !items.length) return;
    if (open) { menu.hidePopover(); return; }
    const rect = trigger.getBoundingClientRect();
    const below = innerHeight - rect.bottom - 8;
    const above = rect.top - 8;
    const height = Math.min(480, Math.max(120, Math.max(below, above) - 4));
    const width = Math.min(360, innerWidth - 16);
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
      document.getElementById(`${id}-option-${activeIndex}`)?.scrollIntoView({ block: 'nearest' });
    } else if (event.key === 'Enter') {
      event.preventDefault();
      const item = filtered[activeIndex < 0 ? 0 : activeIndex];
      if (item) void pick(item.id);
    }
  }

  // ponytail: native popover handles outside clicks and overlay placement without a library.
  $effect(() => { if (disabled || loading) menu?.hidePopover(); });
</script>

<!-- Rounded search/tick rows adapted from legacy chat/ModelSelector/Selector.svelte. -->
<div class="model-selector" class:compact class:toolbar aria-busy={loading}>
  <div class="controls">
    <button class="trigger" type="button" bind:this={trigger} onclick={toggleOpen}
      aria-label={$i18n.t('model.choose')} aria-haspopup="listbox" aria-expanded={open}
      disabled={disabled || loading || !items.length} title={selectedName ?? $i18n.t('model.choose')}><span class="selected-name">{toolbar ? selectedName ?? $i18n.t('model.choose') : $i18n.t('model.prefix', {name: selectedName ?? $i18n.t('model.choose')})}</span><span class="chevron" aria-hidden="true"><svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="m4 6 4 4 4-4"/></svg></span></button>
    {#if !toolbar}<button type="button" aria-label={$i18n.t('model.reload')} onclick={onreload} disabled={disabled || loading}>{#if compact}<span aria-hidden="true">↻</span>{:else}{$i18n.t('common.reload')}{/if}</button>{/if}
  </div>
  {#if loading}<p role="status">{$i18n.t('model.checking')}</p>
  {:else if catalog?.selection_required}<p role="status">{$i18n.t('model.missing')}</p>
  {:else if !items.length && !error}<p role="status">{$i18n.t('model.connectFirst')}</p>{/if}
  {#if error}<p class="error" role="alert">{$i18n.message(error)}</p>{/if}
</div>

<div class="menu" id={`${id}-menu`} popover="auto" bind:this={menu}
  ontoggle={(event) => { open = event.newState === 'open'; }}
  style:top={`${position.top}px`} style:left={`${position.left}px`}
  style:width={`${position.width}px`} style:max-height={`${position.maxHeight}px`}>
  <div class="search-bar">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4.5 4.5"/></svg>
    <input id={`${id}-search`} bind:this={searchInput} bind:value={search} type="search" role="combobox"
      placeholder={$i18n.t('model.search')+'…'} aria-label={$i18n.t('model.search')} aria-controls={`${id}-list`} aria-expanded={open} aria-autocomplete="list"
      aria-activedescendant={activeIndex >= 0 ? `${id}-option-${activeIndex}` : undefined}
      oninput={() => { activeIndex = -1; }} onkeydown={handleKeydown} disabled={disabled || loading} />
  </div>
  {#if open}
    <div class="options" id={`${id}-list`} role="listbox" aria-label={$i18n.t('model.list')}>
      {#each filtered as item, index (item.id)}
        {#if index === 0 || index === 1 && filtered[0].id === catalog?.selected_model_id}
          <p class="group-label" role="presentation">{item.id === catalog?.selected_model_id ? $i18n.t('model.current') : $i18n.t('model.all')}</p>
        {/if}
        <button id={`${id}-option-${index}`} type="button" role="option"
          aria-selected={item.id === catalog?.selected_model_id} class:active={index === activeIndex}
          onclick={() => { void pick(item.id); }} disabled={disabled || loading}>
          <span class="model-copy"><span class="model-name">{item.name}</span><small>{item.id}</small></span>
          {#if item.id === catalog?.selected_model_id}<span class="selected-check" aria-hidden="true"><svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><path d="m3 8 3 3 7-7"/></svg></span>{/if}
        </button>
      {/each}
      {#if !filtered.length}<p class="empty-models" role="status">{$i18n.t('model.noMatch')}</p>{/if}
    </div>
  {/if}
</div>

<style>
  .model-selector { margin-bottom: 12px; }
  .controls { display: flex; flex-wrap: wrap; gap: 8px; }
  button, input { min-height: 44px; border: 1px solid var(--border); border-radius: var(--radius); background: var(--surface); color: var(--ink); }
  button { padding: 8px 12px; }
  .trigger { border: 0; background: transparent; font-size: 18px; font-weight: 600; display: flex; align-items: center; justify-content: space-between; gap: 12px; min-width: 0; max-width: 100%; text-align: left; overflow-wrap: anywhere; }
  .chevron{display:flex;align-items:center;flex:none;transform:rotate(0deg);transition:transform 150ms ease;}
  .trigger[aria-expanded="true"] .chevron{transform:rotate(180deg);}
  @media(prefers-reduced-motion:reduce){.chevron{transition:none;}}
  .selected-name { min-width: 0; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
  :is(button, input):focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  button:disabled { opacity: .65; }
  .menu { position:fixed;inset:auto;margin:0;padding:0;box-sizing:border-box;display:none;flex-direction:column;border:1px solid var(--border);border-radius:12px;background:var(--surface);color:var(--ink);box-shadow:0 12px 32px #0005;overflow:hidden;color-scheme:var(--control-color-scheme,dark); }
  .menu:popover-open{display:flex;}
  .search-bar{position:relative;flex:none;margin:14px 14px 0;padding-bottom:14px;border-bottom:1px solid var(--border);}
  .search-bar>svg{position:absolute;left:12px;top:13px;color:var(--muted);pointer-events:none;}
  .search-bar input{width:100%;height:44px;min-height:44px;padding:10px 12px 10px 38px;border-radius:8px;background:var(--paper);font-size:14px;}
  input::placeholder{color:var(--muted);}
  .options{flex:1;min-height:0;padding:6px 8px 10px;overflow-y:auto;overscroll-behavior:contain;scrollbar-width:thin;scrollbar-color:var(--border) transparent;}
  .options::-webkit-scrollbar{width:6px;}.options::-webkit-scrollbar-track{background:transparent;}.options::-webkit-scrollbar-thumb{background:var(--border);border-radius:8px;}
  .options button{display:flex;justify-content:flex-start;align-items:center;gap:12px;width:100%;min-height:64px;padding:10px 12px;border:0;border-radius:8px;background:transparent;text-align:left;}
  .options button:hover,.options button.active{background:var(--soft);}
  .options button[aria-selected="true"]{background:color-mix(in srgb,var(--soft) 80%,transparent);}
  .model-copy{display:grid;gap:3px;min-width:0;flex:1;}
  .model-name{font-size:14px;line-height:1.4;font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
  small{display:block;color:var(--muted);font-size:12px;line-height:1.4;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
  .selected-check{display:grid;place-items:center;flex:none;width:22px;height:22px;border-radius:50%;background:var(--accent);color:var(--paper);}
  p{margin:8px 0 0;font-size:13px;line-height:1.5;}
  .group-label{padding:10px 12px 6px;margin:0;color:var(--muted);font-size:10px;font-weight:600;letter-spacing:.07em;text-transform:uppercase;}
  .empty-models{padding:18px 12px;color:var(--muted);}
  .error { color: var(--error); }
  .toolbar{margin:0;min-width:0;width:100%;}
  .toolbar .trigger{width:100%;font-size:15px;font-weight:400;padding:0;min-height:44px;display:flex;gap:8px;}
  .toolbar .controls{width:100%;}
  .toolbar .selected-name{display:block;white-space:nowrap;text-overflow:ellipsis;}
  .toolbar .trigger>span:last-child{display:flex;align-items:center;flex:none;}
  .compact{margin:0;}
  .compact .controls{flex-wrap:nowrap;gap:4px;align-items:center;}
  .compact .trigger{font-size:14px;font-weight:400;padding:8px;}
  .compact .controls>button:last-child{border:0;background:transparent;padding:8px;min-width:44px;}
  .compact p{font-size:12px;}
</style>
