# Ruvie Agent

The repository root is the active application. Add production code,
configuration, tests, and documentation here. The backend lives in `backend/`,
the Svelte frontend in `frontend/`, and automated tests in `tests/`.

## Architecture boundaries

- PostgreSQL is the system of record. Use Alembic migrations for persistent
  schema changes; do not alter an applied migration.
- Document authorization is default-deny. Apply the database-backed readable
  document predicate before retrieval, context construction, or response
  serialization. Never accept an ACL scope, project ID, or document IDs from a
  retrieval client as an authorization boundary.
- Document revisions and chunks are immutable. A re-upload creates a revision;
  it does not overwrite prior content or citations.
- Embedding configuration is server-side and pinned. Keep the 1024-dimension
  cosine pgvector schema and the configured embedding profile in sync.
- Keep blob storage private. Do not expose a storage URI or bypass the
  authorization path to read an uploaded object.

## Legacy reference

`references/` contains the legacy Ruvie/Open WebUI source tree. It is
read-only by default: use it to understand existing behavior or deliberately
port a small, reviewed piece into the active project. Do not run, deploy, or
modify it unless the user explicitly asks.

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
