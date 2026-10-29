import { message } from '../../i18n/messages.ts';
import { LlmApiError, getLlmConnection, getModels, selectLlmModel } from './llm-api.ts';
import type { LlmConnection, ModelsResult } from './llm-api.ts';

/** One confirmed model catalog and connection owner for the authenticated workspace. */
export function createLlmState({
  csrfToken,
  onexpired,
  isLocked,
}: {
  csrfToken: string;
  onexpired: () => void;
  isLocked: () => boolean;
}) {
  let catalog = $state<ModelsResult | null>(null),
    connection = $state<LlmConnection | null>(null);
  let loading = $state(false),
    modelBusy = $state(false),
    error = $state<ReturnType<typeof message> | null>(null);
  let modelError = $state<ReturnType<typeof message> | null>(null),
    notice = $state<ReturnType<typeof message> | null>(null);
  let sequence = 0,
    disposed = false,
    initial: Promise<void> | null = null;
  async function metadata(current: number) {
    const result = await getLlmConnection();
    if (disposed || current !== sequence) return;
    connection = result;
    if (result.configured) {
      const models = await getModels();
      if (!disposed && current === sequence) catalog = models;
    } else catalog = null;
  }
  async function run(action: (current: number) => Promise<void>, force = false) {
    if (disposed || loading || modelBusy || (!force && isLocked())) return;
    const current = ++sequence;
    loading = true;
    error = null;
    notice = null;
    try {
      await action(current);
    } catch (failure) {
      if (disposed || current !== sequence) return;
      if (failure instanceof LlmApiError && failure.status === 401) {
        onexpired();
        return;
      }
      error = failure instanceof LlmApiError ? failure.uiMessage : message('llm.errors.read');
    } finally {
      if (!disposed && current === sequence) loading = false;
    }
  }
  function initialize() {
    if (!initial) initial = run(metadata, true);
    return initial;
  }
  async function reloadModels() {
    if (disposed || isLocked() || loading || modelBusy) return;
    const current = ++sequence;
    modelBusy = true;
    catalog = null;
    modelError = null;
    try {
      const result = await getModels();
      if (!disposed && current === sequence) catalog = result;
    } catch (failure) {
      if (disposed || current !== sequence) return;
      if (failure instanceof LlmApiError && failure.status === 401) {
        onexpired();
        return;
      }
      modelError =
        failure instanceof LlmApiError ? failure.uiMessage : message('model.errors.load');
    } finally {
      if (!disposed && current === sequence) modelBusy = false;
    }
  }
  async function chooseModel(id: string) {
    if (
      disposed ||
      isLocked() ||
      loading ||
      modelBusy ||
      !catalog ||
      !catalog.models.some((m) => m.id === id)
    )
      return false;
    if (id === catalog.selected_model_id) return true;
    const current = ++sequence;
    modelBusy = true;
    modelError = null;
    try {
      const result = await selectLlmModel(csrfToken, id);
      if (disposed || current !== sequence) return false;
      catalog = {
        ...catalog,
        selected_model_id: result.selected_model_id,
        selection_required: false,
      };
      return true;
    } catch (failure) {
      if (disposed || current !== sequence) return false;
      if (failure instanceof LlmApiError && failure.status === 401) {
        onexpired();
        return false;
      }
      modelError =
        failure instanceof LlmApiError ? failure.uiMessage : message('model.errors.save');
      return false;
    } finally {
      if (!disposed && current === sequence) modelBusy = false;
    }
  }
  function dispose() {
    disposed = true;
    ++sequence;
    catalog = null;
    connection = null;
  }
  return {
    get catalog() {
      return catalog;
    },
    get connection() {
      return connection;
    },
    get loading() {
      return loading;
    },
    get modelBusy() {
      return modelBusy;
    },
    get error() {
      return error;
    },
    get modelError() {
      return modelError;
    },
    get notice() {
      return notice;
    },
    get modelReady() {
      return Boolean(
        catalog &&
        !catalog.selection_required &&
        catalog.models.some((m) => m.id === catalog?.selected_model_id),
      );
    },
    initialize,
    reloadModels,
    chooseModel,
    reloadConnection: () => run(metadata),
    dispose,
  };
}
