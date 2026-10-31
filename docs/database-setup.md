# Ruvie Agent database setup

[Back to README](../README.md).

## Start PostgreSQL

Start Docker Desktop with Linux containers. Run these PowerShell commands from
the repository root. Replace the password placeholder with a local password.

The [pgvector image](https://github.com/pgvector/pgvector#docker) includes the
vector extension; Docker downloads it automatically when needed.

~~~powershell
docker volume create ruvie-postgres-data
docker run --detach --name ruvie-postgres --restart unless-stopped --publish 127.0.0.1:5432:5432 --env POSTGRES_USER=ruvie --env POSTGRES_PASSWORD=replace-with-local-password --env POSTGRES_DB=ruvie --mount source=ruvie-postgres-data,target=/var/lib/postgresql/data pgvector/pgvector:0.8.6-pg16-bookworm
~~~

The database is reachable through the host's loopback interface. The named
volume preserves data across container stops and replacement. These credentials
are for local development: POSTGRES_USER creates a PostgreSQL superuser, so
use a separate restricted application role for production.

Set the connection string in .env:

~~~dotenv
DATABASE_URL=postgresql+psycopg://ruvie:replace-with-local-password@127.0.0.1:5432/ruvie
~~~

URL-encode special characters in the password when placing it in DATABASE_URL;
keep the actual password in POSTGRES_PASSWORD. The backend and Alembic load
this .env automatically. An existing shell DATABASE_URL takes precedence.

Wait until PostgreSQL accepts connections; rerun the readiness command if
startup is still in progress:

~~~powershell
docker exec ruvie-postgres pg_isready -U ruvie -d ruvie
docker exec ruvie-postgres psql -U ruvie -d ruvie -c "SELECT current_database(), current_user;"
~~~

## Apply migrations

On a fresh Docker database, initialize Alembic's bookkeeping table before
the first upgrade. Existing migration identifiers exceed Alembic's default
32-character version column; this matches the end-to-end test setup:

~~~powershell
docker exec ruvie-postgres psql -U ruvie -d ruvie -v ON_ERROR_STOP=1 -c "CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(128) NOT NULL PRIMARY KEY);"
~~~

Review the SQL, apply migrations to the database in `DATABASE_URL`, then check
the active revision:

~~~powershell
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini upgrade head --sql
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini upgrade head
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini current
~~~

## Operate the database

Inspect the container and recent logs:

~~~powershell
docker ps --all --filter name=ruvie-postgres
docker logs --tail 100 ruvie-postgres
~~~

Use `docker stop ruvie-postgres` and `docker start ruvie-postgres` to stop and
start the container. Wait for readiness before starting the backend or worker.

Open an interactive SQL session (\q exits):

~~~powershell
docker exec -it ruvie-postgres psql -U ruvie -d ruvie
~~~

Changing `POSTGRES_USER`, `POSTGRES_PASSWORD`, or `POSTGRES_DB` does not update
an initialized volume. Reuse `ruvie-postgres-data` when replacing the container;
deleting it permanently deletes the database.

## Troubleshooting

- **Docker is not recognized or the daemon is unavailable:** install/start
  Docker Desktop, use Linux containers, and reopen the terminal.
- **Port 5432 is already in use:** choose another host port, such as
  --publish 127.0.0.1:5433:5432, when creating the container and update
  DATABASE_URL to use port 5433.
- **The container name is already in use:** inspect it with docker ps --all
  and start the existing container with docker start ruvie-postgres.
- **Connection refused:** check container logs and pg_isready, then confirm
  the host port in DATABASE_URL matches the published port.
- **Password authentication failed:** check .env against the password used
  when the volume was first initialized. Editing container environment
  variables does not reset an existing database password.




## F017 embedding connection cutover

Schedule a maintenance window and pause chat, uploads and the ingestion worker.
Back up PostgreSQL with your normal `pg_dump` procedure and verify the backup can
be restored to an isolated database. Back up the server's
`LLM_SETTINGS_ENCRYPTION_KEY` separately and securely; database ciphertext is
unreadable without that key. Never place plaintext provider credentials in backups
of operational instructions, screenshots or command history.

Review migration SQL and upgrade using the commands above. Migration 0013 creates
an unconfigured embedding singleton. It does not import environment variables or
chat credentials and does not change document revisions, vectors or reply policy.
Start the backend, sign in as an administrator and open System settings > AI
connections > Embedding model. Enter the provider URL and explicit key action,
load the embedding catalog, select `baai/bge-m3`, test the model and apply. Only
1024-dimensional cosine vectors are accepted. The catalog must expose
`/embeddings/models`; `/models` is not an embedding catalog.

Start the worker with the same database and encryption key, then reopen traffic.
New requests and claimed jobs read committed configuration without restart;
running operations keep their original connection through completion. No
`EMBEDDING_BASE_URL` or `EMBEDDING_API_KEY` fallback is available. Proxy and
local-origin permissions remain server settings and require process restart when
changed. Verify with a test document readable by the signed-in account.

To roll back, stop traffic and workers first, preserve a recoverable backup and
use the Alembic downgrade command with target `0012_organization_llm_settings`.
This drops only the embedding connection table, including its encrypted key.
It does not export plaintext credentials or restore environment configuration.
Run a compatible prior application version and explicitly configure its connection
using that version's instructions before reopening traffic. A subsequent upgrade
creates an empty singleton again. Do not downgrade a live process that expects
F017's table.

## F018 AI network cutover

Migration 0014 adds network_mode/proxy_url to both connection singletons.
Existing deployments remain **pending** until operator confirmation, rather than
silently taking the direct route. Migration 0015 initializes both routes to direct
only when the upgrade chain starts from a database with no Alembic revision.
An existing deployment with provider version 0 still requires cutover.
Migration 0015 also tightens the network-pair constraints without changing saved
routes, credentials or profiles. Upgrade to head; do not stop at 0014.
Alembic does not read the environment. Pending rows are not usable by
backend, worker or admin API.

1. Schedule maintenance; stop new chat/ingestion traffic, let active work
   finish, and stop **both** old backend and worker processes. Check that
   the old embedding proxy settings were consistent between both processes.
   Back up PostgreSQL and separately preserve credential encryption keys.
2. Upgrade to Alembic head as documented above. Do not reset the application
   database or modify already applied migration files.
3. In the original deployment environment with the old LLM_PROXY_URL and
   EMBEDDING_PROXY_URL still present, dry-run the operator CLI:

   ```powershell
   $env:PYTHONPATH = 'backend'
   .\.venv\Scripts\python.exe -B -m ruvie.network_settings_cli
   ```

   Output includes connection mode, expected version and pending status,
   but never a credential or internal proxy endpoint.
4. Confirm both versions and an active administrator identity. Example (replace
   both example versions and ID with those from the dry run):

   ```powershell
   .\.venv\Scripts\python.exe -B -m ruvie.network_settings_cli --confirm --actor-id "<admin-id>" --llm-version 2 --embedding-version 1
   ```

   Conversion checks authorization/versions and atomically updates both
   network routes with audit entries; any failure rolls back both. Configured
   rows increase version; version-0 rows remain unconfigured. Re-running
   after success never overwrites later admin edits.
5. Start the new backend and worker only after both rows are converted.
   Verify both forms and a disposable embedding job **from the worker**
   before reopening traffic. A backend-only verify does not establish that
   the worker can reach the proxy.
6. Remove both legacy proxy variables from deployment configuration.
   New operations use DB snapshots without process restart; in-flight
   operations keep their pinned route. Proxy failure never falls back to direct.

Direct means no app-selected proxy, not bypassing host VPN/TUN. Rollback requires
explicit old-version configuration and a recoverable DB backup; downgrading
does not recreate old proxy environment values.
