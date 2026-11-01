import {
  historyRequest,
  HistoryError,
  type Conversation,
  type HistoryPage,
} from './conversation-api.ts';
import { message } from '../../i18n/messages.ts';
import { ChatApiError, streamChat } from './chat-api.ts';
import type { ChatTurn } from './chat-turn.ts';
import type { ModelsResult } from '../llm/llm-api.ts';

/** One workspace owns these turns and requests; disposal prevents account leakage. */
export function createChatState(options: {
  csrfToken?: string;
  onaccepted?: (id: string) => void;
  onexpired: () => void;
  getCatalog: () => ModelsResult | null;
  isLocked: () => boolean;
  onModelUnavailable: () => void;
  onMissingModel?: () => void;
}) {
  let draft = $state(''),
    turns = $state<ChatTurn[]>([]),
    busy = $state(false);
  let sequence = 0,
    nextId = 1,
    disposed = false,
    request: AbortController | null = null;
  let activeTurn: ChatTurn | null = null;
  let stopOwner = -1;
  let stopRequested = false,
    stopWaiter: (() => void) | null = null,
    stopPromise: Promise<void> | null = null;
  let conversationId = $state<string | null>(null),
    conversations = $state<Conversation[]>([]),
    loading = $state(false),
    listLoading = $state(false),
    historyError = $state(false),
    listError = $state(false),
    olderCursor = $state<string | null>(null),
    listCursor = $state<string | null>(null);
  let listRequest: AbortController | null = null;
  let readSequence = 0,
    listSequence = 0,
    readRequest: AbortController | null = null;
  const csrf = options.csrfToken ?? '';
  function failure(error: unknown) {
    if (error instanceof HistoryError && error.status === 401) options.onexpired();
    else historyError = true;
  }
  async function loadList(more = false) {
    if (disposed) return;
    const current = ++listSequence;
    listRequest?.abort();
    listRequest = new AbortController();
    listLoading = true;
    listError = false;
    try {
      const page = await historyRequest<{ items: Conversation[]; next_cursor: string | null }>(
        `/conversations${more && listCursor ? '?cursor=' + encodeURIComponent(listCursor) : ''}`,
        csrf,
        'GET',
        undefined,
        listRequest.signal,
      );
      if (disposed || current !== listSequence) return;
      const previous = more
        ? conversations.filter((item) => !page.items.some((incoming) => incoming.id === item.id))
        : [];
      conversations = [...previous, ...page.items];
      listCursor = page.next_cursor;
    } catch (error) {
      if (!disposed && current === listSequence) {
        listError = true;
        if (error instanceof HistoryError && error.status === 401) options.onexpired();
      }
    } finally {
      if (!disposed && current === listSequence) listLoading = false;
    }
  }
  async function open(id: string, more = false) {
    if (disposed) return;
    const current = ++readSequence;
    readRequest?.abort();
    readRequest = new AbortController();
    if (!more) {
      ++sequence;
      request?.abort();
      request = null;
      turns = [];
      draft = '';
      busy = false;
      activeTurn = null;
      conversationId = id;
    }
    loading = true;
    historyError = false;
    try {
      const page = await historyRequest<HistoryPage>(
        `/conversations/${id}${more && olderCursor ? '?before=' + encodeURIComponent(olderCursor) : ''}`,
        csrf,
        'GET',
        undefined,
        readRequest.signal,
      );
      if (disposed || current !== readSequence) return;
      const saved = page.turns.map(
        (turn) =>
          ({
            id: nextId++,
            serverId: turn.id,
            createdAt: turn.created_at,
            attemptId: turn.attempt_id,
            question: turn.question,
            answer: turn.content_unavailable ? '' : turn.answer,
            citations: turn.content_unavailable ? [] : turn.citations,
            modelId: turn.model_id,
            contentUnavailable: turn.content_unavailable,
            status: turn.status === 'generating' ? 'loading' : (turn.status ?? 'interrupted'),
            error:
              turn.status === 'error'
                ? new ChatApiError(
                    [
                      'embedding_unavailable',
                      'provider_unavailable',
                      'generation_failed',
                      'history_unavailable',
                    ].includes(turn.error_code ?? '')
                      ? (turn.error_code as
                          | 'embedding_unavailable'
                          | 'provider_unavailable'
                          | 'generation_failed'
                          | 'history_unavailable')
                      : 'generation_failed',
                  ).uiMessage
                : null,
          }) as ChatTurn,
      );
      turns = more
        ? [
            ...saved.filter(
              (item) => !turns.some((existing) => existing.serverId === item.serverId),
            ),
            ...turns,
          ]
        : saved;
      olderCursor = page.next_cursor;
      activeTurn = turns.find((turn) => turn.status === 'loading') ?? null;
      busy = activeTurn !== null;
    } catch (error) {
      if (disposed || current !== readSequence) return;
      if (error instanceof HistoryError && error.status === 404) {
        reset();
        options.onaccepted?.('');
      }
      failure(error);
    } finally {
      if (!disposed && current === readSequence) loading = false;
    }
  }
  async function rename(id: string, title: string, version: number) {
    if (disposed) return false;
    try {
      await historyRequest(`/conversations/${id}`, csrf, 'PATCH', {
        title,
        expected_version: version,
      });
      if (!disposed) await loadList();
      return true;
    } catch (error) {
      if (!disposed) {
        failure(error);
        await loadList();
      }
      return false;
    }
  }
  async function remove(id: string) {
    if (disposed) return false;
    try {
      await historyRequest(`/conversations/${id}`, csrf, 'DELETE');
      if (disposed) return false;
      conversations = conversations.filter((item) => item.id !== id);
      if (conversationId === id) {
        reset();
        options.onaccepted?.('');
      }
      return true;
    } catch (error) {
      if (!disposed) failure(error);
      return false;
    }
  }

  async function send(turn: ChatTurn, modelId: string) {
    const current = ++sequence;
    const controller = new AbortController();
    request = controller;
    activeTurn = turn;
    busy = true;
    turn.answer = '';
    turn.citations = [];
    turn.error = null;
    turn.status = 'loading';
    turn.modelId = modelId;
    const owns = () => !disposed && current === sequence;
    let invalidModel = false;
    try {
      await streamChat(
        turn.question,
        (event) => {
          if (!owns()) return;
          if (event.type === 'accepted') {
            conversationId = event.conversation_id;
            turn.serverId = event.turn_id;
            turn.attemptId = event.attempt_id;
            options.onaccepted?.(conversationId);
            void loadList();
            if (stopRequested) {
              const waiting = stopWaiter;
              stopWaiter = null;
              stopRequested = false;
              stopOwner = -1;
              void stop().finally(() => {
                waiting?.();
                stopPromise = null;
              });
            }
          } else if (event.type === 'delta') {
            turn.answer += event.text;
            turn.status = 'streaming';
          } else if (event.type === 'citations') turn.citations = event.citations;
          else turn.status = 'completed';
        },
        controller.signal,
        modelId,
        {
          requestId: (turn.requestId ??= crypto.randomUUID()),
          conversationId,
          turnId: turn.serverId,
          csrfToken: csrf,
        },
      );
    } catch (error) {
      if (!owns()) return;
      if (error instanceof ChatApiError && error.code === 'auth_required') {
        options.onexpired();
        return;
      }
      if (error instanceof HistoryError) {
        const id = error.resources.conversation_id ?? conversationId;
        if (id) {
          options.onaccepted?.(id);
          await open(id);
        } else failure(error);
        return;
      }
      if (
        error instanceof ChatApiError &&
        ['interrupted', 'network_error', 'history_unavailable'].includes(error.code)
      ) {
        const id = conversationId;
        if (id) await open(id);
        if (disposed || conversationId !== id) return;
        historyError = true;
        if (conversationId) return;
      }
      invalidModel = error instanceof ChatApiError && error.code === 'model_unavailable';
      turn.status = 'error';
      turn.citations = [];
      turn.error =
        error instanceof ChatApiError ? error.uiMessage : message('chat.errors.complete');
    } finally {
      if (owns()) {
        request = null;
        activeTurn = null;
        busy = false;
        if (invalidModel) options.onModelUnavailable();
      }
      if (stopRequested && stopOwner === current) {
        stopRequested = false;
        stopWaiter?.();
        stopWaiter = null;
        stopPromise = null;
        stopOwner = -1;
      }
    }
  }
  async function submit(event?: SubmitEvent) {
    event?.preventDefault();
    const catalog = options.getCatalog(),
      question = draft.trim();
    if (disposed || busy || loading || options.isLocked() || !question) return;
    if (!catalog || catalog.selection_required) {
      options.onMissingModel?.();
      return;
    }
    const modelId = catalog.selected_model_id;
    if (!modelId || !catalog.models.some((model) => model.id === modelId)) {
      options.onMissingModel?.();
      return;
    }
    turns.push({
      id: nextId++,
      question,
      modelId,
      answer: '',
      citations: [],
      status: 'loading',
      error: null,
    });
    draft = '';
    await send(turns[turns.length - 1], modelId);
  }
  /** Stop browser output, retain partial text and invalidate even late completed events. */
  function cancelLocal() {
    if (!busy) return;
    ++sequence;
    request?.abort();
    request = null;
    busy = false;
    if (activeTurn) {
      activeTurn.status = 'stopped';
      activeTurn.citations = [];
      activeTurn.error = null;
    }
    activeTurn = null;
  }
  async function stop() {
    if (!busy) return;
    const current = sequence;
    const id = conversationId,
      turn = activeTurn;
    if (id && turn?.serverId && turn.attemptId) {
      try {
        await historyRequest(`/conversations/${id}/turns/${turn.serverId}/stop`, csrf, 'POST', {
          attempt_id: turn.attemptId,
        });
      } catch (error) {
        if (!disposed && current === sequence && id === conversationId) failure(error);
        return;
      }
      if (disposed || current !== sequence || id !== conversationId) return;
      cancelLocal();
      await open(id);
    } else {
      stopRequested = true;
      stopOwner = current;
      stopPromise ??= new Promise<void>((resolve) => {
        stopWaiter = resolve;
      });
      return stopPromise;
    }
  }
  async function retry(id: number, replacementModelId?: string) {
    if (disposed || busy || options.isLocked()) return;
    const turn = turns.find((item) => item.id === id),
      catalog = options.getCatalog();
    if (!turn || !catalog || catalog.selection_required) return;
    const modelId = replacementModelId ?? turn.modelId;
    if (!modelId || !catalog.models.some((model) => model.id === modelId)) {
      turn.error = message('chat.retryModel');
      return;
    }
    // A replacement is explicit and must match the backend-confirmed selection.
    if (replacementModelId && replacementModelId !== catalog.selected_model_id) return;
    if (turn.serverId) turn.requestId = crypto.randomUUID();
    await send(turn, modelId);
  }
  function reset() {
    stopRequested = false;
    stopWaiter?.();
    stopWaiter = null;
    stopPromise = null;
    cancelLocal();
    ++readSequence;
    readRequest?.abort();
    loading = false;
    olderCursor = null;
    conversationId = null;
    historyError = false;
    ++sequence;
    turns = [];
    draft = '';
  }
  function dispose() {
    disposed = true;
    ++listSequence;
    listRequest?.abort();
    conversations = [];
    listLoading = false;
    listError = false;
    listCursor = null;
    reset();
  }
  return {
    get conversationId() {
      return conversationId;
    },
    get conversations() {
      return conversations;
    },
    get loading() {
      return loading;
    },
    get listLoading() {
      return listLoading;
    },
    get historyError() {
      return historyError;
    },
    get listError() {
      return listError;
    },
    get olderCursor() {
      return olderCursor;
    },
    get listCursor() {
      return listCursor;
    },
    open,
    loadList,
    rename,
    remove,
    get draft() {
      return draft;
    },
    set draft(value: string) {
      draft = value;
    },
    get turns() {
      return turns;
    },
    get busy() {
      return busy;
    },
    submit,
    stop,
    retry,
    reset,
    dispose,
  };
}
