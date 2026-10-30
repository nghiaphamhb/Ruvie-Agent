import {
  getEmbeddingConnection,
  catalogEmbeddingConnection,
  verifyEmbeddingConnection,
  applyEmbeddingConnection,
  EmbeddingApiError,
  type EmbeddingMetadata,
  type EmbeddingDraft,
  type EmbeddingModel,
} from './embedding-api.ts';

/** Each settings session owns its draft and ignores responses from older generations. */
export function createEmbeddingState({
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
  let metadata = $state<EmbeddingMetadata | null>(null),
    baseUrl = $state(''),
    apiKey = $state('');
  let networkMode = $state<'direct' | 'proxy'>('direct'),
    proxyUrl = $state('');
  let keyAction = $state<EmbeddingDraft['key_action']>('clear'),
    catalog = $state<EmbeddingModel[]>([]),
    modelId = $state<string | null>(null);
  let busy = $state(false),
    verified = $state(false),
    catalogReady = $state(false),
    saved = $state(false),
    uncertain = $state(false),
    errorCode = $state<string | null>(null);
  let active = false,
    disposed = false,
    generation = 0;
  let pendingKind: string | null = null;
  function clearSecret() {
    apiKey = '';
    keyAction =
      metadata?.configured && baseUrl.trim().replace(/\/+$/, '') === metadata.base_url
        ? 'keep'
        : 'clear';
  }
  function invalidate(clearCatalog = true) {
    generation++;
    busy = false;
    verified = false;
    saved = false;
    errorCode = null;
    if (clearCatalog) {
      catalog = [];
      catalogReady = false;
    }
  }
  function draft(): EmbeddingDraft {
    return {
      base_url: baseUrl.trim().replace(/\/+$/, ''),
      key_action: keyAction,
      expected_version: metadata?.version ?? 0,
      network: { mode: networkMode, proxy_url: networkMode === 'proxy' ? proxyUrl.trim() : null },
      ...(keyAction === 'replace' ? { api_key: apiKey } : {}),
    };
  }
  function failure(error: unknown, preserveDraft = false) {
    if (!preserveDraft) clearSecret();
    verified = false;
    const safe = error instanceof EmbeddingApiError ? error : null;
    errorCode = safe?.code ?? 'network';
    uncertain = !!safe?.uncertain;
    if (safe?.status === 401) {
      close();
      onexpired();
    } else if (safe?.code === 'admin_required') {
      close();
      onforbidden();
    }
  }
  async function open() {
    if (disposed) return false;
    active = true;
    const current = ++generation;
    busy = true;
    errorCode = null;
    saved = false;
    uncertain = false;
    verified = false;
    catalogReady = false;
    catalog = [];
    try {
      const result = await getEmbeddingConnection();
      if (!active || disposed || current !== generation) return false;
      metadata = result;
      baseUrl = result.base_url ?? '';
      networkMode = result.network.mode;
      proxyUrl = result.network.proxy_url ?? '';
      modelId = result.model_id;
      clearSecret();
      return true;
    } catch (error) {
      if (active && current === generation) failure(error, true);
      return false;
    } finally {
      if (current === generation) busy = false;
    }
  }
  async function operation(kind: 'catalog' | 'probe' | 'apply') {
    if (!active || disposed || busy || !metadata || !baseUrl.trim() ||
        (networkMode === 'proxy' && !proxyUrl.trim())) return false;
    if (kind !== 'catalog' && (!modelId || !catalog.some((m) => m.id === modelId && m.supported)))
      return false;
    if (kind === 'apply' && !verified) return false;
    const input = draft(),
      current = ++generation,
      selected = modelId;
    pendingKind = kind;
    busy = true;
    errorCode = null;
    saved = false;
    try {
      if (kind === 'catalog') {
        const result = await catalogEmbeddingConnection(csrfToken, input);
        if (!active || disposed || current !== generation) return false;
        if (result.version !== metadata.version)
          throw new EmbeddingApiError(409, 'configuration_conflict');
        catalog = result.models;
        catalogReady = true;
        verified = false;
      } else if (kind === 'probe') {
        await verifyEmbeddingConnection(csrfToken, { ...input, model_id: selected! });
        if (!active || disposed || current !== generation) return false;
        verified = true;
      } else {
        const result = await applyEmbeddingConnection(csrfToken, { ...input, model_id: selected! });
        if (!active || disposed || current !== generation) return false;
        if (result.version <= input.expected_version)
          throw new EmbeddingApiError(undefined, 'network', true);
        metadata = result;
        networkMode = result.network.mode;
        proxyUrl = result.network.proxy_url ?? '';
        clearSecret();
        verified = false;
        saved = true;
        uncertain = false;
        onapplied();
      }
      return true;
    } catch (error) {
      if (active && !disposed && current === generation) {
        failure(error);
        if (uncertain) {
          try {
            const result = await getEmbeddingConnection();
            if (active && current === generation) {
              metadata = result; /* An observed version is not proof of our mutation. */
            }
          } catch {
            /* Retain unknown outcome. */
          }
        }
      }
      return false;
    } finally {
      if (current === generation) busy = false;
    }
  }
  function close() {
    active = false;
    invalidate();
    apiKey = '';
    baseUrl = '';
    networkMode = 'direct';
    proxyUrl = '';
    metadata = null;
    modelId = null;
    keyAction = 'clear';
    uncertain = false;
  }
  return {
    get dirty() {
      return (
        !!metadata &&
        (baseUrl.trim().replace(/\/+$/, '') !== (metadata.base_url ?? '') ||
          keyAction === 'replace' ||
          (keyAction === 'clear' && metadata.has_api_key) ||
          modelId !== metadata.model_id ||
          networkMode !== metadata.network.mode ||
          (networkMode === 'proxy' && proxyUrl.trim() !== metadata.network.proxy_url))
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
    get catalogReady() {
      return catalogReady;
    },
    get saved() {
      return saved;
    },
    get uncertain() {
      return uncertain;
    },
    get errorCode() {
      return errorCode;
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
    set keyAction(value: EmbeddingDraft['key_action']) {
      if (value !== keyAction) {
        invalidate();
        keyAction = value;
        if (value !== 'replace') apiKey = '';
      }
    },
    get defaultModelId() {
      return modelId;
    },
    get allowedModelIds() {
      return modelId ? [modelId] : [];
    },
    get models() {
      return [
        ...catalog.map((m) => ({ ...m, available: true })),
        ...(modelId && !catalog.some((m) => m.id === modelId)
          ? [
              {
                id: modelId,
                name: modelId,
                dimension: metadata?.dimension ?? null,
                supported: false,
                reason_code: 'embedding_model_unsupported',
                available: false,
              },
            ]
          : []),
      ];
    },
    get canApply() {
      return verified && !busy && (networkMode === 'direct' || !!proxyUrl.trim()) &&
        catalog.some((m) => m.id === modelId && m.supported);
    },
    get canKeep() {
      return !!metadata?.configured && baseUrl.trim().replace(/\/+$/, '') === metadata.base_url;
    },
    selectModel(id: string) {
      if (!busy) {
        invalidate(false);
        modelId = id;
      }
    },
    suspend() {
      if (busy && metadata) {
        generation++;
        busy = false;
        verified = false;
        if (pendingKind === 'apply') {
          uncertain = true;
          clearSecret();
        }
        pendingKind = null;
      }
    },
    open,
    verify: () => operation('catalog'),
    probe: () => operation('probe'),
    apply: () => operation('apply'),
    close,
    dispose() {
      close();
      disposed = true;
    },
  };
}
