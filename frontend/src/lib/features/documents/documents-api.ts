import { isCitation, type Citation } from '../chat/chat-api.ts';
import { message, type UiMessage } from '../../i18n/messages.ts';
export type ProjectSummary = { id: string; code: string; name: string };
export type RevisionStatus = {
  revision_id: string;
  status: 'pending' | 'running' | 'ready' | 'failed';
  error_code: string | null;
};
export type UploadDocumentInput = {
  project_id: string;
  title: string;
  software: string;
  software_version: string;
  file: File;
};
export type UploadDocumentResult = {
  document_id: string;
  revision_id: string;
  job_id: string;
  status: 'pending';
};

/** Carry a safe message key; translate only when the UI renders it. */
export class DocumentsApiError extends Error {
  readonly status?: number;
  readonly uiMessage: UiMessage;

  constructor(status?: number, embeddingUnavailable = false) {
    super('Document request failed');
    this.uiMessage = message(
      status === 401
        ? 'common.errors.session'
        : embeddingUnavailable
          ? 'chat.errors.embedding_unavailable'
          : 'upload.errors.request',
    );
    this.name = 'DocumentsApiError';
    this.status = status;
  }
}

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, { ...init, credentials: 'same-origin' });
  } catch {
    throw new DocumentsApiError();
  }
  if (!response.ok) throw new DocumentsApiError(response.status);
  return response.json() as Promise<T>;
}

export async function listProjects(): Promise<ProjectSummary[]> {
  const result = await json<{ items: ProjectSummary[] }>('/projects');
  return result.items;
}

export function uploadDocument(
  csrfToken: string,
  input: UploadDocumentInput,
): Promise<UploadDocumentResult> {
  const body = new FormData();
  body.set('project_id', input.project_id);
  body.set('title', input.title);
  body.set('software', input.software);
  body.set('software_version', input.software_version);
  body.set('file', input.file);
  return json('/documents/upload', {
    method: 'POST',
    headers: { 'X-CSRF-Token': csrfToken },
    body,
  });
}

export function getRevisionStatus(revisionId: string): Promise<RevisionStatus> {
  return json(`/documents/revisions/${encodeURIComponent(revisionId)}/status`);
}

export type RetrievalResult = {
  chunk_id: string;
  document_id: string;
  text: string;
  citation: Citation;
};
/** POST readable-passage search; identity and document access remain server-side. */
export async function retrieveDocuments(
  query: string,
  signal?: AbortSignal,
): Promise<RetrievalResult[]> {
  if (!query.trim()) throw new DocumentsApiError(422);
  let response: Response;
  try {
    response = await fetch('/documents/retrieve', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: query.trim(), limit: 10 }),
      signal,
    });
  } catch {
    throw new DocumentsApiError();
  }
  if (!response.ok) {
    let embeddingUnavailable = false;
    try {
      embeddingUnavailable =
        response.status === 503 &&
        (await response.json())?.detail?.code === 'embedding_unavailable';
    } catch {
      /* Ignore unsafe upstream detail. */
    }
    throw new DocumentsApiError(response.status, embeddingUnavailable);
  }
  let value: unknown;
  try {
    value = await response.json();
  } catch {
    throw new DocumentsApiError();
  }
  if (
    !Array.isArray(value) ||
    !value.every(
      (hit) =>
        hit &&
        typeof hit === 'object' &&
        typeof hit.chunk_id === 'string' &&
        typeof hit.document_id === 'string' &&
        typeof hit.text === 'string' &&
        isCitation(hit.citation) &&
        hit.chunk_id === hit.citation.chunk_id &&
        hit.document_id === hit.citation.document_id,
    )
  )
    throw new DocumentsApiError();
  return value;
}
