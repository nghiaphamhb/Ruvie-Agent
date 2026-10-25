# Ruvie Agent

The repository root is the active application: backend in `backend/`, Svelte 5/Vite
frontend in `frontend/`, and automated tests in `tests/`. Add active code,
configuration, tests, and documentation here.

## Approval before file changes

- Before creating, editing, deleting, moving, or renaming files, report
  the affected paths, planned actions, purpose, and intended validation.
- Wait for explicit user approval before making those changes.
  A request to investigate or propose changes is not approval to edit.
- Approval covers the reported scope; do not ask again within that scope.
  Report additional file changes and obtain approval before proceeding.
- Read-only inspection may proceed without approval. Include commands
  that generate or overwrite files in the proposed scope.
- This rule applies to AGENTS.md itself.

## User-facing documentation

- Keep `docs/` for guides and reference documentation intended for application users. Put agent/developer architecture, implementation notes and design proposals in `specs/` or another appropriate internal location.

## Archived files
Exclude every directory named `archive` (case-insensitive, at any depth) from
searches and project context. Do not read, edit, execute, or use its contents.

## Architecture boundaries

- PostgreSQL is the system of record. Use Alembic for persistent schema changes;
  never modify an applied migration.
- Document access is default-deny. Apply the database-backed readable-document
  predicate before retrieval, context construction, or response serialization.
  Client-supplied ACL scopes, project IDs, or document IDs are not authorization.
- Revision and chunk content are immutable; ingestion status may change.
  Re-uploads create revisions without overwriting prior content or citations.
- Provider model IDs, endpoints, API keys, and embedding profiles are server-side
  settings. Keep the pinned profile aligned with 1024-dimension cosine pgvector.
- Keep blobs private: never expose storage URIs or bypass authorized object reads.

## Backend boundaries

- `main.py`: shared resource lifecycle and router registration; business rules
  for chat, retrieval, and documents belong in services.
- `api/`: HTTP input, trusted identity dependencies, service calls, HTTP/SSE
  serialization. No prompt assembly, access decisions, direct chunk queries,
  or provider orchestration in routes.
- `services/`: use cases. Chat obtains context through
  `AuthorizedRetrievalService`, never directly from the chunk repository.
- `adapters/`: external provider implementations. Never accept provider
  configuration from chat or retrieval clients.
- New services return structured results/events; API code encodes HTTP/SSE.
  The direct embedder call in `api/documents.py` is a known exception.
  Resolve it when changing that flow; do not copy it into new routes.
- Keep boundaries proportional: no new layers or unrelated moves for convention alone.

## Frontend organization

Organize `frontend/src/lib/` by feature, with thin composing pages:

- `pages/`: page composition, navigation state, page/session lifecycle.
  `WorkspacePage.svelte` connects feature owners and views.
- `layout/`: shells, sidebar/account navigation, responsive layout and focus.
  Keep `WorkspaceShell.svelte`, `AppSidebar.svelte`, and `AccountMenu.svelte` here.
- `features/<feature>/`: feature components, state, API clients, and business logic
  (auth, chat, documents, llm, settings, etc.).
- `shared/`: reusable components without feature-specific logic.
- `i18n/`: locale selection, translation utilities, and catalogs.

Pages compose features/layouts; layouts must not import pages. Keep business
logic and API operations in their features. Add functionality within its feature
first; extract modules only when responsibilities warrant it. Preserve descriptive
names such as `WorkspacePage` and `WorkspaceShell`.

## Legacy reference

`references/` is the read-only legacy Ruvie/Open WebUI source. Use it to understand
behavior and deliberately port compatible, reviewed code; never import its runtime
code. Do not run, deploy, or modify it without explicit user instructions.
`references/AGENTS.md` describes the legacy app, not the active one.

Before implementing behavior that may exist there:

1. Find relevant legacy files/functions; record paths and reusable behavior in
   the task plan or change summary.
2. Reuse active code first, then port coherent compatible legacy pieces;
   write new code for remaining gaps. Avoid unrelated subsystem dependencies.
3. Compare contracts, dependencies, data model, authorization, and failures with
   the active spec. Adapt to PostgreSQL, default-deny access, immutable revisions,
   private storage, and server-side provider settings. Do not port legacy auth,
   SQLite assumptions, or client-selected scope as authorization.
4. Port relevant tests or add focused tests. Record source paths, reused behavior,
   and adaptations. No separate license check is required for supplied reference
   code; a missing LICENSE must not block reuse.

Legacy UI may be adapted while preserving active API and authorization contracts.
Never commit generated files, environments, caches, logs, downloaded models, or
secrets under `references/`.

## Development workflow

- Read `README.md` before running the app, migrations, frontend, or tests.
  Read [current and target architecture](specs/02-architecture.md) when working on module
  boundaries, data flows, authorization, persistence or feature state ownership.
  Use [database setup](docs/database-setup.md) for migrations and database operations.
  Keep runnable commands in README or linked documentation, not duplicated here.
- Run the documented backend suite before submitting backend changes.
- For schema changes, add an Alembic migration and verify its SQL plus relevant
  authorization/isolation coverage.
- Preserve user work. Never commit `.env`, local uploads, virtual environments,
  logs, or generated frontend output.

## Agent validation workflow

Start Docker Desktop with Linux containers before database tests. Tests create
disposable PostgreSQL/pgvector containers and databases, run Alembic there and use
local fake providers. They do not require provider keys or reset the application
database. The first run may pull the test image. Do not run two backend suites at
once: their shared fixture owns process-wide application/provider resources.

From the repository root:

~~~powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONPATH = 'tests;backend'
npm --prefix frontend run build
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_*.py'
npm --prefix frontend test
npm --prefix frontend run lint
npm --prefix frontend run format:check
~~~

Browser tests require an installed Playwright module and Chromium. Point the
environment variables at your installation; these paths are examples to replace:

~~~powershell
$env:RUVIE_PLAYWRIGHT_PATH = 'C:\path\to\node_modules\playwright'
$env:RUVIE_BROWSER_PATH = 'C:\path\to\chrome.exe'
~~~

If using Playwright's default browser installation instead, install the matching
browser with `node "$env:RUVIE_PLAYWRIGHT_PATH\cli.js" install chromium` and leave
`RUVIE_BROWSER_PATH` unset. Build the frontend before browser runs. Without the
module/build prerequisites, Python browser tests report skips; the admin form
component browser test skips without `RUVIE_PLAYWRIGHT_PATH`. A skip is not a pass.

With browser variables configured, run the full backend command above again to
include browser tests. For focused account integration and frontend regression:

~~~powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_f012_*.py'
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_f009_006_registration_e2e.py'
npm --prefix frontend test
node frontend/tests/admin-browser.mjs
node frontend/tests/auth-browser.mjs
node frontend/tests/theme-browser.mjs
node frontend/tests/workspace-browser.mjs
node frontend/tests/llm-browser.mjs
node frontend/tests/frontend-ux-browser.mjs
~~~

`admin-e2e.mjs` and `auth-e2e.mjs` are launched by Python with a disposable backend,
ports and database; do not launch them against the application database. Standalone
browser scripts fake their HTTP boundary. Build output is under `frontend/dist/`;
screenshots are under ignored `logs/`. Neither should be committed. See the F012
spec for measured results and known regression failures; these commands do not
imply that every current browser regression passes.
