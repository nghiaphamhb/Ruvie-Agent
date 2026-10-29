# Ruvie Agent architecture

This document separates behavior implemented in the active application from the broader target design. The first section describes current code; the second is aspirational and must not be read as implemented functionality.

## 1. Current implemented architecture

Updated against the active source tree for F012 on 2026-10-22. Keep this section aligned with active code. Repository rules remain in [AGENTS.md](../AGENTS.md). Setup and startup commands are in [README](../README.md).
### Runtime components

| Component | Implementation and responsibility |
| --- | --- |
| Browser frontend | Svelte 5, Vite and TypeScript in `frontend/`; authentication, projects, upload/status, passage search, model settings and streaming chat |
| HTTP API | FastAPI in `backend/ruvie/`; authenticates requests, calls services and serializes HTTP/SSE results |
| Ingestion worker | Separate `ruvie.worker_cli` process; polls PostgreSQL jobs, reads private uploads, extracts/chunks text and requests embeddings |
| Database | PostgreSQL with pgvector; system of record for identity, permissions, document metadata/content, vectors, jobs, LLM settings and audit |
| Private blob storage | API and worker currently share `LocalBlobStore` at repository-root `data/uploads/`; original upload bytes stay outside public web assets |
| Embedding provider | Server-configured provider used by the worker for chunks and by the API for queries |
| LLM provider | OpenAI-compatible model catalog/chat endpoints, resolved from account settings or server fallback through the guarded adapter |

During development, Vite proxies `/auth`, `/admin`, `/projects`, `/documents`, `/llm`,
`/models` and `/chat` to the API at `127.0.0.1:8000`. The API and worker run on
the host; the documented Docker deployment runs PostgreSQL only. There is no
separate vector database, Redis queue or external agent orchestrator in this flow.

`main.py` loads settings and owns the API's database engine, session factory,
embedding HTTP client, query embedder and blob store lifecycle. The worker creates
its own resources with the same database, embedding profile and storage root.
`/health` and `/ready` return a static OK response; neither probes the database.

### Backend module ownership

All paths in the following table are under `backend/ruvie/`.

| Module | Responsibility |
| --- | --- |
| `main.py`, `dependencies.py` | Resource lifecycle, router registration, session/resource dependencies and trusted identity resolution |
| `api/`, `contracts/` | Request validation, HTTP security checks, service calls, structured response/event contracts and HTTP/SSE serialization |
| `services/auth.py` | Password authentication, registration and session management |
| `services/admin.py` | Revalidate active administrator identity, create recipient accounts and exact-email lookup |
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

### Data model and durable state

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

### Identity and authorization

The browser signs in or bootstraps the first administrator through `/auth`; the backend establishes a
Secure HttpOnly cookie session and supplies the existing CSRF contract. Account
emails are normalized to lowercase and constrained in PostgreSQL. Bootstrap is
allowed only with zero users, including inactive users. A transaction-scoped
PostgreSQL advisory lock serializes bootstrap before the emptiness check. The
transaction creates an active administrator, session and audit together; the
cookie is set after commit. Any existing user closes public registration.

`POST /auth/login` verifies the password before reporting a disabled account.
Correct credentials for a disabled account return 403 `account_disabled` without
creating a session or setting a cookie. Incorrect credentials retain the generic
401 response. The frontend displays a localized disabled-account message only for
that specific 403 code; revoked sessions still receive 401.

`users.system_role` is `user` or `admin`, separate from project roles. Migration
defaults existing accounts to `user`. `POST /admin/users` requires an active admin,
Origin and CSRF; the service reloads and locks the actor before creating an active
recipient and audit in one transaction. The selected role belongs to the recipient,
not the caller. The response contains safe metadata, no recipient session or cookie.
`GET /admin/users?email=...` is an admin-only exact-email lookup returning zero or
one summary, including inactive accounts. Errors expose safe codes and allowlisted
field errors; admin responses forbid caching. Neither creation flow adds memberships
or grants. Losing all active administrators does not reopen bootstrap; recovery
is a separate, unimplemented operation.

`PATCH /admin/users/{id}/activity` accepts a strict desired account status and
requires an active administrator, Origin and CSRF. The account service uses the
same PostgreSQL transaction advisory lock as account updates, then reloads and
locks the actor and target. It prevents self-deactivation and loss of the last
active administrator. Deactivation removes all target sessions and records an
`account.deactivate` audit event in the same transaction. Reactivation records
`account.activate` and requires a new login; it does not restore old sessions.
Existing memberships, grants and account data are retained. Already authenticated
requests or streams are not cancelled by this operation. The admin directory
shows account status separately from presence and confirms both actions.

Document access is default-deny. `DocumentAccessService` permits a document only
when either the user's database-backed project membership has a role allowed by
that document, or the user has a direct read grant that has not expired. Project
membership alone does not bypass the document's allowed roles.

Apply this predicate in SQL before selecting/exposing passages, building LLM
context or serializing document content. Identity and scope come from the server;
client-provided project/document IDs identify resources to check and cannot grant
access. Status tracking separately permits the uploader or a document reader.
API responses and citations never expose private blob URIs.

### Main data flows

#### Upload and ingestion

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

#### Passage search

1. Search submits `query` and `limit` to `POST /documents/retrieve`; it does not
   submit an authorization scope.
2. The query embedder creates the vector. `AuthorizedRetrievalService` filters
   by readable documents and READY revisions before cosine ranking and limiting.
3. It builds revision/chunk citations, records the access audit and returns only
   authorized passage text and safe metadata.

#### Chat

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

#### Provider settings and transport

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

### Frontend organization and state

`App.svelte` owns auth/session/toasts and mounts a workspace keyed by account and
CSRF token. `pages/WorkspacePage.svelte` composes layout and feature owners; it
handles navigation, focus and the page lifecycle. Layouts do not import pages.

| Location under `frontend/src/` | Responsibility |
| --- | --- |
| `lib/layout/` | `WorkspaceShell`, desktop sidebar/account navigation and shell |
| `lib/features/auth/` | Login/registration forms, validation, auth client and toast presentation |
| `lib/features/admin/` | Account form, create/lookup client, safe metadata and request lifecycle |
| `lib/features/chat/` | Draft/turn/stream ownership, composer, Markdown, Retry/Stop and citations |
| `lib/features/documents/` | Projects, upload/status, passage search and their API/state owner |
| `lib/features/llm/` | Catalog/connection/model API and shared LLM state owner |
| `lib/features/settings/` | Personal Appearance/Account tabs, password form validation/lifecycle, and administrator LLM settings panel |
| `lib/shared/` | Reusable components without feature-specific business rules |
| `lib/i18n/` | Locale resolution, translation utilities and vi-VN/en-US/ru-RU catalogs |
| `lib/assets/`, `styles/` | Local brand/auth assets, shared theme and workspace styles |

Chat, document and LLM owners live for one authenticated workspace. Navigation,
Settings and language changes preserve drafts, selected files and running work.
Logout or a current protected request's 401 disposes owners, invalidates stale
responses and clears account state. Chat history/drafts exist only in page memory;
saved provider settings/model selection return from PostgreSQL after reload.

Personal Settings includes an Account tab for both user and admin. The
`ChangePasswordForm` mounts only while Settings and Account are active. It clears
passwords and visibility toggles on completion, server/network failure or leaving
the form. Generation checks and request cancellation ignore late responses.
Success and errors use translated toasts; a current 401 passes its safe notice
through `WorkspacePage` to `App`, whose auth toast survives workspace disposal.

`POST /auth/password` checks the trusted cookie identity, Origin and CSRF, then
calls `AuthService.change_password`. The service locks the user before the current
session, rechecks activity/expiry after waiting, validates the old password and
the new 12–128-character password, and preserves whitespace. One transaction
updates the scrypt hash, revokes the actor's other sessions and records
`account.password_change`; failure rolls everything back. The current cookie,
CSRF and session expiry remain unchanged. Responses contain safe codes only and
use `Cache-Control: no-store`; secrets are absent from audit/validation output.
No schema migration is required. Administrator password reset remains a separate
use case that revokes all sessions of the target account.

Administration is an `admin-users` view selected by `?view=admin-users`. Only admin
sessions see its account-menu entry. Entering the view re-reads the server session
and checks actor, CSRF and current role before mounting `pages/AdminPage.svelte`.
Query/history is navigation state, never authorization. Leaving the view unmounts
admin form/state and clears password drafts; chat/document/LLM owners remain mounted.
Stale create, lookup and navigation responses cannot update a later view/session.
An `admin_required` response leaves administration without logging out; Origin/CSRF
403 errors do not imply role loss. A protected 401 uses the normal expiry path.
An uncertain create is not automatically retried; exact-email lookup reports the
current account without attributing it to the previous POST.

Account creation opens in the shared `SurfaceDialog` above the Users directory,
with a dimmed backdrop, trapped keyboard focus and locked background scrolling.
Validation, uncertain-result feedback and email lookup remain inside the modal.
Escape, backdrop and close actions are disabled during an active request. Success
closes the modal, refreshes the directory and returns focus to Create account.
The retained admin page releases its native modal while personal Settings is
visible, then restores it when browser history returns to Users.

The workspace presence owner sends `POST /auth/presence` immediately and every
30 seconds while visible or 60 seconds in the background. Origin, CSRF and the
current cookie session are checked before the service writes server UTC time.
Writes sharing one session are throttled to 25 seconds. Login also records
activity. `auth_sessions.last_seen_at` grants a 180-second presence lease only
while that session is unexpired and its account is enabled; any fresh session
makes the account online. `users.last_active_at` retains the last observation
after logout or session revocation. Migration 0011 adds nullable timestamps;
existing accounts remain unknown until their next login or heartbeat.

The admin list keeps account metadata compatible and adds a `presence` map keyed
only by IDs on the returned page. Users refreshes that page every 15 seconds while
visible, preserving the active search and pagination. Last active displays Online,
a localized relative time, or Never active. Failed background refreshes keep rows
and label presence unavailable, never infer Offline. `is_active` still controls
account enablement and authorization. Heartbeats have a 10-second timeout, never
overlap within a workspace, and stop on disposal or a current 401. No client
timestamp, account ID or unload-based Offline command is trusted.

Chat Markdown uses pinned `marked` tokens and Svelte escaping; raw HTML and model
images/embeds remain text, and links allow only absolute HTTP/HTTPS URLs. The
browser persists only an explicit locale choice under `ruvie.ui.locale`; UI
language does not change question content, API scope or the LLM's answer language.

### Implemented scope and remaining gaps

The runtime supports registration/login, projects, authorized upload/ingestion,
passage search, provider/model settings and cited streaming answers. Notes,
Workspace library tabs, folder/history persistence and unsupported chat Controls
remain placeholders. There is no document preview/download API or persistent chat
history, general system settings administration, ticket integration, automatic repair/tool execution,
or role/software-version personalization of answers.

`references/` is read-only legacy source, not an active runtime dependency. Every
directory named `archive` is excluded from active context. Broader proposals in
specs must not be mistaken for implemented components. Existing diagrams are
linked from [Visual specifications](visual/README.md); compare them with
the active source when changing a flow.

#### Workspace presentation convention

Workspace content groups use the existing page background by default: transparent
background, no enclosing border, card radius or shadow. Group content through
headings and spacing. Apply this convention to future page and feature components.
Interactive controls, dialogs, popovers and navigation selection indicators retain
their own visible interaction states. All settings tabs inherit this presentation
from `SettingsPanel.svelte`; new tabs should use that shared panel.

#### Workspace theme preference

The active application targets desktop browsers and has no mobile navigation or
mobile-specific page layout. Browser zoom, keyboard navigation and reduced-motion
preferences remain supported.

Account menu > Settings opens an embedded Appearance page in the workspace content area, preserving the main sidebar. The page is available to administrators and regular users and contains only appearance controls, including language and Background (System, Light and Dark). Admin > System settings contains only LLM connection controls. Both use the same embedded settings layout. The label does not change the existing per-account LLM persistence or API authorization contracts. The `view=settings` query supports direct navigation, reload and Back/Forward alongside the existing admin views. The unconfigured-model shortcut opens system settings only for administrators; regular users cannot open provider editing from the UI. The settings
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

## 2. Target architecture (proposal)

Version: 0.2. The proposal below describes target capabilities and design constraints; it is not a statement that those capabilities exist in the active application.
### 1. Mục tiêu kiến trúc

Kiến trúc phải hỗ trợ:

- nhiều role và nhiều project;
- document-level access control;
- personalization theo project, software, software version và plugin version;
- RAG có source citation;
- Skills và external tools có kiểm soát;
- đánh giá hệ thống đề xuất bằng scenario và metrics;
- audit cho truy cập bị từ chối và tool call.

Ruvie/OpenWebUI trong `references/` là implementation tham khảo. Active
application xây độc lập; không mặc định copy toàn bộ kiến trúc hoặc source của
reference.

### 2. High-Level Architecture

```text
User
  |
  v
Frontend ─────── confirmation UI for side-effect actions
  |
  v
Backend API
  |
  +--> Authentication ──> trusted identity
  |
  +--> Domain Authorization ──> authorized resource scope
  |          |                         |
  |          |                         +--> Audit event
  |          v
  |     User / Project Context
  |
  +--> Chat Orchestrator
         |
         +--> Retrieval Service ──> Vector Store / Document Store
         |          |
         |          +--> authorization filter → personalization/reranking
         |
         +--> Typed Tool Adapter ──> Compatibility Registry
         |          |                Ticket System
         |          +--> tool + object authorization → audit event
         |
         +--> LLM Provider
                  |
                  v
          streamed answer + citations
```

Thứ tự là bắt buộc: **Authentication → Authorization → Authorized Scope →
Retrieval → Personalization → LLM**. Personalization không được mở rộng phạm
vi dữ liệu đã được cấp quyền.

### 3. Các thành phần chính

#### 3.1. Frontend

Trách nhiệm:

- login và quản lý session client;
- chat, upload/select document và project context;
- hiển thị streaming state, citations và trạng thái tool;
- hiển thị ticket draft;
- yêu cầu user xác nhận ngay trước tool có side effect.

Frontend không tự quyết định permission. Confirmation của frontend chỉ là UX;
backend phải xác minh confirmation token trước khi thực thi action.

#### 3.2. Backend API

Trách nhiệm:

- xác thực request và cung cấp trusted identity;
- load domain context;
- gọi Authorization Service trước retrieval/tool execution;
- gọi Chat Orchestrator;
- trả streaming answer/citations;
- ghi audit events.

MVP API chỉ cần các nhóm endpoint: session, chat, files/knowledge, retrieval,
citations, compatibility lookup và ticket preparation/creation.

#### 3.3. Authentication

Trách nhiệm:

- xác định user identity;
- session/token lifecycle;
- cung cấp trusted `user_id` cho backend;
- bảo vệ endpoint khỏi anonymous access.

JWT/password hashing/session dependency của Ruvie là tham khảo để adapt sau
security review; domain role không lấy trực tiếp từ role `admin/user/pending`
của reference.

#### 3.4. Domain Authorization Service

Authorization Service là boundary trung tâm, không phải system prompt và không
do LLM quyết định.

Trách nhiệm:

- resolve role, project membership và explicit grants;
- kiểm tra quyền document/knowledge/skill/tool/ticket;
- tạo **authorized resource scope** cho retrieval;
- kiểm tra lại tool permission và object scope từ arguments;
- ghi `allow`/`deny` audit events.

Yêu cầu bất biến:

- resource không được phép không xuất hiện trong LLM context;
- tool được phép không đồng nghĩa với quyền đọc mọi object;
- deny không được tiết lộ metadata nhạy cảm của resource.

#### 3.5. User and Working Context

Context tối thiểu:

```json
{
  "user_id": "u-001",
  "role": "bim_cad_specialist",
  "project_ids": ["project-alpha"],
  "team": "bim",
  "software": "Revit",
  "software_version": "2026",
  "plugin_id": "plugin-x",
  "plugin_version": "2.4"
}
```

Context do identity, membership và input đã validate tạo thành. Trường thiếu
không được suy đoán như một quyền mới.

#### 3.6. Chat Orchestrator

Trách nhiệm:

1. nhận query, identity và validated working context;
2. yêu cầu authorized resource scope;
3. gọi Retrieval Service;
4. áp dụng personalization/reranking trên kết quả đã authorized;
5. quyết định có cần typed tool hay không;
6. gọi LLM với authorized context, tool result và citation provenance;
7. stream final answer.

Orchestrator không truy cập vector store hoặc external system theo đường tắt
ngoài Authorization Service/Tool Adapter.

#### 3.7. Retrieval Service

Pipeline:

```text
Document ingestion
  → parse / normalize
  → chunk
  → embed
  → index with domain metadata

User query
  → authorized scope
  → retrieval filter
  → retrieve candidates
  → version/project-aware reranking
  → citations + authorized context
  → LLM
```

Document và chunk metadata tối thiểu:

```json
{
  "document_id": "doc-123",
  "project_id": "project-alpha",
  "document_type": "plugin_guide",
  "allowed_roles": ["bim_cad_specialist", "it_support"],
  "software": "Revit",
  "software_versions": ["2025", "2026"],
  "plugin_id": "plugin-x",
  "plugin_versions": ["2.4"],
  "sensitivity": "internal",
  "source_uri": "..."
}
```

The vector query itself must be constrained to the authorized scope. Filtering
after retrieval is not acceptable. Citation must preserve document id, title,
chunk/location and source URI through to the UI.

#### 3.8. Personalization Service

Input:

- authorized retrieved documents;
- project membership;
- role/team;
- software/plugin and versions;
- user task and technical level.

Allowed effects:

- rank/filter within the authorized set;
- choose answer detail/style;
- select compatible documents or tool query parameters.

Forbidden effect: add project, document, ticket or tool access.

#### 3.9. Skills

Planned Skills:

- Troubleshooting;
- Log Analysis;
- Incident Summary;
- Ticket Preparation.

Skills are reviewed workflows with typed input/output. The MVP must not use
database-stored executable Python functions, arbitrary prompt artifacts or
unreviewed dynamic code as Skills.

#### 3.10. Typed Tool Adapter

Tool Adapter exposes only declared operations:

```text
get_plugin_version(plugin_id)
get_compatibility(plugin_id, software, version)
get_service_status(service_id)
get_ticket(ticket_id)
get_my_tickets()
prepare_ticket(...)
create_ticket(confirmed_draft_id)
```

For every call it must:

1. validate the arguments against a typed schema;
2. check tool permission;
3. check project/resource scope from the arguments;
4. require a valid confirmation for side effects;
5. execute through a domain adapter;
6. return structured output and record an audit event.

MCP or OpenAPI can be transport implementations behind this interface; user
supplied arbitrary tool servers and terminal/shell execution are out of scope.

### 4. External Systems

#### 4.1. Compatibility / Technical Status Registry

Read-only domain adapter for:

- plugin and latest version;
- supported software versions;
- known incompatibilities;
- approved technical/service status.

Use a mock registry for the initial experiment. The adapter allows replacement
with an organizational system later without changing orchestration code.

#### 4.2. Ticket System

Ticket flow:

```text
Issue + context + attempted steps
  → prepare_ticket
  → user reviews draft
  → backend records confirmation
  → create_ticket
  → ticket reference + audit event
```

`create_ticket` is the first external side effect and is never triggered solely
from a model response.

### 5. Data Stores

| Store | Responsibility |
|---|---|
| PostgreSQL relational DB | users, roles, projects, memberships, grants, ticket metadata, confirmation records |
| Document/object storage | original uploaded files and normalized document content |
| Vector store | embeddings, chunk text and retrieval metadata |
| Audit store | access decisions, retrieval scope identifiers, tool attempts/results and ticket actions |

PostgreSQL là source of truth cho authorization và dùng migration để quản lý
schema. Vector store là index, không phải authority về permission.

### 6. Main request flows

#### 6.1. Answer with RAG

```text
User query
  → Authenticate
  → Load validated user/working context
  → Resolve authorized scope
  → Retrieve only within that scope
  → Personalize/rerank authorized candidates
  → Generate answer with citations
  → Stream answer and audit result
```

#### 6.2. Answer requiring a tool

```text
User query
  → Authenticate and resolve scope
  → Determine eligible typed tool
  → Validate arguments
  → Re-check tool + object authorization
  → Execute read-only adapter
  → Generate answer with tool provenance
```

#### 6.3. Ticket creation

```text
User query
  → prepare ticket draft
  → user confirmation
  → validate confirmation + authorization again
  → create ticket
  → return ticket id and audit event
```

### 7. Experiment execution

Thực nghiệm đánh giá một phiên bản xác định của hệ thống đề xuất bằng dataset,
scenario và metrics trong `04-experiment-plan.md`; không duy trì các biến thể
A/B/C hoặc feature flags chỉ để so sánh.

Mỗi lần chạy phải ghi nhận application revision, PostgreSQL schema migration,
LLM, embedding model, dataset version, user permissions, trạng thái tool và
generation parameters để kết quả tái lập được.

### 8. Design constraints

- Authorization precedes retrieval and personalization.
- Permission is not decided by the LLM or frontend.
- Unauthorized resources never enter LLM context, tool result or citation.
- The vector store must receive an authorized filter/scope before query.
- Tool execution always passes through the Typed Tool Adapter.
- Side-effect actions require explicit confirmation and a second authorization
  check.
- RAG and tool outputs retain source provenance.
- Domain logic does not live entirely in a system prompt.
- External integrations are adapters so mock services can support experiments.
- No arbitrary shell commands, dynamic DB-stored Python tools/filters or
  unreviewed user-supplied tool servers in the MVP.
