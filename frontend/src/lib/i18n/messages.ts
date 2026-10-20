import type english from './locales/en-US/translation.json';
type BaseKey<Key extends string> = Key extends `${infer Base}_${'one' | 'few' | 'many' | 'other'}`
  ? Base
  : Key;
export type MessageKey = BaseKey<keyof typeof english>;
export type UiMessage = {
  key: MessageKey;
  params?: Record<string, string | number> & { count?: number };
};
/** Store a key, never a translated string, so existing notices can change language. */
export function message(key: MessageKey, params?: UiMessage['params']): UiMessage {
  return params ? { key, params } : { key };
}
export function llmErrorMessage(status?: number): UiMessage {
  const keys: Record<number, MessageKey> = {
    401: 'common.errors.session',
    403: 'llm.errors.csrf',
    422: 'llm.errors.invalid',
    502: 'llm.errors.providerUnavailable',
    503: 'llm.errors.settings',
  };
  return message(keys[status ?? 0] ?? 'common.errors.network');
}
