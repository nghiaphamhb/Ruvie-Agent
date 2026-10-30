/** Organization-only HTTP client. Response/error projection never preserves secrets. */
export type OrganizationMetadata = {
  configured: boolean;
  base_url: string | null;
  has_api_key: boolean;
  allowed_model_ids: string[];
  default_model_id: string | null;
  version: number;
  updated_at: string | null;
};
export type OrganizationDraft = {
  base_url: string;
  key_action: 'keep' | 'replace' | 'clear';
  api_key?: string;
  expected_version: number;
};
export type OrganizationPolicy = { allowed_model_ids: string[]; default_model_id: string };
export type VerifiedCatalog = { models: { id: string; name: string }[]; version: number };
const safeCodes = new Set([
  'authentication_required',
  'admin_required',
  'csrf_invalid',
  'origin_invalid',
  'configuration_conflict',
  'invalid_llm_request',
  'llm_provider_unavailable',
  'llm_not_configured',
  'llm_settings_unavailable',
]);
export class OrganizationLlmApiError extends Error {
  status?: number;
  code: string;
  uncertain: boolean;
  constructor(status?: number, code = 'network', uncertain = false) {
    super('Organization LLM request failed');
    this.status = status;
    this.code = safeCodes.has(code) ? code : 'network';
    this.uncertain = uncertain;
  }
}
async function request(path: string, method = 'GET', csrfToken = '', body?: object) {
  let response: Response;
  try {
    response = await fetch(path, {
      method,
      credentials: 'same-origin',
      cache: 'no-store',
      headers:
        method === 'GET' ? {} : { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
  } catch {
    throw new OrganizationLlmApiError(undefined, 'network', method === 'PUT');
  }
  if (!response.ok) {
    let code = 'network';
    try {
      code = (await response.json())?.detail?.code;
    } catch {
      /* Keep errors safe even for a proxy HTML error. */
    }
    throw new OrganizationLlmApiError(
      response.status,
      code,
      method === 'PUT' && response.status >= 500,
    );
  }
  try {
    return await response.json();
  } catch {
    throw new OrganizationLlmApiError(undefined, 'network', method === 'PUT');
  }
}
function metadata(data: OrganizationMetadata): OrganizationMetadata {
  if (
    typeof data?.configured !== 'boolean' ||
    !Number.isInteger(data.version) ||
    data.version < 0 ||
    !Array.isArray(data.allowed_model_ids) ||
    data.allowed_model_ids.some((id) => typeof id !== 'string') ||
    typeof data.has_api_key !== 'boolean' ||
    (data.base_url !== null && typeof data.base_url !== 'string') ||
    (data.default_model_id !== null && typeof data.default_model_id !== 'string')
  )
    throw new OrganizationLlmApiError();
  return {
    configured: data.configured,
    base_url: data.base_url,
    has_api_key: data.has_api_key,
    allowed_model_ids: [...data.allowed_model_ids],
    default_model_id: data.default_model_id,
    version: data.version,
    updated_at: typeof data.updated_at === 'string' ? data.updated_at : null,
  };
}
export async function getOrganizationConnection(): Promise<OrganizationMetadata> {
  return metadata(await request('/admin/llm/connection'));
}
export async function verifyOrganizationConnection(
  csrfToken: string,
  draft: OrganizationDraft,
): Promise<VerifiedCatalog> {
  const data = await request('/admin/llm/connection/verify', 'POST', csrfToken, draft);
  if (
    !Number.isInteger(data?.version) ||
    !Array.isArray(data.models) ||
    data.models.some(
      (m: { id: string; name: string }) => typeof m?.id !== 'string' || typeof m?.name !== 'string',
    )
  )
    throw new OrganizationLlmApiError();
  return {
    models: data.models.map((m: { id: string; name: string }) => ({ id: m.id, name: m.name })),
    version: data.version,
  };
}
export async function applyOrganizationConnection(
  csrfToken: string,
  draft: OrganizationDraft & OrganizationPolicy,
): Promise<OrganizationMetadata> {
  const data = await request('/admin/llm/connection', 'PUT', csrfToken, draft);
  try {
    return metadata(data);
  } catch {
    throw new OrganizationLlmApiError(undefined, 'network', true);
  }
}

export async function probeOrganizationModel(
  csrfToken: string,
  draft: OrganizationDraft & { model_id: string },
) {
  const data = await request('/admin/llm/connection/probe', 'POST', csrfToken, draft);
  if (
    data?.success !== true ||
    data.model_id !== draft.model_id ||
    data.version !== draft.expected_version
  )
    throw new OrganizationLlmApiError();
  return true;
}
