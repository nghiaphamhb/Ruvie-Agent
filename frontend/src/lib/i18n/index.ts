import { createInstance } from 'i18next';
import { writable } from 'svelte/store';
import vi from './locales/vi-VN/translation.json' with { type: 'json' };
import en from './locales/en-US/translation.json' with { type: 'json' };
import ru from './locales/ru-RU/translation.json' with { type: 'json' };
import { isLocale, languages, resolveInitialLocale, LOCALE_STORAGE_KEY, type Locale } from './locale.ts';
import type { MessageKey, UiMessage } from './messages.ts';
export { languages, resolveInitialLocale, LOCALE_STORAGE_KEY };
export type { Locale, MessageKey, UiMessage };

export const translationOptions = {
  supportedLngs: languages.map(language => language.code), fallbackLng: 'en-US',
  ns: 'translation', defaultNS: 'translation', keySeparator: false as const,
  returnEmptyString: false, interpolation: { escapeValue: false }
};
const instance = createInstance();
function snapshot(locale: Locale) {
  const number = (value: number) => new Intl.NumberFormat(locale).format(value);
  const t = (key: MessageKey, params: UiMessage['params'] = {}) => String(instance.t(key, {
    ...params, ...(typeof params.count === 'number' ? { formattedCount: number(params.count) } : {})
  }));
  return { locale, t, number, message: (value: UiMessage | null) => value ? t(value.key, value.params) : '' };
}
const store = writable(snapshot('vi-VN'));
export const i18n = { subscribe: store.subscribe };
/** Port the legacy languageChanged store update; keep the DOM and store in agreement. */
function publish() {
  if (!isLocale(instance.language)) return;
  if (typeof document !== 'undefined') document.documentElement.lang = instance.language;
  store.set(snapshot(instance.language));
}
instance.on('languageChanged', publish);
let initialization: Promise<void> | undefined;
let selection = 0;
/** Initialize bundled resources once before mounting, with no translation network calls. */
export function initI18n(): Promise<void> {
  if (!initialization) {
    let saved: string | null = null;
    if (typeof window !== 'undefined') {
      try { saved = window.localStorage.getItem(LOCALE_STORAGE_KEY); } catch { /* Storage may be blocked. */ }
    }
    const preferred = typeof window !== 'undefined' && typeof navigator !== 'undefined'
      ? navigator.languages?.length ? navigator.languages : [navigator.language] : [];
    initialization = instance.init({ ...translationOptions, lng: resolveInitialLocale(saved, preferred),
      resources: { 'vi-VN': { translation: vi }, 'en-US': { translation: en }, 'ru-RU': { translation: ru } }
    }).then(() => { publish(); });
  }
  return initialization;
}
/** A valid manual choice changes only UI state; the latest choice wins initialization races. */
export async function setLocale(locale: string): Promise<void> {
  if (!isLocale(locale)) return;
  const current = ++selection;
  await initI18n();
  if (current !== selection) return;
  await instance.changeLanguage(locale);
  if (typeof window !== 'undefined') {
    try { window.localStorage.setItem(LOCALE_STORAGE_KEY, locale); } catch { /* Keep the in-session choice. */ }
  }
}
/** Keep binary size thresholds and precision; localize only the displayed number. */
export function formatFileSize(bytes: number, locale: Locale): string {
  const divisor = bytes < 1024 ? 1 : bytes < 1024 * 1024 ? 1024 : 1024 * 1024;
  const precision = divisor === 1 ? 0 : 1;
  const number = new Intl.NumberFormat(locale, { minimumFractionDigits: precision, maximumFractionDigits: precision }).format(bytes / divisor);
  return `${number} ${divisor === 1 ? 'B' : divisor === 1024 ? 'KiB' : 'MiB'}`;
}
