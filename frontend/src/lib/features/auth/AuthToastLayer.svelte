<script module lang="ts">
  import type { UiMessage } from '../../i18n/messages.ts';
  export type AuthNotice = {
    id: number;
    type: 'success' | 'error';
    message: UiMessage;
    retry?: boolean;
  };
</script>

<script lang="ts">
  import { Toaster, toast } from 'svelte-sonner';
  import { i18n } from '../../i18n/index.ts';
  let {
    notice,
    ondismiss,
    onretry,
  }: {
    notice: AuthNotice | null;
    ondismiss: (id: number) => void;
    onretry: () => void;
  } = $props();

  // One stable toast ID replaces repeated responses. UiMessage keeps an open toast localized.
  $effect(() => {
    const current = notice;
    if (!current) {
      toast.dismiss('auth-response');
      return;
    }
    toast[current.type]($i18n.message(current.message), {
      id: 'auth-response',
      duration: 5000,
      onDismiss: () => ondismiss(current.id),
      onAutoClose: () => ondismiss(current.id),
      action: current.retry ? { label: $i18n.t('common.retry'), onClick: onretry } : undefined,
    });
  });
</script>

<!-- Ported from references/src/routes/+layout.svelte: Toaster, richColors, top-right, closeButton. -->
<Toaster
  theme="light"
  richColors
  position="top-right"
  closeButton
  offset={{ top: '76px', right: '24px' }}
  containerAriaLabel={$i18n.t('notifications.label')}
  closeButtonAriaLabel={$i18n.t('notifications.close')}
  style="--width:356px;"
  toastOptions={{ classes: { closeButton: 'auth-toast-close', toast: 'auth-response-toast' } }}
/>

<style>
  :global([data-sonner-toast].auth-response-toast) {
    font-family: var(--font-family);
    border-radius: 14px;
  }
  :global([data-sonner-toast] .auth-toast-close) {
    background: rgba(255, 255, 255, 0.8);
    color: #6b7280;
    border-color: #e5e7eb;
  }
  :global([data-sonner-toast] .auth-toast-close:hover) {
    background: #f9fafb;
    color: #374151;
  }
  :global([data-sonner-toast] button:focus-visible) {
    outline: 2px solid #073b65;
    outline-offset: 3px;
  }
</style>
