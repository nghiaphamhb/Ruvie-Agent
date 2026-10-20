import { toast } from 'svelte-sonner';
import { i18n } from '../../i18n/index.ts';
import type { MessageKey } from '../../i18n/messages.ts';
let releaseFeedback = () => {};

/** Keep the current UI-only notice localized; release on replacement or dismissal. */
function feedback(kind: 'success' | 'error', key: MessageKey) {
  releaseFeedback();
  let unsubscribe = () => {};
  const finish = () => unsubscribe();
  unsubscribe = i18n.subscribe((locale) => {
    toast[kind](locale.t(key), {
      id: 'chat-copy',
      duration: 3500,
      onDismiss: finish,
      onAutoClose: finish,
    });
  });
  releaseFeedback = unsubscribe;
}
/** Copy exact source text; permission errors get safe feedback in the existing host. */
export async function copyText(text: string) {
  try {
    await navigator.clipboard.writeText(text);
    feedback('success', 'chat.copied');
  } catch {
    feedback('error', 'chat.copyFailed');
  }
}
