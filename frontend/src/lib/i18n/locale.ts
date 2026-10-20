import languages from './locales/languages.json' with { type: 'json' };
export type Locale = 'vi-VN' | 'en-US' | 'ru-RU';
export { languages };
export const LOCALE_STORAGE_KEY = 'ruvie.ui.locale';
export function isLocale(value: unknown): value is Locale {
  return typeof value === 'string' && languages.some((language) => language.code === value);
}
/** Prefer an explicit stored choice, then each valid browser tag in its original order. */
export function resolveInitialLocale(saved: unknown, preferred: readonly string[] = []): Locale {
  if (isLocale(saved)) return saved;
  for (const tag of preferred) {
    try {
      const normalized = Intl.getCanonicalLocales(tag)[0];
      const exact = languages.find(
        (language) => language.code.toLowerCase() === normalized.toLowerCase(),
      );
      const match =
        exact ??
        languages.find((language) => language.code.split('-')[0] === normalized.split('-')[0]);
      if (match) return match.code as Locale;
    } catch {
      /* Invalid browser tags cannot select an arbitrary resource. */
    }
  }
  return 'vi-VN'; // fallback
}
