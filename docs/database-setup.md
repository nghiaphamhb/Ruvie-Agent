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



