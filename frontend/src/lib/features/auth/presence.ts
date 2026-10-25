import { AuthApiError, sendPresence } from './auth-api.ts';

/** One workspace owns one heartbeat loop. Other tabs may share its server session lease. */
export function startPresence(csrfToken: string, onexpired: () => void) {
  let timer: ReturnType<typeof setTimeout>;
  let controller: AbortController | null = null;
  let disposed = false;
  let expired = false;
  function schedule() {
    clearTimeout(timer);
    timer = setTimeout(() => void heartbeat(), document.hidden ? 60000 : 30000);
  }
  async function heartbeat() {
    if (disposed || expired || controller) return;
    clearTimeout(timer);
    const request = new AbortController();
    controller = request;
    const timeout = setTimeout(() => request.abort(), 10000);
    try {
      await sendPresence(csrfToken, request.signal);
    } catch (error) {
      if (!disposed && error instanceof AuthApiError && error.status === 401) {
        expired = true;
        onexpired();
      }
      // Network and server failures retry without inventing an offline state or discarding drafts.
    } finally {
      clearTimeout(timeout);
      controller = null;
      if (!disposed && !expired) schedule();
    }
  }
  function visibilityChanged() {
    if (disposed || expired) return;
    clearTimeout(timer);
    if (!document.hidden) void heartbeat();
    else if (!controller) schedule();
  }
  const online = () => void heartbeat();
  document.addEventListener('visibilitychange', visibilityChanged);
  window.addEventListener('online', online);
  void heartbeat();
  return {
    dispose() {
      disposed = true;
      clearTimeout(timer);
      controller?.abort();
      document.removeEventListener('visibilitychange', visibilityChanged);
      window.removeEventListener('online', online);
    },
  };
}
