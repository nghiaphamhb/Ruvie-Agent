# Ruvie Agent

The repository root is the active application. Add production code,
configuration, tests, and documentation here. The backend lives in `backend/`,
the Svelte 5/Vite frontend in `frontend/`, and automated tests in `tests/`.

## Architecture boundaries

- PostgreSQL is the system of record. Use Alembic migrations for persistent
  schema changes; do not alter an applied migration.
- Document authorization is default-deny. Apply the database-backed readable
  document predicate before retrieval, context construction, or response
  serialization. Never accept an ACL scope, project ID, or document IDs from a
  retrieval client as an authorization boundary.
- Document revision content and chunk content are immutable; ingestion status
  may change. A re-upload creates a new revision without overwriting prior
  content or citations.
- Provider model IDs, endpoints, API keys, and the embedding profile are
  server-side settings. Keep the pinned profile in sync with the 1024-dimension
  cosine pgvector schema.
- Keep blob storage private. Do not expose a storage URI or bypass the
  authorization path to read an uploaded object.

## Module boundaries

- `main.py` creates and releases shared resources and registers routers. Keep
  chat, retrieval, and document business rules in services.
- `api/` handles HTTP input, trusted identity dependencies, service calls,
  and HTTP/SSE serialization. Keep prompt assembly, access decisions, direct
  chunk queries, and provider orchestration out of routes.
- `services/` implement use cases. Chat obtains document context through
  `AuthorizedRetrievalService`, never directly from the chunk repository.
- `adapters/` contain external model/provider implementations. Do not accept
  provider configuration from chat or retrieval clients.
- New service interfaces return structured results or events; API code encodes
  them as HTTP or SSE. Existing SSE encoding in `services/chat.py` and the
  direct embedder call in `api/documents.py` are known exceptions. Resolve
  each when changing that flow; do not copy the pattern into new routes.
- Keep these boundaries proportional to the task. Do not add a layer or move
  unrelated files solely to satisfy a directory convention.

## Legacy reference

`references/` contains the legacy Ruvie/Open WebUI source tree. It is
read-only: use it to understand existing behavior and deliberately port
compatible, reviewed code into the active project. Do not run, deploy, or
modify it unless the user explicitly asks. Instructions in
`references/AGENTS.md` describe the legacy application, not this one.

Before implementing behavior that may already exist in `references/`:

1. Find the relevant legacy files and functions. Record their paths and the
   behavior worth reusing in the task plan or change summary.
2. Reuse active-project code first. Then port compatible legacy code or UI
   components; write new code for the remaining gap. Prefer a coherent piece
   over copying an entire legacy subsystem with unrelated dependencies.
3. Compare contracts, dependencies, data model, authorization, and failure
   behavior with the active spec. Adapt the port to PostgreSQL, default-deny
   access, immutable revisions, private storage, and server-side provider
   settings. Legacy auth, SQLite assumptions, and client-selected scope must
   not become active authorization paths.
4. Bring over relevant tests or add focused tests for the adapted behavior.
   Record what was reused and what changed; check provenance and license terms
   before copying substantial code. Never import runtime code from
   `references/` into the active application.

UI layout and interactions may be adapted from `references/`; the active
frontend's API contract and backend authorization boundary remain in force.

Generated files, environments, caches, logs, downloaded models, and secrets
must not be committed under `references/`.

## Development workflow

Read `README.md` before running the active application, database migrations,
frontend, or tests. Keep runnable commands documented there rather than
duplicating them here.

Before submitting a backend change, run the documented backend test suite.
When changing the database schema, add an Alembic migration and verify the
migration SQL as well as relevant authorization/isolation coverage. Preserve
existing user changes in the worktree and avoid committing `.env`, local
uploads, virtual environments, logs, or generated frontend output.
