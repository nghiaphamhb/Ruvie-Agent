# OpenWebUI / Ruvie Source Analysis

Version: 0.2
Status: completed source inspection — 2026-09-21

## 1. Scope and evidence

The inspected implementation is the read-only tree at `references/`. It is a
customized Open WebUI/Ruvie application, not the product to deploy unchanged.

| Field | Observed value |
|---|---|
| Frontend package | `references/package.json`: `open-webui` `0.10.2` |
| Backend package | `references/pyproject.toml`: `ruvie` |
| Reference revision | local repository `03ca9e1c6e80bfd425aecc6e1d159bf0e2269565` |
| Current remote | `https://github.com/nghiaphamhb/Ruvie-Assistant.git` |
| Licence record | No `references/LICENSE` is present; licence and original upstream commit must be verified before any source is copied. |

The decisions below concern architecture and implementation ideas. They do not
authorize copying source until the provenance record required in section 8 is
complete.

## 2. Repository map

```text
references/
├── src/                                      SvelteKit frontend
│   ├── routes/+layout.svelte                 application bootstrap and Socket.IO connection
│   ├── routes/(app)/+layout.svelte           authenticated application shell
│   ├── routes/(app)/c/[id]/+page.svelte      chat route
│   ├── lib/components/chat/Chat.svelte       chat state, submit and streaming UI
│   ├── lib/apis/openai/index.ts              completion request client
│   └── lib/apis/streaming/index.ts           SSE parser and source events
├── backend/ruvie/
│   ├── main.py                               FastAPI app, lifespan, router composition,
│   │                                         `/api/chat/completions`
│   ├── routers/auths.py                      sign-in, sign-up, LDAP/OAuth configuration
│   ├── routers/files.py                      upload and file access endpoints
│   ├── routers/knowledge.py                  knowledge-base lifecycle and sharing
│   ├── routers/retrieval.py                  parsing, chunking, indexing, query endpoints
│   ├── routers/tools.py                      tool CRUD and tool access management
│   ├── models/                               SQLAlchemy entities and data access helpers
│   ├── utils/auth.py                         JWT/API-key identity dependencies
│   ├── utils/middleware.py                   chat enrichment, RAG, tools and response handling
│   ├── utils/chat.py                         provider/model dispatch
│   ├── utils/tools.py                        local/OpenAPI tool resolution and builtin tools
│   ├── utils/access_control/                 file/folder access checks
│   └── retrieval/                            loaders, embeddings, vector-store abstraction
└── static/                                   frontend assets
```

`main.py` composes many generic product routers. The parts relevant to this
project are explicitly mounted under `/api/v1/auths`, `/api/v1/files`,
`/api/v1/knowledge`, `/api/v1/retrieval`, `/api/v1/tools`, and the completion
endpoint `/api/chat/completions`.

## 3. Observed flows

### 3.1 Login and session flow

```text
Svelte root layout
  → getSessionUser(token/cookie)
  → /api/v1/auths/signin or session endpoint
  → Auths.authenticate_user + bcrypt verification
  → create_session_response
  → signed JWT (user id, expiry, jti) + optional HttpOnly cookie
  → get_current_user dependency loads user for protected API calls
```

Evidence:

- `src/routes/+layout.svelte` initializes the session and Socket.IO client.
- `routers/auths.py:create_session_response` issues a JWT, returns role and
  computed permissions, and can set an HttpOnly cookie.
- `routers/auths.py:signin` rate-limits password sign-in and delegates password
  verification to `utils/auth.py`.
- `utils/auth.py:get_current_user`, `get_verified_user`, and `get_admin_user`
  are FastAPI dependencies for protected routes.

This gives a usable authentication baseline, but its built-in role vocabulary
is principally `admin`, `user`, and `pending`; it is not the domain RBAC model
required by `03-access-control.md`.

### 3.2 Chat and streaming flow

```text
Chat.svelte
  → generateOpenAIChatCompletion
  → POST /api/chat/completions
  → main.py validates selected model and chat/channel access
  → utils.middleware.process_chat_payload
       → history, filters, skills, RAG/files, tools
  → utils.chat.generate_chat_completion
       → OpenAI-compatible provider | Ollama | pipe
  → utils.middleware.process_chat_response
  → SSE events/text → createOpenAITextStream → message UI and citations
```

The primary orchestration seam is `utils/middleware.py:process_chat_payload`.
It builds trusted metadata from the authenticated user, processes chat history,
loads selected skills/tools, retrieves file context, and appends source context
before provider dispatch. `utils/chat.py` is a provider adapter rather than a
domain orchestrator.

The UI receives normal deltas and structured events. In particular,
`src/lib/apis/streaming/index.ts` recognizes `sources`, so citation display can
be preserved without coupling a new backend to the full legacy UI.

### 3.3 Ingestion, retrieval and citation flow

```text
Upload file
  → routers/files.py
  → routers/retrieval.py:process_file
  → configured loader
  → save_docs_to_vector_db
       → split chunks + metadata + embeddings + VectorDBBase.insert

Chat attachment / knowledge reference
  → middleware.chat_completion_files_handler
  → retrieval.utils.get_sources_from_items
  → filter_accessible_collections / has_access_to_file
  → vector or hybrid search + optional reranking
  → source objects
  → apply_source_context_to_messages + SSE `sources` event
```

Useful implementation details:

- `routers/retrieval.py:save_docs_to_vector_db` supports character/token
  splitting, metadata propagation, embedding engines and a vector DB adapter.
- `retrieval/vector/main.py:VectorDBBase` defines the minimum collection,
  insert, search, query and delete interface; multiple vector providers are
  implemented below it.
- `retrieval/utils.py:filter_accessible_collections` validates collection names
  and, for non-admin users, checks file ownership/share grants or knowledge-base
  access before query.
- `utils/access_control/files.py:has_access_to_file` handles ownership,
  knowledge-base, group, channel and shared-chat paths.
- `utils/middleware.py:chat_completion_files_handler` produces the source
  objects used both for LLM context and frontend citation events.

This is access-aware retrieval, but authorization is collection/file/knowledge
based. It has no first-class `project_id`, software version, plugin version or
document sensitivity policy for this product.

### 3.4 Tools, functions and MCP flow

```text
selected tool ids / configured server
  → process_chat_payload
  → local tools: utils.tools.get_tools
  → MCP: connect_mcp_server → MCPClient.call_tool
  → OpenAPI server: execute_tool_server
  → provider native function call or legacy tool-call loop
  → structured tool result, optional source event, final answer
```

`utils/tools.py:get_tools` checks an `AccessGrants` record before loading a
local tool and also checks configured OpenAPI-server access. The middleware
checks MCP connection access before establishing an `MCPClient`. Built-in tools
are conditionally injected according to global config, model capability and
some user feature permissions.

However, local tools and filters are Python source stored in database columns
(`models/tools.py` and `models/functions.py`) and loaded dynamically. That
execution model is inappropriate for the MVP unless a separate sandboxing and
review model is designed.

## 4. Component decision table

| Component | Legacy implementation | Decision | Rationale and boundary |
|---|---|---|---|
| Svelte chat shell, message rendering | `src/lib/components/chat/*` | ADAPT | Reuse interaction patterns only; extract a smaller domain chat UI. |
| SSE parser and source-event contract | `src/lib/apis/streaming/index.ts` | ADAPT | Small, useful protocol boundary for streaming and citations. |
| FastAPI router composition | `backend/ruvie/main.py` | ADAPT | Keep the framework pattern, not the monolithic app/route set. |
| JWT, password hashing, session dependency | `utils/auth.py`, `routers/auths.py` | ADAPT | Reuse only after a security review; map identity to domain roles/projects. |
| Generic users/groups/access grants | `models/users.py`, `models/access_grants.py` | ADAPT | Object-level grant concept is useful; schema/policy must become project-aware. |
| Product role and project authorization | no equivalent domain model | REWRITE | Build explicit BIM/CAD Specialist, Developer, IT Support roles; project membership and policy enforcement before retrieval. |
| Chat persistence/history | `models/chats.py`, `routers/chats.py` | ADAPT | Retain a minimal conversation/message model; omit sharing, channels and unrelated workspace features. |
| File upload and loader pipeline | `routers/files.py`, `retrieval/loaders/` | ADAPT | Loader boundary and async ingestion are useful; whitelist supported formats only. |
| Chunking, embeddings, vector abstraction | `routers/retrieval.py`, `retrieval/vector/main.py` | ADAPT | Retain interfaces and provenance ideas; redesign metadata and authorization filter around project/version. |
| Retrieval ACL | `filter_accessible_collections`, `has_access_to_file` | ADAPT | Valuable defence-in-depth reference; enforce the new policy in the retrieval query itself, not post-filtering. |
| Source citation | middleware source objects + frontend stream parser | ADAPT | Keep provenance from chunks through response; define a stable domain citation schema. |
| Personalization by project/software/plugin version | no domain implementation | REWRITE | Introduce typed user context and metadata filters/reranking after authorization. |
| Skills | legacy skills and prompt injection | REWRITE | Build narrow, reviewed workflow skills; do not expose arbitrary prompt/code artifacts. |
| OpenAPI/MCP transport client | `utils/tools.py`, `utils/mcp/client.py` | ADAPT | Use as protocol reference behind a domain tool adapter. |
| Tool permission, confirmation and audit | generic grants/capabilities | REWRITE | Enforce tool + object scope server-side; require confirmation for ticket creation and other side effects. |
| DB-stored Python tools, pipes and filters | `models/tools.py`, `models/functions.py` | IGNORE | Dynamic executable user/admin code expands the threat surface without helping the MVP. |
| Web search, images, code interpreter, terminal, calendar, channels, automations | generic feature modules | IGNORE | Outside MVP and increases operational/security scope. |
| Compatibility registry | no BIM/CAD-specific service | BUILD | Typed compatibility data and read-only query tool. |
| Ticket integration | no domain-specific integration | BUILD | Ticket schema, confirmation flow, adapter and audit record. |
| Experiment/evaluation harness | no thesis-specific framework | BUILD | Scenario fixtures, evaluators and metric capture from `04-experiment-plan.md`. |

## 5. Technical decisions for the new product

1. Keep the active application independent from `references`; copy no module
   wholesale as a starting point.
2. Implement one small FastAPI backend and Svelte frontend. Add only endpoints
   needed by the MVP: session, chat, files/knowledge, retrieval and citations.
3. Make `project_id`, document type, allowed roles, software, software version,
   plugin and plugin version explicit document/chunk metadata.
4. Resolve allowed projects/resources before generating a vector query. The
   LLM receives only retrieved, authorized chunks.
5. Keep a stable `Citation` payload from retrieval to streaming UI, containing
   document id, title, chunk/location and provenance; do not rely on an opaque
   legacy metadata shape.
6. Place compatibility and ticket operations behind typed backend adapters.
   The LLM selects only declared, validated operations; the backend checks both
   tool permission and object scope.
7. Require explicit user confirmation immediately before a ticket-creation
   side effect. Read-only compatibility lookup needs no confirmation.
8. Do not execute database-stored Python, arbitrary shell commands, terminal
   servers or arbitrary user-provided MCP/OpenAPI endpoints in the MVP.
9. Record the application revision, PostgreSQL schema migration, models,
   dataset, permissions and tool state for each evaluation run.

## 6. Components to build

- Domain identity/context: user role, team, project membership and trusted
  software/plugin working context.
- Authorization service: project/document/tool/ticket policy checks and audit
  events; it must be called before retrieval and tool execution.
- Knowledge schema and ingestion metadata for public versus synthetic internal
  documents.
- Retrieval service with authorized-scope filtering, version-aware ranking and
  citations.
- Focused chat orchestrator for the implemented product capabilities.
- Read-only compatibility registry adapter.
- Ticket preparation, confirmation and creation adapter.
- Evaluation fixture runner, ground-truth scenarios and metric collection.

## 7. Input for `02-architecture.md` v0.2

The architecture update should add these boundaries:

```text
Authenticated identity
  → Domain authorization service
  → Authorized retrieval scope
  → Retrieval + personalization/reranking
  → Chat orchestrator
  → optional typed tool adapter
  → streamed answer + citations + audit event
```

The authorization service is not a frontend concern and is not delegated to the
LLM. `Personalization` consumes only the already-authorized scope. Tool calls
must cross the same authorization boundary a second time because their object
arguments can change scope.

## 8. Reuse record required before implementation

Before copying or adapting any legacy source, add an entry to
`THIRD_PARTY_NOTICES.md` containing:

- original upstream repository URL and immutable commit/tag;
- applicable license text and notice;
- local source path and destination path;
- copied/adapted component or line range;
- modifications and reason;
- reviewer and verification date.

The currently inspected local reference does not retain a license file, so it
is insufficient as the provenance source by itself.
