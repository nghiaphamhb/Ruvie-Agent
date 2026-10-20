# Ruvie Agent current architecture

Verified against the active source tree on 2026-10-17. This document describes
implemented behavior. Read it before changing cross-feature flows, authorization,
persistence or module ownership; keep it aligned with the code. Repository rules
remain in [AGENTS.md](../AGENTS.md). Setup and startup commands are in
[README](../README.md).

## Runtime components

| Component | Implementation and responsibility |
| --- | --- |
| Browser frontend | Svelte 5, Vite and TypeScript in `frontend/`; authentication, projects, upload/status, passage search, model settings and streaming chat |
| HTTP API | FastAPI in `backend/ruvie/`; authenticates requests, calls services and serializes HTTP/SSE results |
| Ingestion worker | Separate `ruvie.worker_cli` process; polls PostgreSQL jobs, reads private uploads, extracts/chunks text and requests embeddings |
| Database | PostgreSQL with pgvector; system of record for identity, permissions, document metadata/content, vectors, jobs, LLM settings and audit |
| Private blob storage | API and worker currently share `LocalBlobStore` at repository-root `data/uploads/`; original upload bytes stay outside public web assets |
| Embedding provider | Server-configured provider used by the worker for chunks and by the API for queries |
| LLM provider | OpenAI-compatible model catalog/chat endpoints, resolved from account settings or server fallback through the guarded adapter |

During development, Vite proxies `/auth`, `/projects`, `/documents`, `/llm`,
`/models` and `/chat` to the API at `127.0.0.1:8000`. The API and worker run on
the host; the documented Docker deployment runs PostgreSQL only. There is no
separate vector database, Redis queue or external agent orchestrator in this flow.

`main.py` loads settings and owns the API's database engine, session factory,
embedding HTTP client, query embedder and blob store lifecycle. The worker creates
its own resources with the same database, embedding profile and storage root.
`/health` and `/ready` return a static OK response; neither probes the database.

## Backend module ownership

All paths in the following table are under `backend/ruvie/`.

| Module | Responsibility |
| --- | --- |
| `main.py`, `dependencies.py` | Resource lifecycle, router registration, session/resource dependencies and trusted identity resolution |
| `api/`, `contracts/` | Request validation, HTTP security checks, service calls, structured response/event contracts and HTTP/SSE serialization |
| `services/auth.py` | Password authentication, registration and session management |
| `services/projects.py`, `services/access.py` | Project membership and the shared database-backed readable-document predicate |
| `services/documents/` | Upload authorization, immutable revisions, ingestion lifecycle, safe status and stable citation metadata |
| `services/retrieval.py` | Authorized retrieval, SQL chunk search, READY-revision filtering, cosine ranking, citations and retrieval audit |
| `services/chat.py` | Model resolution, authorized context preparation, prompt assembly and structured streaming events |
| `services/llm.py` | Account connection/model persistence, catalog validation and server fallback resolution |
| `services/audit.py` | Access-decision audit records |
| `adapters/` | Embedding/LLM transport and private blob-storage implementations |
| `models/`, `database.py` | SQLAlchemy data model and database/session setup |
| `config.py` | Repository-root `.env` loading and server-side configuration validation |

Chat calls `AuthorizedRetrievalService`; it does not query chunk storage directly.
`ChatService` returns `ChatStreamEvent` values, and `api/chat.py` encodes SSE.
The direct query-embedder call in `api/documents.py` is an existing boundary
exception: resolve it when changing that retrieval flow, rather than copying it
into new routes. Do not add layers or move unrelated modules just for convention.

## Data model and durable state

The current domain has 12 tables, in addition to Alembic bookkeeping:

| Tables | Stored state |
| --- | --- |
| `users`, `auth_sessions` | Account identity, password hashes and session records |
| `projects`, `roles`, `memberships`, `access_grants` | Project membership/roles and direct document permissions |
| `documents`, `document_revisions` | Document metadata, original revision identity/hash, private blob reference and ingestion state |
| `ingestion_jobs` | Worker job state, attempts, heartbeat and safe failure codes |
| `document_chunks` | Revision-linked immutable text, offsets, software metadata and 1024-dimensional embedding vectors |
| `user_llm_settings` | Per-account provider connection, API key and model selection |
| `audit_events` | Append-only access decisions protected against update/delete |

Persistent schema changes use `backend/migrations/` and Alembic. Never alter an
applied migration. The current embedding profile is `baai/bge-m3`, dimension
`1024`, cosine distance; configuration and the pgvector schema must agree.

Revision content and chunk content are immutable. A new upload/revision does not
overwrite old content or citations; ingestion status may change. The upload
service supports adding a revision to an existing document, but the current
multipart HTTP upload creates a new document and does not accept `document_id`.
Retrieval can return readable READY revisions; it does not promise latest-only
results.

## Identity and authorization

The browser signs in or registers through `/auth`; the backend establishes a
Secure HttpOnly cookie session and supplies the existing CSRF contract. Account
emails are normalized to lowercase and constrained in PostgreSQL. Registration
creates no project membership, document grant or administrator privilege.

Document access is default-deny. `DocumentAccessService` permits a document only
when either the user's database-backed project membership has a role allowed by
that document, or the user has a direct read grant that has not expired. Project
membership alone does not bypass the document's allowed roles.

Apply this predicate in SQL before selecting/exposing passages, building LLM
context or serializing document content. Identity and scope come from the server;
client-provided project/document IDs identify resources to check and cannot grant
access. Status tracking separately permits the uploader or a document reader.
API responses and citations never expose private blob URIs.

## Main data flows

### Upload and ingestion

1. The authenticated multipart upload supplies a project, title, software/version
   metadata and one PDF or UTF-8 text file, up to 25 MiB. The API checks browser
   origin/CSRF; the upload service checks project access and request validity.
2. The service writes private bytes and creates document/revision/job records.
   The API returns safe IDs and pending status with HTTP 202.
3. The separate worker claims eligible PostgreSQL jobs with row locking and
   `skip_locked`, maintains a heartbeat and recovers/retries eligible stale or
   failed work. It extracts text, chunks it and requests embeddings.
4. Chunks and embeddings are stored in PostgreSQL. Only a successfully indexed
   revision becomes READY and can participate in retrieval; partial chunks stay
   hidden while ingestion runs. Failures produce safe status/error codes.
5. The browser polls revision status every two seconds for up to five minutes,
   then offers manual refresh. Browser timeout or closing the upload dialog does
   not cancel the server job.

### Passage search

1. Search submits `query` and `limit` to `POST /documents/retrieve`; it does not
   submit an authorization scope.
2. The query embedder creates the vector. `AuthorizedRetrievalService` filters
   by readable documents and READY revisions before cosine ranking and limiting.
3. It builds revision/chunk citations, records the access audit and returns only
   authorized passage text and safe metadata.

### Chat

1. `POST /chat` accepts a message and optional model ID. Provider URLs/keys and
   client-selected ACL scopes are forbidden by the request contract.
2. `ChatService.prepare` validates the model against the effective provider
   catalog, embeds the question and obtains authorized retrieval hits. Database
   sessions close before streaming.
3. The service assembles a prompt from those hits, treating document text as
   evidence rather than instructions, and streams from the provider. With no
   readable hits, it may answer from general knowledge without claiming sources.
4. The API serializes `delta`, `citations`, `completed` and `error` SSE events.
   Citations are sent after successful answer generation and retain the original
   revision/chunk identity. The browser shows sources on completion.

Each question, including Retry, is independent. Prior browser turns are not sent
as conversation context. Stop aborts browser consumption and retains partial
text; it does not guarantee cancellation of provider-side computation.

### Provider settings and transport

Users can save a personal connection and selected model through dedicated settings
endpoints. The backend stores them per account and validates provider/model
availability. It never repopulates API keys into the browser or localStorage.
Without a personal connection, optional server `LLM_*` settings supply a fallback.
A failed personal connection does not silently switch to that fallback.

The guarded LLM adapter rejects redirects and prohibited destinations, verifies
TLS and pins DNS results. HTTP/private endpoints require an exact origin in the
server's `LLM_ALLOWED_LOCAL_ORIGINS`. Optional `LLM_PROXY_URL` configures explicit
SOCKS5 egress for model discovery and chat, with no direct fallback on failure.
Independent `EMBEDDING_PROXY_URL` configures SOCKS5 egress for query and ingestion
embeddings in the API and worker. Empty means direct; ambient system/environment
proxy settings are not used by these shared embedding clients. Neither proxy
setting silently falls back to direct. Restart the backend and worker to apply
changes. These policies are server-owned.

## Frontend organization and state

`App.svelte` owns auth/session/toasts and mounts a workspace keyed by account and
CSRF token. `pages/WorkspacePage.svelte` composes layout and feature owners; it
handles navigation, focus and the page lifecycle. Layouts do not import pages.

| Location under `frontend/src/` | Responsibility |
| --- | --- |
| `lib/layout/` | `WorkspaceShell`, sidebar/account navigation and responsive shell |
| `lib/features/auth/` | Login/registration forms, validation, auth client and toast presentation |
| `lib/features/chat/` | Draft/turn/stream ownership, composer, Markdown, Retry/Stop and citations |
| `lib/features/documents/` | Projects, upload/status, passage search and their API/state owner |
| `lib/features/llm/` | Catalog/connection/model API and shared LLM state owner |
| `lib/features/settings/` | Settings dialog composition |
| `lib/shared/` | Reusable components without feature-specific business rules |
| `lib/i18n/` | Locale resolution, translation utilities and vi-VN/en-US/ru-RU catalogs |
| `lib/assets/`, `styles/` | Local brand/auth assets, shared theme and workspace styles |

Chat, document and LLM owners live for one authenticated workspace. Navigation,
Settings and language changes preserve drafts, selected files and running work.
Logout or a current protected request's 401 disposes owners, invalidates stale
responses and clears account state. Chat history/drafts exist only in page memory;
saved provider settings/model selection return from PostgreSQL after reload.

Chat Markdown uses pinned `marked` tokens and Svelte escaping; raw HTML and model
images/embeds remain text, and links allow only absolute HTTP/HTTPS URLs. The
browser persists only an explicit locale choice under `ruvie.ui.locale`; UI
language does not change question content, API scope or the LLM's answer language.

## Implemented scope and remaining gaps

The runtime supports registration/login, projects, authorized upload/ingestion,
passage search, provider/model settings and cited streaming answers. Notes,
Workspace library tabs, folder/history persistence and unsupported chat Controls
remain placeholders. There is no document preview/download API or persistent chat
history, admin settings UI, ticket integration, automatic repair/tool execution,
or role/software-version personalization of answers.

`references/` is read-only legacy source, not an active runtime dependency. Every
directory named `archive` is excluded from active context. Broader proposals in
specs must not be mistaken for implemented components. Existing diagrams are
linked from [Visual specifications](../specs/visual/README.md); compare them with
the active source when changing a flow.

### Workspace theme preference

Settings > Display > Background offers System, Light and Dark. The settings
feature owns this browser-only preference in `ruvie.ui.theme.<encoded-user-id>`;
it is separate for each signed-in account and is not sent to the backend.
The default System mode follows `prefers-color-scheme` changes without persisting
the detected color. Explicit choices apply immediately, survive reload, and do
not remount chat or trigger business requests. Storage failures retain a usable
in-session choice. Workspace disposal removes media/storage listeners. Light
and dark workspace tokens also style Settings and model popovers; auth retains
its existing styling. The legacy `chat/Settings/General.svelte::applyTheme` is a
behavior reference only; active code uses Svelte state and scoped tokens, not
legacy theme classes or runtime imports.
