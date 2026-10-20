import {writable} from 'svelte/store';

export type ThemePreference = 'system' | 'light' | 'dark';
export type ResolvedTheme = 'light' | 'dark';
const isPreference = (value: unknown): value is ThemePreference =>
  value === 'system' || value === 'light' || value === 'dark';

/** Own one account's browser-only choice; OS changes never overwrite that choice. */
export function createThemeState(userId: string) {
  const browser = typeof window === 'undefined' ? null : window;
  const key = `ruvie.ui.theme.${encodeURIComponent(userId)}`;
  const media = browser?.matchMedia('(prefers-color-scheme: dark)');
  let preference: ThemePreference = 'system';
  let systemDark = media?.matches ?? false;
  let disposed = false;
  try {
    const saved = browser?.localStorage.getItem(key);
    if (isPreference(saved)) preference = saved;
  } catch { /* Storage can be blocked; keep the in-session choice usable. */ }
  const snapshot = () => ({preference, resolved: (preference === 'system' ? systemDark ? 'dark' : 'light' : preference) as ResolvedTheme});
  const store = writable(snapshot());
  function select(value: unknown) {
    if (disposed || !isPreference(value)) return;
    preference = value;
    store.set(snapshot());
    try { browser?.localStorage.setItem(key, preference); } catch { /* The current session still changes theme. */ }
  }
  function systemChanged(event: MediaQueryListEvent) {
    systemDark = event.matches;
    if (preference === 'system') store.set(snapshot());
  }
  function storageChanged(event: StorageEvent) {
    if (event.key !== key && event.key !== null) return;
    preference = isPreference(event.newValue) ? event.newValue : 'system';
    store.set(snapshot());
  }
  media?.addEventListener('change', systemChanged);
  browser?.addEventListener('storage', storageChanged);
  return {
    subscribe: store.subscribe, select,
    dispose() {
      disposed = true;
      media?.removeEventListener('change', systemChanged);
      browser?.removeEventListener('storage', storageChanged);
    }
  };
}
