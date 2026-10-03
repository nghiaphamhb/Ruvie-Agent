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

export class DocumentsApiError extends Error {
  readonly status?: number;

  constructor(status?: number) {
    super(status === 401 ? 'Phiên đăng nhập đã hết hạn.' : 'Không thể hoàn tất yêu cầu tài liệu.');
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

export function uploadDocument(csrfToken: string, input: UploadDocumentInput): Promise<UploadDocumentResult> {
  const body = new FormData();
  body.set('project_id', input.project_id);
  body.set('title', input.title);
  body.set('software', input.software);
  body.set('software_version', input.software_version);
  body.set('file', input.file);
  return json('/documents/upload', {
    method: 'POST',
    headers: { 'X-CSRF-Token': csrfToken },
    body
  });
}

export function getRevisionStatus(revisionId: string): Promise<RevisionStatus> {
  return json(`/documents/revisions/${encodeURIComponent(revisionId)}/status`);
}
