# Ruvie Agent

Ruvie Agent lets project members upload PDF or text files, retrieve authorized
passages, and chat with citations. PostgreSQL with pgvector stores application
data and vectors; uploaded files stay in private blob storage.

## Requirements

- Python 3.11+
- Node.js and npm
- PostgreSQL with the pgvector extension

## Setup

Create and install the backend environment:

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
~~~

Install frontend dependencies:

~~~powershell
Set-Location frontend
npm install
Set-Location ..
~~~

Create `.env` and set `DATABASE_URL`, the embedding profile/provider, `LLM_*`
if chat is needed, and `AUTH_ALLOWED_ORIGINS` for the browser origin. Keep
credentials local. The vector schema requires 1024-dimensional cosine
embeddings.

~~~powershell
Copy-Item .env.example .env
~~~

## Database

Review the SQL, apply migrations to the database in `DATABASE_URL`, then check
the active revision:

~~~powershell
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini upgrade head --sql
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini upgrade head
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini current
~~~

Confirm the target database before applying migrations. It must have pgvector
installed.

There is no public signup. Provision a password for an existing user:

~~~powershell
Set-Location backend
..\.venv\Scripts\python.exe -m ruvie.password_cli user@example.com
Set-Location ..
~~~

The command prompts for the password without displaying it.

## Run locally

Start each process in a separate terminal.

Backend, from the repository root:

~~~powershell
.\.venv\Scripts\uvicorn.exe ruvie.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
~~~

Frontend:

~~~powershell
Set-Location frontend
npm run dev
~~~

In another terminal, start the document ingestion worker:

~~~powershell
Set-Location backend
..\.venv\Scripts\python.exe -m ruvie.worker_cli
~~~

Check the backend at <http://127.0.0.1:8000/health>. Vite prints the frontend
URL when it starts.

## Backend layout

- `api/` handles HTTP and SSE; `contracts/` defines request/response data.
- `models/` holds SQLAlchemy models grouped by data area.
- `services/` implements workflows; `adapters/` connects providers and storage.
- `main.py` starts the API; `worker_cli.py` starts ingestion separately.
- `references/` is read-only legacy source, not part of the runtime.

Document access is default-deny. The server determines identity and retrieval
scope; clients cannot select provider credentials or authorization scope.

## Tests

Run the backend suite from the repository root:

~~~powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
~~~

The end-to-end suite uses Docker and a disposable PostgreSQL/pgvector container.
Tests use fake providers; they do not connect to the development database or
external model APIs.

Run frontend tests from `frontend/`:

~~~powershell
npm test
~~~
