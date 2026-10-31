export type NetworkConfig = { mode: 'direct' | 'proxy'; proxy_url: string | null };
export function safeNetwork(value: unknown): value is NetworkConfig {
  if (!value || typeof value !== 'object') return false;
  const network = value as Partial<NetworkConfig>;
  return (
    (network.mode === 'direct' && network.proxy_url === null) ||
    (network.mode === 'proxy' &&
      typeof network.proxy_url === 'string' &&
      network.proxy_url.startsWith('socks5://'))
  );
}
/** Independent embedding HTTP contracts; never retain raw response errors or secrets. */
export type EmbeddingMetadata = {
  configured: boolean;
  base_url: string | null;
  has_api_key: boolean;
  network: NetworkConfig;
  model_id: string | null;
  dimension: number | null;
  distance_metric: string | null;
  version: number;
  updated_at: string | null;
};
export type EmbeddingDraft = {
  base_url: string;
  key_action: 'keep' | 'replace' | 'clear';
  api_key?: string;
  expected_version: number;
  network: NetworkConfig;
};
export type EmbeddingModel = {
  id: string;
  name: string;
  dimension: number | null;
  supported: boolean;
  reason_code: string | null;
};
const codes = new Set([
  'authentication_required',
  'admin_required',
  'csrf_invalid',
  'origin_invalid',
  'configuration_conflict',
  'invalid_network_configuration',
  'proxy_unavailable',
  'network_configuration_pending',
  'invalid_embedding_request',
  'embedding_model_unsupported',
  'embedding_dimension_unsupported',
  'embedding_provider_unavailable',
  'embedding_authentication_failed',
  'embedding_rate_limited',
  'embedding_timeout',
  'embedding_catalog_unavailable',
  'embedding_settings_unavailable',
  'embedding_not_configured',
]);
export class EmbeddingApiError extends Error {
  status?: number;
  code: string;
  uncertain: boolean;
  constructor(status?: number, code = 'network', uncertain = false) {
    super('Embedding request failed');
    this.status = status;
    this.code = codes.has(code) ? code : 'network';
    this.uncertain = uncertain;
  }
}
async function request(path = '', method = 'GET', csrfToken = '', body?: object) {
  let response: Response;
  try {
    response = await fetch('/admin/embedding/connection' + path, {
      method,
      credentials: 'same-origin',
      cache: 'no-store',
      headers:
        method === 'GET' ? {} : { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
  } catch {
    throw new EmbeddingApiError(undefined, 'network', method === 'PUT');
  }
  if (!response.ok) {
    let code = 'network';
    try {
      code = (await response.json())?.detail?.code;
    } catch {
      /* Safe fallback. */
    }
    throw new EmbeddingApiError(response.status, code, method === 'PUT' && response.status >= 500);
  }
  try {
    return await response.json();
  } catch {
    throw new EmbeddingApiError(undefined, 'network', method === 'PUT');
  }
}
function metadata(data: EmbeddingMetadata): EmbeddingMetadata {
  if (
    typeof data?.configured !== 'boolean' ||
    !safeNetwork(data.network) ||
    typeof data.has_api_key !== 'boolean' ||
    !Number.isInteger(data.version) ||
    data.version < 0 ||
    (data.base_url !== null && typeof data.base_url !== 'string') ||
    (data.model_id !== null && typeof data.model_id !== 'string') ||
    (data.dimension !== null && !Number.isInteger(data.dimension)) ||
    (data.distance_metric !== null && typeof data.distance_metric !== 'string')
  )
    throw new EmbeddingApiError();
  return {
    configured: data.configured,
    base_url: data.base_url,
    has_api_key: data.has_api_key,
    network: { ...data.network },
    model_id: data.model_id,
    dimension: data.dimension,
    distance_metric: data.distance_metric,
    version: data.version,
    updated_at: typeof data.updated_at === 'string' ? data.updated_at : null,
  };
}
export async function getEmbeddingConnection() {
  return metadata(await request());
}
export async function catalogEmbeddingConnection(
  csrf: string,
  draft: EmbeddingDraft,
): Promise<{ models: EmbeddingModel[]; version: number }> {
  const data = await request('/catalog', 'POST', csrf, draft);
  if (
    !Number.isInteger(data?.version) ||
    !Array.isArray(data.models) ||
    data.models.some(
      (m: EmbeddingModel) =>
        typeof m?.id !== 'string' ||
        typeof m.name !== 'string' ||
        typeof m.supported !== 'boolean' ||
        (m.dimension !== null && !Number.isInteger(m.dimension)),
    )
  )
    throw new EmbeddingApiError();
  return {
    version: data.version,
    models: data.models.map((m: EmbeddingModel) => ({
      id: m.id,
      name: m.name,
      dimension: m.dimension,
      supported: m.supported,
      reason_code: codes.has(m.reason_code ?? '') ? m.reason_code : null,
    })),
  };
}
export async function verifyEmbeddingConnection(
  csrf: string,
  draft: EmbeddingDraft & { model_id: string },
) {
  const data = await request('/verify', 'POST', csrf, draft);
  if (
    data?.model_id !== draft.model_id ||
    data.dimension !== 1024 ||
    data.distance_metric !== 'cosine' ||
    data.compatible !== true ||
    data.version !== draft.expected_version
  )
    throw new EmbeddingApiError();
  return { model_id: data.model_id, version: data.version };
}
export async function applyEmbeddingConnection(
  csrf: string,
  draft: EmbeddingDraft & { model_id: string },
) {
  const data = await request('', 'PUT', csrf, draft);
  try {
    return metadata(data);
  } catch {
    throw new EmbeddingApiError(undefined, 'network', true);
  }
}
