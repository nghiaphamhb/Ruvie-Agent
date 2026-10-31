import {
  getOrganizationConnection,
  probeOrganizationModel,
  verifyOrganizationConnection,
  applyOrganizationConnection,
  OrganizationLlmApiError,
  type OrganizationMetadata,
  type OrganizationDraft,
} from './organization-llm-api.ts';

/** Draft and request lifecycle for one mounted administrator settings panel. */
export function createOrganizationLlmState({
  csrfToken,
  onexpired,
  onforbidden,
  onapplied,
}: {
  csrfToken: string;
  onexpired: () => void;
  onforbidden: () => void;
  onapplied: () => void;
}) {
  let metadata = $state<OrganizationMetadata | null>(null);
  let baseUrl = $state(''),
    apiKey = $state('');
  let networkMode = $state<'direct' | 'proxy'>('direct'),
    proxyUrl = $state('');
  let keyAction = $state<OrganizationDraft['key_action']>('clear');
  let catalog = $state<{ id: string; name: string }[]>([]),
    allowed = $state<string[]>([]);
  let defaultId = $state<string | null>(null);
  let verified = $state(false),
    busy = $state(false),
    uncertain = $state(false);
  let errorCode = $state<string | null>(null),
    saved = $state(false);
  let probeSuccess = $state(false);
  let applying = false;
  let active = false,
    disposed = false,
    generation = 0;
  function invalidate() {
    probeSuccess = false;
    verified = false;
    catalog = [];
    saved = false;
    generation++;
    busy = false;
  }
  function clearSecret() {
    apiKey = '';
    keyAction =
      metadata?.configured && baseUrl.trim().replace(/\/+$/, '') === metadata.base_url
        ? 'keep'
        : 'clear';
  }
  function failure(error: unknown, preserveDraft = false) {
    if (!preserveDraft) clearSecret();
    probeSuccess = false;
    verified = false;
    catalog = [];
    const safe = error instanceof OrganizationLlmApiError ? error : null;
    errorCode = safe?.code ?? 'network';
    uncertain = Boolean(safe?.uncertain);
    if (safe?.status === 401) {
      close();
      onexpired();
    } else if (safe?.code === 'admin_required') {
      close();
      onforbidden();
    }
  }
  function draft(): OrganizationDraft {
    return {
      base_url: baseUrl.trim().replace(/\/+$/, ''),
      key_action: keyAction,
      expected_version: metadata?.version ?? 0,
      network: { mode: networkMode, proxy_url: networkMode === 'proxy' ? proxyUrl.trim() : null },
      ...(keyAction === 'replace' ? { api_key: apiKey } : {}),
    };
  }
  async function open() {
    if (disposed) return;
    active = true;
    const current = ++generation;
    busy = true;
    errorCode = null;
    saved = false;
    clearSecret();
    probeSuccess = false;
    verified = false;
    catalog = [];
    try {
      const result = await getOrganizationConnection();
      if (!active || disposed || current !== generation) return;
      if (metadata && result.version < metadata.version) return;
      metadata = result;
      baseUrl = result.base_url ?? '';
      networkMode = result.network.mode;
      proxyUrl = result.network.proxy_url ?? '';
      allowed = [...result.allowed_model_ids];
      defaultId = result.default_model_id;
      uncertain = false;
      clearSecret();
      return true;
    } catch (error) {
      if (active && !disposed && current === generation) {
        failure(error, true);
        return false;
      }
    } finally {
      if (current === generation) busy = false;
    }
  }
  async function verify() {
    if (
      !active ||
      disposed ||
      busy ||
      !metadata ||
      !baseUrl.trim() ||
      (networkMode === 'proxy' && !proxyUrl.trim())
    )
      return false;
    const input = draft(),
      current = ++generation;
    busy = true;
    errorCode = null;
    saved = false;
    verified = false;
    try {
      const result = await verifyOrganizationConnection(csrfToken, input);
      if (!active || disposed || current !== generation) return false;
      if (result.version !== metadata.version) {
        errorCode = 'configuration_conflict';
        clearSecret();
        return false;
      }
      catalog = result.models;
      verified = true;
      return true;
    } catch (error) {
      if (active && !disposed && current === generation) failure(error);
      return false;
    } finally {
      if (current === generation) busy = false;
    }
  }
  async function apply() {
    if (
      !active ||
      disposed ||
      busy ||
      !verified ||
      !metadata ||
      (networkMode === 'proxy' && !proxyUrl.trim()) ||
      !defaultId ||
      !allowed.length ||
      !allowed.includes(defaultId) ||
      allowed.some((id) => !catalog.some((m) => m.id === id))
    )
      return false;
    applying = true;
    const input = { ...draft(), allowed_model_ids: [...allowed], default_model_id: defaultId };
    const current = ++generation;
    busy = true;
    errorCode = null;
    saved = false;
    try {
      const result = await applyOrganizationConnection(csrfToken, input);
      if (!active || disposed || current !== generation) return false;
      if (result.version <= input.expected_version) {
        throw new OrganizationLlmApiError(undefined, 'network', true);
      }
      metadata = result;
      baseUrl = result.base_url ?? '';
      networkMode = result.network.mode;
      proxyUrl = result.network.proxy_url ?? '';
      allowed = [...result.allowed_model_ids];
      defaultId = result.default_model_id;
      clearSecret();
      verified = false;
      saved = true;
      uncertain = false;
      onapplied();
      return true;
    } catch (error) {
      if (active && !disposed && current === generation) {
        failure(error);
        if (uncertain) {
          try {
            const result = await getOrganizationConnection();
            if (active && !disposed && current === generation) metadata = result;
          } catch {
            /* Keep the unknown result; never retry the mutation. */
          }
        }
      }
      return false;
    } finally {
      if (current === generation) {
        busy = false;
        applying = false;
      }
    }
  }
  function close() {
    applying = false;
    active = false;
    generation++;
    busy = false;
    apiKey = '';
    baseUrl = '';
    networkMode = 'direct';
    proxyUrl = '';
    keyAction = 'clear';
    catalog = [];
    allowed = [];
    defaultId = null;
    verified = false;
    metadata = null;
    errorCode = null;
    uncertain = false;
    saved = false;
  }
  return {
    get dirty() {
      return (
        !!metadata &&
        (baseUrl.trim().replace(/\/+$/, '') !== (metadata.base_url ?? '') ||
          keyAction === 'replace' ||
          (keyAction === 'clear' && metadata.has_api_key) ||
          defaultId !== metadata.default_model_id ||
          networkMode !== metadata.network.mode ||
          (networkMode === 'proxy' && proxyUrl.trim() !== metadata.network.proxy_url) ||
          [...allowed].sort().join('\n') !== [...metadata.allowed_model_ids].sort().join('\n'))
      );
    },
    get metadata() {
      return metadata;
    },
    get busy() {
      return busy;
    },
    get verified() {
      return verified;
    },
    get uncertain() {
      return uncertain;
    },
    get errorCode() {
      return errorCode;
    },
    get saved() {
      return saved;
    },
    get baseUrl() {
      return baseUrl;
    },
    set baseUrl(value: string) {
      if (value !== baseUrl) {
        invalidate();
        baseUrl = value;
        apiKey = '';
        keyAction = 'clear';
      }
    },
    get networkMode() {
      return networkMode;
    },
    set networkMode(value: 'direct' | 'proxy') {
      if (value !== networkMode) {
        invalidate();
        networkMode = value;
      }
    },
    get proxyUrl() {
      return proxyUrl;
    },
    set proxyUrl(value: string) {
      if (value !== proxyUrl) {
        invalidate();
        proxyUrl = value;
      }
    },
    get apiKey() {
      return apiKey;
    },
    set apiKey(value: string) {
      if (value !== apiKey) {
        invalidate();
        apiKey = value;
        keyAction = 'replace';
      }
    },
    get keyAction() {
      return keyAction;
    },
    set keyAction(value: OrganizationDraft['key_action']) {
      if (value !== keyAction) {
        invalidate();
        keyAction = value;
        if (value !== 'replace') apiKey = '';
      }
    },
    get allowedModelIds() {
      return allowed;
    },
    get defaultModelId() {
      return defaultId;
    },
    get models() {
      return [
        ...catalog.map((m) => ({ ...m, available: true })),
        ...allowed
          .filter((id) => !catalog.some((m) => m.id === id))
          .map((id) => ({ id, name: id, available: false })),
      ];
    },
    get canApply() {
      return (
        verified &&
        !busy &&
        (networkMode === 'direct' || !!proxyUrl.trim()) &&
        !!defaultId &&
        allowed.includes(defaultId) &&
        allowed.length > 0 &&
        allowed.every((id) => catalog.some((m) => m.id === id))
      );
    },
    get canKeep() {
      return !!metadata?.configured && baseUrl.trim().replace(/\/+$/, '') === metadata.base_url;
    },
    setPolicy(next: { allowedModelIds: string[]; defaultModelId: string | null }) {
      if (!busy && verified) {
        allowed = next.allowedModelIds.filter((id, index, ids) => ids.indexOf(id) === index);
        defaultId = next.defaultModelId;
        probeSuccess = false;
        saved = false;
      }
    },
    get probeSuccess() {
      return probeSuccess;
    },
    async probe() {
      if (!active || disposed || busy || !verified || !defaultId) return false;
      const current = ++generation;
      busy = true;
      errorCode = null;
      probeSuccess = false;
      try {
        await probeOrganizationModel(csrfToken, { ...draft(), model_id: defaultId });
        if (!active || disposed || current !== generation) return false;
        probeSuccess = true;
        return true;
      } catch (error) {
        if (active && current === generation) failure(error);
        return false;
      } finally {
        if (current === generation) busy = false;
      }
    },
    suspend() {
      if (busy && metadata) {
        generation++;
        busy = false;
        verified = false;
        if (applying) {
          uncertain = true;
          clearSecret();
        }
        applying = false;
      }
    },
    open,
    verify,
    apply,
    close,
    dispose() {
      close();
      disposed = true;
    },
  };
}
