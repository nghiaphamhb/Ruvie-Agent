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

/** Map only known server codes; never render raw validation/provider detail. */
export function organizationLlmErrorMessage(code: string): UiMessage {
  const keys: Record<string, MessageKey> = {
    configuration_conflict: 'llm.org.conflict',
    invalid_network_configuration: 'ai.network.invalid',
    proxy_unavailable: 'ai.network.unavailable',
    network_configuration_pending: 'ai.network.pending',
    authentication_required: 'common.errors.session',
    admin_required: 'admin.errors.admin_required',
    csrf_invalid: 'llm.errors.csrf',
    origin_invalid: 'llm.errors.csrf',
    invalid_llm_request: 'llm.errors.invalid',
    invalid_embedding_request: 'llm.errors.invalid',
    embedding_model_unsupported: 'embedding.unsupported',
    embedding_dimension_unsupported: 'embedding.unsupported',
    embedding_provider_unavailable: 'embedding.error',
    embedding_authentication_failed: 'embedding.authError',
    embedding_rate_limited: 'embedding.rateLimit',
    embedding_timeout: 'embedding.timeout',
    embedding_catalog_unavailable: 'embedding.catalogError',
    embedding_settings_unavailable: 'embedding.error',
    embedding_not_configured: 'llm.org.unconfigured',
    llm_provider_unavailable: 'llm.errors.providerUnavailable',
    llm_settings_unavailable: 'llm.errors.settings',
    llm_not_configured: 'llm.org.unconfigured',
  };
  return message(keys[code] ?? 'common.errors.network');
}
