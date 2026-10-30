<script lang="ts">
  import SurfaceDialog from '../../shared/SurfaceDialog.svelte';
  import { untrack, tick } from 'svelte';
  import { get } from 'svelte/store';
  import { toast } from 'svelte-sonner';
  import { i18n } from '../../i18n/index.ts';
  import { organizationLlmErrorMessage } from '../../i18n/messages.ts';
  import type { createOrganizationLlmState } from '../llm/organization-llm-state.svelte.ts';
  import type { createEmbeddingState } from '../embedding/embedding-state.svelte.ts';
  import EmbeddingModelSelector from '../embedding/EmbeddingModelSelector.svelte';
  import OrganizationModelPolicyEditor from '../llm/OrganizationModelPolicyEditor.svelte';
  let {
    state: owner,
    disabled = false,
    active = false,
    visible = true,
    embedding = false,
  }: {
    state: ReturnType<typeof createOrganizationLlmState> | ReturnType<typeof createEmbeddingState>;
    embedding?: boolean;
    visible?: boolean;
    disabled?: boolean;
    active?: boolean;
  } = $props();
  const id = (value: string) =>
    embedding
      ? value
          .replaceAll('llm-', 'embedding-')
          .replaceAll('connection-step', 'embedding-connection-step')
          .replaceAll('policy-step', 'embedding-policy-step')
      : value;
  let reloadConfirm = $state(false);
  let keyMenu: HTMLDivElement;
  let keyTrigger: HTMLButtonElement;
  let menuOpen = $state(false),
    hintDismissed = $state(false);
  let menuPosition = $state({ top: 0, left: 0, width: 240 });
  let showKey = $state(false);
  let operationGeneration = 0;
  const actionLabels = $derived({
    keep: $i18n.t('llm.org.keep'),
    replace: $i18n.t('llm.org.replace'),
    clear: $i18n.t('llm.org.clear'),
  });
  const actions = ['keep', 'replace', 'clear'] as const;
  async function openKeyMenu(event?: KeyboardEvent) {
    if (disabled || owner.busy) return;
    if (event && !['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return;
    event?.preventDefault();
    const rect = keyTrigger.getBoundingClientRect();
    menuPosition = {
      top: rect.bottom + 164 > innerHeight ? Math.max(8, rect.top - 160) : rect.bottom + 4,
      left: Math.max(8, Math.min(rect.left, innerWidth - rect.width - 8)),
      width: Math.min(rect.width, innerWidth - 16),
    };
    keyMenu.showPopover();
    await tick();
    const options = keyMenu.querySelectorAll<HTMLButtonElement>('button:not(:disabled)');
    (event?.key === 'ArrowUp' || event?.key === 'End'
      ? options[options.length - 1]
      : options[0]
    )?.focus();
  }
  function menuKeydown(event: KeyboardEvent) {
    const options = [...keyMenu.querySelectorAll<HTMLButtonElement>('button:not(:disabled)')];
    const current = options.indexOf(document.activeElement as HTMLButtonElement);
    if (event.key === 'Escape') {
      event.preventDefault();
      keyMenu.hidePopover();
      keyTrigger.focus();
    } else if (['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) {
      event.preventDefault();
      const index =
        event.key === 'Home'
          ? 0
          : event.key === 'End'
            ? options.length - 1
            : (current + (event.key === 'ArrowDown' ? 1 : -1) + options.length) % options.length;
      options[index]?.focus();
    }
  }
  /** Only explicit clicks notify; initial load and superseded requests remain quiet. */
  async function notifyOperation(operation: 'verify' | 'reload' | 'probe') {
    if (disabled || owner.busy) return;
    const generation = ++operationGeneration;
    const success = await (operation === 'verify'
      ? owner.verify()
      : operation === 'probe'
        ? owner.probe()
        : owner.open());
    if (!active || !visible || generation !== operationGeneration) return;
    const translations = get(i18n);
    if (success)
      toast.success(
        translations.t(
          operation === 'probe'
            ? 'ai.probeSuccess'
            : operation === 'verify'
              ? 'ai.catalogSuccess'
              : 'llm.org.reloaded',
        ),
        { id: id('llm-operation') },
      );
    else if (owner.errorCode)
      toast.error(translations.message(organizationLlmErrorMessage(owner.errorCode)), {
        id: id('llm-operation'),
      });
  }
  $effect(() => {
    const isActive = active;
    untrack(() => {
      if (isActive) void owner.open();
      else owner.close();
    });
    return () =>
      untrack(() => {
        operationGeneration++;
        showKey = false;
        keyMenu?.hidePopover();
        owner.close();
        toast.dismiss(id('llm-operation'));
      });
  });
  $effect(() => {
    if (!visible) {
      untrack(() => owner.suspend?.());
      operationGeneration++;
      showKey = false;
      keyMenu?.hidePopover();
      toast.dismiss(id('llm-operation'));
    }
  });
  const defaultModel = $derived(
    owner.models.find((model) => model.id === owner.defaultModelId && model.available),
  );
  let labels = $derived({
    heading: $i18n.t('llm.org.modelColumn'),
    search: $i18n.t('model.search'),
    allow: $i18n.t('llm.org.allow'),
    selectAll: $i18n.t('llm.org.selectAll'),
    defaultModel: $i18n.t('llm.org.default'),
    unavailable: $i18n.t('llm.org.unavailable'),
    empty: $i18n.t('llm.org.empty'),
    noMatches: $i18n.t('model.noMatch'),
    help: $i18n.t('llm.org.help'),
  });
</script>

<section
  class="llm-panel organization-connection"
  data-connection={embedding ? 'embedding' : 'reply'}
  aria-labelledby={id('llm-heading')}
  aria-busy={owner.busy}
>
  <header class="form-header">
    <div>
      <h2 id={id('llm-heading')}>{$i18n.t(embedding ? 'embedding.heading' : 'ai.reply')}</h2>
      <p class="subtitle">{$i18n.t(embedding ? 'embedding.subtitle' : 'llm.org.subtitle')}</p>
    </div>
    <button
      class="reload"
      type="button"
      disabled={disabled || owner.busy}
      onclick={() => (owner.dirty ? (reloadConfirm = true) : notifyOperation('reload'))}
      ><span aria-hidden="true">↻</span> {$i18n.t('common.reload')}</button
    >
  </header>
  <form
    onsubmit={(event) => {
      event.preventDefault();
      void owner.apply();
    }}
  >
    <fieldset disabled={disabled || owner.busy}>
      <section class="connection-section" aria-labelledby={id('connection-step')}>
        <h3 id={id('connection-step')}>
          <span class="step" aria-hidden="true">1</span>{$i18n.t('llm.org.connectionStep')}
        </h3>
        <div class="fields">
          <label for={id('llm-url')}
            >{$i18n.t('llm.url')}<input
              id={id('llm-url')}
              type="url"
              required
              bind:value={owner.baseUrl}
              placeholder="https://example.com/v1"
            /></label
          >
          <div class="key-field">
            <div class="key-label-row">
              <span id={id('llm-key-action-label')}>{$i18n.t('llm.org.apiKey')}</span>
              <span class="hint-wrap" class:hint-dismissed={hintDismissed}>
                <button
                  id={id('llm-key-hint-trigger')}
                  type="button"
                  class="hint-trigger"
                  aria-label={$i18n.t('llm.org.keyHint')}
                  aria-describedby={id('llm-key-hint')}
                  onpointerenter={() => (hintDismissed = false)}
                  onfocus={() => (hintDismissed = false)}
                  onkeydown={(event) => {
                    if (event.key === 'Escape') {
                      hintDismissed = true;
                      event.preventDefault();
                    }
                  }}
                >
                  <span aria-hidden="true">i</span>
                </button>
                <span id={id('llm-key-hint')} role="tooltip" class="key-hint">
                  <strong>{$i18n.t('llm.org.keep')}</strong><span
                    >{$i18n.t('llm.org.keepHint')}</span
                  >
                  <strong>{$i18n.t('llm.org.replace')}</strong><span
                    >{$i18n.t('llm.org.replaceHint')}</span
                  >
                  <strong>{$i18n.t('llm.org.clear')}</strong><span
                    >{$i18n.t('llm.org.clearHint')}</span
                  >
                  <span class="key-apply-hint">{$i18n.t('llm.org.keyApplyHint')}</span></span
                >
              </span>
            </div>
            <button
              id={id('llm-key-action')}
              class="key-trigger"
              type="button"
              bind:this={keyTrigger}
              aria-labelledby={id('llm-key-action-label llm-key-action-value')}
              aria-haspopup="listbox"
              aria-controls={id('llm-key-options')}
              aria-expanded={menuOpen}
              onclick={() => (menuOpen ? keyMenu.hidePopover() : openKeyMenu())}
              onkeydown={openKeyMenu}
            >
              <span id={id('llm-key-action-value')}>{actionLabels[owner.keyAction]}</span>
              <svg
                class="key-chevron"
                aria-hidden="true"
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
                stroke="currentColor"
                stroke-width="1.5"
                stroke-linecap="round"
                stroke-linejoin="round"><path d="m4 6 4 4 4-4" /></svg
              >
            </button>
          </div>

          {#if owner.keyAction === 'replace'}
            <div class="key-entry">
              <input
                id={id('llm-key')}
                aria-label={$i18n.t('llm.org.newKey')}
                type={showKey ? 'text' : 'password'}
                autocomplete="off"
                required
                maxlength="4096"
                bind:value={owner.apiKey}
              />
              <button
                type="button"
                class="visibility"
                aria-label={$i18n.t('llm.org.showKey')}
                aria-pressed={showKey}
                onclick={() => (showKey = !showKey)}
              >
                <svg
                  aria-hidden="true"
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.5"
                  ><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z" /><circle
                    cx="12"
                    cy="12"
                    r="3"
                  />{#if showKey}<path d="m3 3 18 18" />{/if}</svg
                >
              </button>
            </div>
            <p class="help">{$i18n.t('llm.org.newKeyHelp')}</p>
          {:else if owner.metadata?.has_api_key}<p class="help">
              {$i18n.t('llm.org.savedKey')}
            </p>{/if}
        </div>
        <div class="network-settings" role="group" aria-labelledby={id('llm-network-title')}>
          <h4 id={id('llm-network-title')}>{$i18n.t('ai.network.title')}</h4>
          <label for={id('llm-network-mode')}>
            {$i18n.t('ai.network.method')}
            <select id={id('llm-network-mode')} bind:value={owner.networkMode}>
              <option value="direct">{$i18n.t('ai.network.direct')}</option>
              <option value="proxy">{$i18n.t('ai.network.proxy')}</option>
            </select>
          </label>
          {#if owner.networkMode === 'proxy'}
            <label for={id('llm-network-proxy')}>
              {$i18n.t('ai.network.endpoint')}
              <input
                id={id('llm-network-proxy')}
                type="text"
                placeholder="socks5://127.0.0.1:12334"
                maxlength="2048"
                required
                autocomplete="off"
                aria-describedby={id('llm-network-help')}
                aria-invalid={owner.errorCode === 'invalid_network_configuration'}
                bind:value={owner.proxyUrl}
              />
            </label>
            <p id={id('llm-network-help')} class="help">{$i18n.t('ai.network.help')}</p>
            {#if owner.errorCode === 'invalid_network_configuration'}
              <p class="error" role="alert">{$i18n.t('ai.network.invalid')}</p>
            {/if}
          {/if}
        </div>
        <div class="connection-actions">
          <p class:verified={owner.verified} role="status">
            {#if owner.busy}{$i18n.t('llm.processing')}{:else if owner.verified}<span
                class="success-mark"
                aria-hidden="true"
                ><svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="3"
                  stroke-linecap="round"
                  stroke-linejoin="round"><path d="m5 12 4 4L19 6" /></svg
                >
              </span>{$i18n.t(embedding ? 'embedding.verified' : 'llm.org.catalogFound', {
                count: owner.models.length,
              })}{/if}
          </p>
          <button
            type="button"
            title={$i18n.t('llm.org.verifyHelp')}
            aria-describedby={id('llm-verify-help')}
            onclick={() => notifyOperation('verify')}
            disabled={!owner.baseUrl.trim() ||
              (owner.keyAction === 'replace' && !owner.apiKey.trim()) ||
              (owner.networkMode === 'proxy' && !owner.proxyUrl.trim())}
            >{$i18n.t('llm.org.verify')}</button
          >
        </div>
      </section>
      <section class="policy-section" aria-labelledby={id('policy-step')}>
        <h3 id={id('policy-step')}>
          <span class="step" aria-hidden="true">2</span>{$i18n.t(
            embedding ? 'embedding.heading' : 'llm.org.policyStep',
          )}
        </h3>
        {#if embedding && 'selectModel' in owner && owner.catalogReady}
          <EmbeddingModelSelector {owner} />
        {:else if !embedding && 'setPolicy' in owner && owner.verified}
          <OrganizationModelPolicyEditor
            id="organization-model-policy"
            models={owner.models}
            allowedModelIds={owner.allowedModelIds}
            defaultModelId={owner.defaultModelId}
            disabled={disabled || owner.busy}
            error={null}
            {labels}
            onchange={owner.setPolicy}
          />
        {:else}<p class="empty-policy">{$i18n.t('ai.verifyFirst')}</p>{/if}
      </section>
      {#if (embedding && 'catalogReady' in owner && owner.catalogReady) || (!embedding && owner.verified)}
        <button
          type="button"
          disabled={!owner.defaultModelId ||
            owner.busy ||
            (embedding &&
              'selectModel' in owner &&
              !owner.models.some(
                (model) => model.id === owner.defaultModelId && model.supported && model.available,
              ))}
          onclick={() => notifyOperation('probe')}>{$i18n.t('ai.probe')}</button
        >
        {#if !embedding && 'probeSuccess' in owner && owner.probeSuccess}<p role="status">
            {$i18n.t('ai.probeSuccess')}
          </p>{/if}
      {/if}
      {#if owner.verified && !owner.canApply && !owner.busy}<p role="status">
          {$i18n.t('ai.chooseModel')}
        </p>{/if}
      <footer class="form-footer">
        <p role="status">
          {#if owner.saved}{$i18n.t('llm.org.saved')}{:else if embedding && owner.verified}{$i18n.t(
              'embedding.profile',
            )}{:else if owner.verified}<span
              >{$i18n.t('llm.org.policyCount', { count: owner.allowedModelIds.length })}</span
            ><span class="default-summary"
              >{defaultModel
                ? $i18n.t('llm.org.defaultNamed', { name: defaultModel.name })
                : $i18n.t('llm.org.defaultMissing')}</span
            >{:else if !owner.metadata?.configured}{$i18n.t('llm.org.unconfigured')}{:else}{$i18n.t(
              owner.dirty ? 'llm.org.draft' : 'ai.loaded',
            )}{/if}
        </p>
        <button class="primary" type="submit" disabled={!owner.canApply}
          >{$i18n.t('llm.org.apply')}</button
        >
      </footer>
    </fieldset>
  </form>
  <span id={id('llm-verify-help')} class="sr-only">{$i18n.t('llm.org.verifyHelp')}</span>
  {#if owner.uncertain}<p class="error" role="alert">
      {$i18n.t('llm.org.unknown')}
    </p>{:else if owner.errorCode && owner.errorCode !== 'llm_settings_unavailable'}<p
      class="error"
      role="alert"
    >
      {$i18n.message(organizationLlmErrorMessage(owner.errorCode))}
    </p>{/if}
</section>

<SurfaceDialog
  open={reloadConfirm}
  title={$i18n.t('ai.reloadTitle')}
  className="reload-configuration-dialog"
  onclose={() => (reloadConfirm = false)}
>
  <p>{$i18n.t('ai.reloadHelp')}</p>
  <button
    class="keep-editing"
    type="button"
    data-dialog-initial-focus
    onclick={() => (reloadConfirm = false)}>{$i18n.t('ai.keepEditing')}</button
  >
  <button
    class="discard-reload"
    type="button"
    onclick={() => {
      reloadConfirm = false;
      void notifyOperation('reload');
    }}>{$i18n.t('ai.discardReload')}</button
  >
</SurfaceDialog>
<div
  id={id('llm-key-options')}
  class="key-options"
  popover="auto"
  role="listbox"
  tabindex="-1"
  aria-labelledby={id('llm-key-action-label')}
  bind:this={keyMenu}
  onkeydown={menuKeydown}
  ontoggle={(event) => (menuOpen = event.newState === 'open')}
  style:top={`${menuPosition.top}px`}
  style:left={`${menuPosition.left}px`}
  style:width={`${menuPosition.width}px`}
>
  {#each actions as action (action)}
    <button
      type="button"
      role="option"
      data-key-action={action}
      aria-selected={owner.keyAction === action}
      disabled={disabled || owner.busy || (action === 'keep' && !owner.canKeep)}
      onclick={() => {
        owner.keyAction = action;
        keyMenu.hidePopover();
        keyTrigger.focus();
      }}
    >
      <span>{actionLabels[action]}</span><span aria-hidden="true"
        >{owner.keyAction === action ? '✓' : ''}</span
      >
    </button>
  {/each}
</div>

<style>
  :global(.reload-configuration-dialog .keep-editing) {
    border-color: #d8e5f0;
    background: #fff;
    color: #073b65;
  }
  :global(.reload-configuration-dialog .keep-editing:hover) {
    background: #f0f6fc;
  }
  :global(.reload-configuration-dialog .discard-reload) {
    border-color: color-mix(in srgb, var(--error) 58%, var(--border));
    background: color-mix(in srgb, var(--error-bg) 84%, var(--surface));
    color: var(--error);
  }
  :global(.reload-configuration-dialog .discard-reload:hover) {
    background: color-mix(in srgb, var(--error-bg) 72%, var(--error) 28%);
  }
  .network-settings { display: grid; gap: 10px; padding: 12px 0; }
  .network-settings h4 { margin: 0; font-size: 14px; }
  .network-settings select { width: 100%; min-height: 44px; padding: 9px 12px;
    border: 1px solid var(--border); border-radius: var(--radius); background: var(--paper);
    color: var(--ink); font: inherit; }
  .network-settings select:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .network-settings select:disabled { opacity: 0.65; }
  .key-field {
    padding: 12px;
    border-radius: var(--radius);
    background: var(--paper);
    color: var(--muted);
    font-size: 13px;
  }
  .key-label-row {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .key-trigger {
    width: 100%;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 6px;
    text-align: left;
    background: var(--surface);
  }
  .hint-wrap {
    position: relative;
    display: inline-flex;
  }
  .hint-trigger {
    padding: 0;
    min-width: 44px;
    border: 0;
    background: transparent;
  }
  .hint-trigger span {
    display: inline-grid;
    place-items: center;
    width: 18px;
    height: 18px;
    border: 1px solid currentColor;
    border-radius: 50%;
    font-weight: 700;
  }
  .key-hint {
    visibility: hidden;
    opacity: 0;
    pointer-events: none;
    position: absolute;
    top: 100%;
    left: -100px;
    width: min(340px, 70vw);
    z-index: 50;
    padding: 16px;
    border: 1px solid var(--border);
    border-radius: 12px;
    background: var(--surface);
    color: var(--ink);
    box-shadow: 0 8px 24px #0004;
    font-size: 13px;
    line-height: 1.5;
    display: grid;
    gap: 6px;
  }
  .hint-wrap:hover .key-hint,
  .hint-wrap:focus-within .key-hint {
    visibility: visible;
    opacity: 1;
    pointer-events: auto;
  }
  .hint-wrap.hint-dismissed .key-hint {
    visibility: hidden;
    opacity: 0;
    pointer-events: none;
  }
  .key-options {
    position: fixed;
    inset: auto;
    margin: 0;
    padding: 6px;
    border: 1px solid var(--border);
    border-radius: 12px;
    background: var(--surface);
    color: var(--ink);
    box-shadow: 0 10px 28px #0005;
    max-height: 45vh;
    overflow: auto;
  }
  .key-options button {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    width: 100%;
    min-height: 44px;
    border: 0;
    text-align: left;
  }
  .key-options button:hover:not(:disabled),
  .key-options button:focus-visible {
    background: var(--soft);
  }
  .key-options button[aria-selected='true'] {
    font-weight: 600;
  }

  .llm-panel.organization-connection {
    flex: none;
    width: min(calc(100% - 48px), var(--form-width));
    margin: 24px auto;
    padding: calc(3 * var(--space));
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--surface);
  }
  h2 {
    margin: 0 0 12px;
    font-size: 20px;
  }
  fieldset {
    margin: 0;
    padding: 0;
    border: 0;
    min-width: 0;
  }
  .fields {
    display: grid;
    gap: 16px;
  }
  label {
    display: grid;
    gap: 6px;
    padding: calc(1.5 * var(--space));
    border-radius: var(--radius);
    background: var(--paper);
    color: var(--muted);
    font-size: 13px;
  }
  input {
    width: 100%;
    min-width: 0;
    min-height: 44px;
    padding: 9px 12px;
    border: 0;
    border-radius: var(--radius);
    background: transparent;
    color: var(--ink);
  }
  button {
    min-height: 44px;
    padding: 8px 12px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--surface);
    color: var(--ink);
  }
  .primary {
    background: var(--accent);
    color: var(--surface);
  }
  :is(input, button):focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
  :is(input, button):disabled {
    opacity: 0.65;
  }
  .help,
  .error {
    margin: 10px 0;
    font-size: 13px;
    line-height: 1.5;
    overflow-wrap: anywhere;
  }
  .help {
    color: var(--muted);
  }
  .error {
    color: var(--error);
  }

  .llm-panel.organization-connection {
    width: min(calc(100% - 32px), 760px);
    padding: 24px;
    margin: 16px auto;
    border-radius: 12px;
  }
  .form-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 24px;
  }
  .form-header h2 {
    margin: 0;
    font-size: 24px;
  }
  .subtitle {
    margin: 6px 0 0;
    font-size: 14px;
    color: var(--muted);
  }
  .reload {
    border: 1px solid var(--border);
    border-radius: 7px;
    background: var(--soft);
    color: var(--ink);
    white-space: nowrap;
    padding: 8px 12px;
    font-weight: 500;
  }
  h3 {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 0 0 18px;
    font-size: 17px;
  }
  .step {
    display: inline-grid;
    place-items: center;
    width: 30px;
    height: 30px;
    border-radius: 50%;
    border: 1px solid var(--border);
    background: var(--soft);
    color: var(--ink);
    font-size: 16px;
  }
  .fields {
    gap: 8px;
  }
  label {
    padding: 0;
    background: none;
    color: var(--ink);
    font-size: 13px;
  }
  input {
    border: 1px solid var(--border);
    background: var(--paper);
    border-radius: 7px;
    padding: 10px 12px;
  }
  .key-field {
    display: grid;
    grid-template-columns: max-content max-content;
    gap: 8px;
    align-items: center;
    padding: 8px 0 0;
    background: none;
  }
  .key-label-row {
    display: contents;
  }
  [id$='-key-action-label'] {
    grid-column: 1 / -1;
    order: 1;
    color: var(--ink);
  }
  .key-trigger {
    order: 2;
    width: auto;
    min-width: 130px;
    margin: 0;
    border-radius: 7px;
  }
  .hint-wrap {
    order: 3;
  }
  .key-hint {
    left: 0;
    right: auto;
    width: min(340px, 75vw);
  }
  .key-entry {
    position: relative;
  }
  .key-entry input {
    padding-right: 48px;
  }
  .visibility {
    position: absolute;
    right: 2px;
    top: 1px;
    border: 0;
    background: transparent;
    display: grid;
    place-items: center;
    padding: 0;
    width: 44px;
  }
  .help {
    margin: 0;
    font-size: 12px;
  }
  .connection-actions {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    margin: 16px 0 24px;
  }
  .connection-actions p {
    font-size: 12px;
    color: var(--muted);
  }
  .connection-actions .verified {
    color: var(--ink);
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .success-mark {
    display: inline-grid;
    place-items: center;
    flex: none;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background: #15803d;
    color: #fff;
  }
  .policy-section {
    border-top: 1px solid var(--border);
    padding-top: 20px;
  }
  .empty-policy {
    font-size: 13px;
    color: var(--muted);
    margin: 0 0 20px;
  }
  .form-footer {
    border-top: 1px solid var(--border);
    margin-top: 20px;
    padding-top: 16px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }
  .form-footer p {
    margin: 0;
    color: var(--muted);
    font-size: 12px;
  }
  .primary {
    font-weight: 600;
    border-radius: 7px;
  }
  .primary:disabled {
    background: var(--soft);
    color: var(--muted);
    opacity: 1;
  }
  @media (max-width: 520px) {
    .llm-panel {
      width: calc(100% - 16px);
      padding: 16px;
    }
    .form-header h2 {
      font-size: 20px;
    }
    .connection-actions,
    .form-footer {
      align-items: stretch;
      flex-direction: column;
    }
    .key-trigger {
      min-width: 0;
    }
  }

  .llm-panel.organization-connection {
    border: 0;
    border-radius: 0;
    background: transparent;
    box-shadow: none;
  }
  .key-trigger {
    gap: 12px;
    padding: 8px 12px;
  }
  [id$='-key-action-value'] {
    white-space: nowrap;
  }
  .key-chevron {
    display: block;
    flex: none;
    transition: transform 120ms ease;
  }
  .key-trigger[aria-expanded='true'] .key-chevron {
    transform: rotate(180deg);
  }
  @media (prefers-reduced-motion: reduce) {
    .key-chevron {
      transition: none;
    }
  }
  .default-summary {
    display: block;
    margin-top: 4px;
  }
  .key-apply-hint {
    border-top: 1px solid var(--border);
    padding-top: 8px;
  }
  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip-path: inset(50%);
  }
</style>
