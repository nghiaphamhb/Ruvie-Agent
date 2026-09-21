# Ruvie Assistant

The repository root contains the active application. `references/` is legacy
source for reading only and is not part of the runtime.

## Prerequisites

- Python 3
- Node.js and npm
- A running PostgreSQL server with an empty local database

## Local setup

Create the Python environment and install backend dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

Copy the example configuration, then replace the password placeholder with
the credentials for the local PostgreSQL database:

```powershell
Copy-Item .env.example .env
notepad .env
```

`DATABASE_URL` uses the `postgresql+psycopg://` SQLAlchemy driver URL. Keep
`.env` local; it is ignored by Git and must not contain shared credentials.

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

The current baseline creates only Alembic's `alembic_version` table. Domain
tables will be introduced by later features.

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

## Tests

Run the complete backend test suite from the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

## Current scope

Foundation provides application scaffolding, configuration, PostgreSQL
migrations, and health endpoints. Authentication, domain schema, RAG, chat,
and tool execution are not implemented yet.
