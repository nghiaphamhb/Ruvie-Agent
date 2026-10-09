<script lang="ts">
  import { i18n } from '../i18n/index.ts';
  let { draft, disabled, oninput, onsubmit }: {
    draft: string; disabled: boolean; oninput: (value: string) => void;
    onsubmit: (event: SubmitEvent) => void;
  } = $props();
  let compositionEndedAt = 0;
  /** Enter submits once; Shift+Enter and IME confirmation keep editing. */
  function handleInputKeydown(event: KeyboardEvent) {
    if (event.key !== 'Enter' || event.shiftKey || event.isComposing || event.timeStamp - compositionEndedAt < 40) return;
    event.preventDefault();
    (event.currentTarget as HTMLTextAreaElement).form?.requestSubmit();
  }
</script>
<!-- Round arrow-up send control ported from chat/MessageInput.svelte. -->
<div class="composer-area">
  <form class="composer" onsubmit={onsubmit}>
    <label for="question">{$i18n.t('chat.question')}</label>
    <div class="composer-input">
      <textarea
        id="question"
        rows="2"
        placeholder={$i18n.t('chat.placeholder')}
        value={draft} oninput={(event) => oninput(event.currentTarget.value)}
        onkeydown={handleInputKeydown}
        oncompositionend={(event) => (compositionEndedAt = event.timeStamp)}
      ></textarea>
      <button type="submit" disabled={disabled || !draft.trim()} aria-label={$i18n.t('chat.send')} title={$i18n.t('chat.send')}>
        <svg viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path d="M8 14a.75.75 0 0 1-.75-.75V4.56L4.03 7.78a.75.75 0 0 1-1.06-1.06l4.5-4.5a.75.75 0 0 1 1.06 0l4.5 4.5a.75.75 0 0 1-1.06 1.06L8.75 4.56v8.69A.75.75 0 0 1 8 14Z" /></svg>
      </button>
    </div>
  </form>
  <p class="composer-hint">{$i18n.t('chat.hint')}</p>
</div>

<style>
  .composer-area { flex: none; padding: calc(2 * var(--space)) calc(3 * var(--space)); background: var(--surface); }
  .composer, .composer-hint { width: min(100%, var(--content-width)); margin-left: auto; margin-right: auto; }
  .composer label { display: block; margin: 0 0 8px 4px; color: var(--muted); font-size: 12px; font-weight: 600; }
  .composer-input { display: flex; align-items: flex-end; gap: 10px; padding: 11px 11px 11px 16px; border: 1px solid var(--border); border-radius: var(--radius); background: var(--surface); box-shadow: 0 10px 28px #24454a0c; }
  .composer-input:focus-within { border-color: var(--accent); box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 15%, transparent); }
  .composer textarea { flex: 1; min-width: 0; min-height: 48px; max-height: 180px; padding: 9px 0 0; resize: vertical; border: 0; outline: 0; background: transparent; color: var(--ink); font-size: 15px; line-height: 1.5; }
  .composer textarea::placeholder { color: var(--muted); }
  .composer button { flex: none; width: 44px; height: 44px; display: grid; place-items: center; border: 0; border-radius: var(--radius); background: var(--accent); color: white; transition: background .15s ease, transform .15s ease; }
  .composer button:hover:not(:disabled) { background: var(--accent-hover); transform: translateY(-1px); }
  .composer button:disabled { background: var(--border); }
  .composer button svg { width: 19px; height: 19px; }
  .composer-hint { margin-top: 9px; margin-bottom: 0; text-align: center; color: var(--muted); font-size: 12px; line-height: 1.5; }
</style>
