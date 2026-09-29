# Ruvie Agent

Ruvie Agent is a project-scoped document-ingestion, retrieval, and chat MVP.
It stores domain and ACL data in PostgreSQL, indexes document chunks with
pgvector, and ensures that retrieval is restricted by a database-backed,
default-deny document policy before authorized context reaches the LLM.

The repository root contains the active application. `references/` is legacy
source for reading only and is not part of the runtime.

## What is implemented

- Domain entities for users, roles, projects, memberships, documents, direct
  read grants, and append-only audit events.
- Private document uploads that require membership in the target project and
  create immutable document revisions plus ingestion jobs.
- Text/PDF extraction, deterministic chunking, embedding validation, and
  pgvector-backed retrieval of ready revisions.
- Retrieval authorization applied in the database before chunks, citations, or
  document content are returned. A direct read grant applies only to its
  specific document.
- Stable citations that identify the document, revision, chunk, source hash,
  and source offsets.
- An OpenAI-compatible embedding adapter and streaming chat-completion adapter,
  both configured only on the server.
- A Svelte chat page that submits a message, consumes SSE answer events, and
  displays loading, error, and citation states.

Authentication remains an integration seam: trusted upstream middleware must
set `request.state.domain_user_id`. The API rejects requests without that
identity and never accepts an identity or authorization scope from the client.
Document upload creates ingestion jobs, but the repository does not yet include
a production process that continuously runs `DocumentIngestionWorker`.

## Prerequisites

- Python 3.11 or later
- Node.js and npm
- PostgreSQL with the `vector` (pgvector) extension available
- A running local PostgreSQL database owned by the configured user

## Local setup

Create the Python environment and install backend dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

Copy the example configuration. Set the PostgreSQL credentials and provider
credentials for the services you use:

```powershell
Copy-Item .env.example .env
notepad .env
```

`DATABASE_URL` uses the `postgresql+psycopg://` SQLAlchemy driver URL. The
current schema requires an embedding profile with a 1024-dimensional cosine
model; changing its dimension or distance metric requires a schema migration.
Keep `.env` local; it is ignored by Git and must not contain shared
credentials.

### Server configuration

| Variable | Required | Purpose |
|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL SQLAlchemy URL using the psycopg driver. |
| `EMBEDDING_MODEL_ID` | Yes | Model sent to the embedding provider. |
| `EMBEDDING_DIMENSION` | Yes | Must be `1024` for the current `vector(1024)` schema. |
| `EMBEDDING_DISTANCE_METRIC` | Yes | Must be `cosine` for the current HNSW index. |
| `EMBEDDING_BASE_URL` | For retrieval/chat | OpenAI-compatible base URL; the adapter calls `/embeddings`. |
| `EMBEDDING_API_KEY` | For retrieval/chat | Server-side bearer token for the embedding provider. |
| `LLM_BASE_URL` | For chat | OpenAI-compatible base URL; the adapter calls `/chat/completions`. |
| `LLM_MODEL` | For chat | Server-selected chat model ID. |
| `LLM_API_KEY` | For chat | Server-side bearer token for the LLM provider. |

`EMBEDDING_BASE_URL` and `EMBEDDING_API_KEY` must either both be set or both
be omitted. The three `LLM_*` values follow the same all-or-none rule. Provider
URLs, model IDs, API keys, embedding profiles, project IDs, document IDs, and
authorization scopes cannot be selected through `POST /chat`.

The MVP does not require an embedding model version because compatible
providers do not consistently expose one. The database still records the
server-selected model ID, dimension, and distance metric with each revision.

Install frontend dependencies in a separate terminal:

```powershell
Set-Location frontend
npm install
```

## Database migrations

Apply every pending migration to the database configured in `.env`:

```powershell
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini upgrade head
```

Check the active revision:

```powershell
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini current
```

For a review of the generated PostgreSQL migration SQL without changing the
database, run:

```powershell
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini upgrade head --sql
```

The migration chain creates the domain/ACL tables plus document revisions,
ingestion jobs, document chunks, and pgvector indexes. Ensure the database
server has pgvector installed before applying it.

## Run locally

Start the backend from the repository root:

```powershell
.\.venv\Scripts\uvicorn.exe ruvie.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

In a second terminal, start the frontend from `frontend/`:

```powershell
npm run dev
```

Verify the backend after it starts:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/ready
```

Both endpoints return `status: ok`. The backend API documentation is at
`http://127.0.0.1:8000/docs`; Vite prints the frontend URL when it starts.

`POST /documents/upload` and `POST /documents/retrieve` require an upstream
authentication integration to populate `request.state.domain_user_id`. The
retrieval route also requires a configured query embedding adapter. These
dependencies intentionally fail closed; do not use client-supplied identity or
authorization fields to bypass them.

### Chat endpoint

`POST /chat` accepts only this JSON body:

```json
{"message":"How do I install plugin X?"}
```

The route requires `request.state.domain_user_id`, the embedding provider, and
the LLM provider. It builds the retrieval scope on the server, searches only
authorized ready revisions, and sends only authorized chunk text to the LLM.
The response uses `Content-Type: text/event-stream` with `delta`, optional
`citations`, and `completed` events. Provider failures are returned as a safe
`error` event without provider credentials, upstream response bodies, or
private document content.

The chat history exists only in the browser page and is lost on reload. The
request path does not store messages, execute tools or skills, or create
tickets.

### Integration seams

- **Identity:** add trusted authentication middleware that resolves a domain
  user and sets `request.state.domain_user_id` before protected routes run.
- **Ingestion runner:** deploy a separate process or command that calls
  `DocumentIngestionWorker.run_next()` with polling, shutdown, and retry rules.
- **Blob storage:** the application lifecycle currently wires
  `LocalBlobStore` at `data/uploads`; production S3-compatible wiring remains
  deployment work even though the adapter exists.
- **Providers:** embedding and LLM calls use OpenAI-compatible HTTP contracts.
  Provider-specific authentication or payload differences require an adapter,
  not client-controlled request fields.

## Tests

Run the complete backend test suite from the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

The suite uses SQLite for most service-level tests and generates PostgreSQL
migration SQL for schema coverage; it does not download an embedding model or
call external embedding or LLM services.

Run the frontend API-client tests from `frontend/`:

```powershell
npm test
```

## Current scope

The current scope includes authorized document upload/retrieval and ephemeral
streaming chat with citations. Login and identity provisioning, a production
ingestion runner and retry policy, persisted chat history, OCR, hybrid search,
project administration, and tool execution are not implemented yet.
