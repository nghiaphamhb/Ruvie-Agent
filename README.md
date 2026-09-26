# Ruvie Agent

Ruvie Agent is a project-scoped document-ingestion and retrieval
foundation. It stores domain and ACL data in PostgreSQL, indexes document
chunks with pgvector, and ensures that retrieval is restricted by a
database-backed, default-deny document policy.

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

The frontend remains a minimal Svelte shell. The backend HTTP routes are
integration seams: authentication must set `request.state.domain_user_id`, and
a production query embedder must be supplied before `/documents/retrieve` can
return results.

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

Copy the example configuration. Set the PostgreSQL credentials and replace the
embedding model revision placeholder with an exact 40-character commit SHA:

```powershell
Copy-Item .env.example .env
notepad .env
```

`DATABASE_URL` uses the `postgresql+psycopg://` SQLAlchemy driver URL. The
current schema requires an embedding profile with a 1024-dimensional cosine
model; changing its dimension or distance metric requires a schema migration.
Keep `.env` local; it is ignored by Git and must not contain shared
credentials.

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

## Tests

Run the complete backend test suite from the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

The suite uses SQLite for most service-level tests and generates PostgreSQL
migration SQL for schema coverage; it does not download an embedding model or
call an external embedding service.

## Current scope

The current scope ends at authorized document ingestion and retrieval. Login
and identity provisioning, a production embedding provider/worker runner,
chat and answer generation, OCR, hybrid search, project administration, and
tool execution are not implemented yet.
