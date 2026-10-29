<script lang="ts">
  interface ModelItem {
    id: string;
    name: string;
    available: boolean;
  }

  interface Labels {
    heading: string;
    search: string;
    allow: string;
    defaultModel: string;
    unavailable: string;
    empty: string;
    noMatches: string;
    help: string;
    selectAll?: string;
  }

  let {
    id,
    models,
    allowedModelIds,
    defaultModelId,
    disabled = false,
    error = null,
    labels,
    onchange,
  }: {
    id: string;
    models: readonly ModelItem[];
    allowedModelIds: readonly string[];
    defaultModelId: string | null;
    disabled?: boolean;
    error?: string | null;
    labels: Labels;
    onchange: (next: { allowedModelIds: string[]; defaultModelId: string | null }) => void;
  } = $props();

  let search = $state('');
  let trimmedSearch = $derived(search.trim().toLowerCase());
  let filteredModels = $derived.by(() => {
    if (!trimmedSearch) return models;
    return models.filter(
      (m) =>
        m.name.toLowerCase().includes(trimmedSearch) || m.id.toLowerCase().includes(trimmedSearch),
    );
  });

  let selectableModels = $derived(
    filteredModels.filter((model) => model.available || allowedModelIds.includes(model.id)),
  );
  let selectedCount = $derived(
    selectableModels.filter((model) => allowedModelIds.includes(model.id)).length,
  );
  let allSelected = $derived(
    selectableModels.length > 0 && selectedCount === selectableModels.length,
  );
  let partlySelected = $derived(selectedCount > 0 && !allSelected);

  function handleToggleAll() {
    if (disabled || selectableModels.length === 0) return;
    const visibleIds = new Set(selectableModels.map((model) => model.id));
    const nextAllowed = allSelected
      ? allowedModelIds.filter((modelId) => !visibleIds.has(modelId))
      : Array.from(
          new Set([
            ...allowedModelIds,
            ...selectableModels.filter((model) => model.available).map((model) => model.id),
          ]),
        );
    onchange({
      allowedModelIds: nextAllowed,
      defaultModelId:
        defaultModelId && nextAllowed.includes(defaultModelId) ? defaultModelId : null,
    });
  }

  function handleToggleAllow(modelId: string, available: boolean) {
    if (disabled) return;
    const isCurrentlyAllowed = allowedModelIds.includes(modelId);
    if (isCurrentlyAllowed) {
      const nextAllowed = allowedModelIds.filter((mid) => mid !== modelId);
      const nextDefault = defaultModelId === modelId ? null : defaultModelId;
      onchange({
        allowedModelIds: nextAllowed,
        defaultModelId: nextDefault,
      });
    } else {
      if (!available) return;
      const nextAllowed = Array.from(new Set([...allowedModelIds, modelId]));
      onchange({
        allowedModelIds: nextAllowed,
        defaultModelId,
      });
    }
  }

  function handleSelectDefault(modelId: string, available: boolean) {
    if (disabled || !available || !allowedModelIds.includes(modelId)) return;
    if (defaultModelId === modelId) return;
    onchange({
      allowedModelIds: [...allowedModelIds],
      defaultModelId: modelId,
    });
  }

  function restoreControlledRadios(input: HTMLInputElement) {
    // Native radio activation unchecks its sibling before onchange. Restore the
    // parent's selection before emitting a proposal which the parent may decline.
    const radios = input
      .closest('section')
      ?.querySelectorAll<HTMLInputElement>('input[type="radio"]');
    radios?.forEach((radio) => {
      radio.checked = radio.dataset.modelId === defaultModelId;
    });
  }
</script>

<section class="model-policy-editor" {id} aria-labelledby="{id}-heading">
  <div class="editor-header">
    <h3 id="{id}-heading" class="editor-heading">{labels.heading}</h3>
    <p id="{id}-help" class="editor-help">{labels.help}</p>
  </div>

  {#if error}
    <p id="{id}-error" class="editor-error" role="alert">{error}</p>
  {/if}

  <div class="search-section">
    <label for="{id}-search" class="search-label">{labels.search}</label>
    <input
      id="{id}-search"
      type="search"
      class="search-input"
      bind:value={search}
      {disabled}
      placeholder={labels.search}
      autocomplete="off"
    />
  </div>

  <div class="models-container">
    {#if models.length === 0}
      <p id="{id}-empty" class="status-message" role="status">{labels.empty}</p>
    {:else if filteredModels.length === 0}
      <p id="{id}-no-matches" class="status-message" role="status">{labels.noMatches}</p>
    {:else}
      <table class="model-list" aria-label={labels.heading}>
        <thead
          ><tr
            ><th scope="col">{labels.heading}</th><th scope="col">
              <label class="bulk-control" title={labels.selectAll ?? labels.allow}>
                <input
                  id="{id}-allow-all"
                  type="checkbox"
                  checked={allSelected}
                  indeterminate={partlySelected}
                  aria-label={labels.selectAll ?? labels.allow}
                  disabled={disabled || selectableModels.length === 0}
                  onchange={(event) => {
                    event.currentTarget.checked = allSelected;
                    event.currentTarget.indeterminate = partlySelected;
                    handleToggleAll();
                  }}
                />
                <span>{labels.allow}</span>
              </label>
            </th><th scope="col">{labels.defaultModel}</th></tr
          ></thead
        ><tbody>
          {#each filteredModels as model, index (model.id)}
            {@const isAllowed = allowedModelIds.includes(model.id)}
            {@const isDefault = defaultModelId === model.id}
            {@const allowId = `${id}-allow-${index}`}
            {@const defaultId = `${id}-default-${index}`}
            <tr class="model-item" class:is-unavailable={!model.available}>
              <td class="model-meta">
                <div class="model-name-row">
                  <span id="{id}-model-name-{index}" class="model-name">{model.name}</span>
                  {#if !model.available}
                    <span class="unavailable-tag">{labels.unavailable}</span>
                  {/if}
                </div>
                <span id="{id}-model-id-{index}" class="model-id">{model.id}</span>
              </td><td class="model-controls">
                <label class="control-option" for={allowId}>
                  <input
                    id={allowId}
                    type="checkbox"
                    checked={isAllowed}
                    aria-labelledby={`${allowId}-label ${id}-model-name-${index} ${id}-model-id-${index}`}
                    disabled={disabled || (!model.available && !isAllowed)}
                    onchange={(event) => {
                      event.currentTarget.checked = isAllowed;
                      handleToggleAllow(model.id, model.available);
                    }}
                  />
                  <span id={`${allowId}-label`} class="control-text">{labels.allow}</span>
                </label>
              </td><td class="model-controls">
                <label class="control-option" for={defaultId}>
                  <input
                    id={defaultId}
                    type="radio"
                    name="{id}-default-group"
                    checked={isDefault}
                    data-model-id={model.id}
                    aria-labelledby={`${defaultId}-label ${id}-model-name-${index} ${id}-model-id-${index}`}
                    disabled={disabled || !model.available || !isAllowed}
                    onchange={(event) => {
                      restoreControlledRadios(event.currentTarget);
                      handleSelectDefault(model.id, model.available);
                    }}
                  />
                  <span id={`${defaultId}-label`} class="control-text">{labels.defaultModel}</span>
                </label>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </div>
</section>

<style>
  .model-policy-editor {
    box-sizing: border-box;
    width: 100%;
    max-width: 100%;
    margin: 0;
    padding: calc(2.5 * var(--space));
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--ink);
    overflow-x: hidden;
  }

  .editor-header {
    margin-bottom: calc(2 * var(--space));
  }

  .editor-heading {
    margin: 0 0 calc(0.5 * var(--space));
    font-size: 18px;
    font-weight: 600;
    line-height: 1.4;
    color: var(--ink);
  }

  .editor-help {
    margin: 0;
    font-size: 13px;
    line-height: 1.5;
    color: var(--muted);
    overflow-wrap: anywhere;
  }

  .editor-error {
    margin: 0 0 calc(2 * var(--space));
    padding: 10px 12px;
    background: var(--paper);
    border: 1px solid var(--error);
    border-radius: calc(var(--radius) / 2);
    color: var(--error);
    font-size: 13px;
    line-height: 1.5;
    overflow-wrap: anywhere;
  }

  .search-section {
    display: grid;
    gap: 6px;
    margin-bottom: calc(2 * var(--space));
  }

  .search-label {
    font-size: 13px;
    font-weight: 500;
    color: var(--muted);
  }

  .search-input {
    width: 100%;
    min-height: 44px;
    padding: 8px 12px;
    box-sizing: border-box;
    border: 1px solid var(--border);
    border-radius: calc(var(--radius) / 2);
    background: var(--paper);
    color: var(--ink);
    font-size: 14px;
  }

  .models-container {
    max-height: 360px;
    overflow: auto;
    scrollbar-gutter: stable;
    scrollbar-width: thin;
    scrollbar-color: var(--border) transparent;
    border-radius: 7px;
    min-width: 0;
  }

  .models-container:hover {
    scrollbar-color: var(--muted) transparent;
  }
  .models-container::-webkit-scrollbar {
    width: 8px;
    height: 8px;
  }
  .models-container::-webkit-scrollbar-thumb {
    background: var(--border);
    border: 2px solid var(--surface);
    border-radius: 8px;
  }
  .models-container::-webkit-scrollbar-thumb:hover {
    background: var(--muted);
  }
  .bulk-control {
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    gap: 6px;
    cursor: pointer;
  }
  .bulk-control input {
    width: 16px;
    height: 16px;
    margin: 0;
    accent-color: var(--accent);
    cursor: inherit;
  }
  .bulk-control:has(input:disabled) {
    cursor: not-allowed;
    opacity: 0.65;
  }

  .model-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: calc(1.5 * var(--space));
  }

  .model-item {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: calc(1.5 * var(--space));
    border: 1px solid var(--border);
    border-radius: calc(var(--radius) / 2);
    background: var(--paper);
    min-width: 0;
    box-sizing: border-box;
  }

  .model-item.is-unavailable {
    opacity: 0.85;
  }

  .model-meta {
    flex: 1 1 200px;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .model-name-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    min-width: 0;
  }

  .model-name {
    font-size: 15px;
    font-weight: 600;
    color: var(--ink);
    overflow-wrap: anywhere;
    word-break: break-word;
  }

  .unavailable-tag {
    display: inline-flex;
    align-items: center;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
    border-radius: 9999px;
    background: var(--border);
    color: var(--muted);
    white-space: nowrap;
  }

  .model-id {
    font-size: 12px;
    color: var(--muted);
    font-family: monospace;
    overflow-wrap: anywhere;
    word-break: break-all;
    min-width: 0;
  }

  .model-controls {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 16px;
    flex-shrink: 0;
  }

  .control-option {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
    font-size: 13px;
    color: var(--ink);
    user-select: none;
    min-height: 44px;
  }

  .control-option input {
    cursor: pointer;
    width: 16px;
    height: 16px;
    margin: 0;
    accent-color: var(--accent);
  }

  .control-option:has(input:disabled) {
    cursor: not-allowed;
    color: var(--muted);
    opacity: 0.65;
  }

  .control-option input:disabled {
    cursor: not-allowed;
  }

  :is(input):focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }

  .status-message {
    margin: calc(2 * var(--space)) 0;
    padding: calc(2 * var(--space));
    text-align: center;
    font-size: 14px;
    color: var(--muted);
    background: var(--paper);
    border-radius: calc(var(--radius) / 2);
  }

  @media (max-width: 480px) {
    .model-meta {
      flex: none;
      width: 100%;
    }
    .model-item {
      flex-direction: column;
      align-items: flex-start;
    }

    .model-controls {
      width: 100%;
      justify-content: flex-start;
      padding-top: 6px;
      border-top: 1px dashed var(--border);
    }
  }

  .model-policy-editor {
    border: 0;
    padding: 0;
    background: transparent;
    overflow: visible;
  }
  .editor-heading {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip-path: inset(50%);
  }
  .editor-header {
    margin-bottom: 12px;
  }
  .search-section {
    margin-bottom: 12px;
  }
  .model-list {
    display: table;
    width: 100%;
    table-layout: fixed;
    border-collapse: collapse;
    border: 1px solid var(--border);
    border-radius: 7px;
  }
  th {
    position: sticky;
    top: 0;
    z-index: 1;
    padding: 10px 12px;
    background: var(--soft);
    text-align: left;
    color: var(--ink);
    font-size: 12px;
    font-weight: 600;
  }
  th:not(:first-child) {
    width: 90px;
    text-align: center;
  }
  .model-item {
    display: table-row;
    background: transparent;
  }
  .model-meta {
    display: table-cell;
    padding: 10px 12px;
    width: auto;
    vertical-align: middle;
  }
  .model-controls {
    display: table-cell;
    padding: 4px;
    text-align: center;
    vertical-align: middle;
    border-top: 1px solid var(--border);
  }
  .model-name {
    font-size: 14px;
  }
  .model-id {
    display: block;
    margin-top: 4px;
    font-family: inherit;
    font-size: 12px;
  }
  .control-option {
    display: inline-flex;
    justify-content: center;
    min-width: 44px;
  }
  .control-text {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip-path: inset(50%);
  }
  @media (max-width: 480px) {
    th:not(:first-child) {
      width: 64px;
      padding: 8px 2px;
    }
    .model-controls {
      width: auto;
    }
    .model-meta {
      width: auto;
      padding: 8px;
    }
  }
</style>
