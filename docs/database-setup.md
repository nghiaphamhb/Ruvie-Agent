# Ruvie Agent database setup

[Back to README](../README.md).

## Install and start PostgreSQL with Docker

Run the following PowerShell commands from the repository root. The backend,
frontend, and ingestion worker run on the host; Docker runs the database.

On Windows, install [Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/)
with the WSL 2 backend, start it, and use Linux containers. Open a new terminal
after installation and confirm that both the Docker client and server respond:

~~~powershell
docker version
~~~

Use the [pgvector image](https://github.com/pgvector/pgvector#docker), which
includes PostgreSQL and the vector extension. This example uses the same
PostgreSQL 16 image as the end-to-end tests. Replace the password placeholder
before running the command, and use the same password in the repository-root
.env file.

~~~powershell
docker pull pgvector/pgvector:0.8.6-pg16-bookworm
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

Confirm the target database before applying migrations. The Docker image
provides pgvector; the ingestion schema migration enables the vector
extension. Verify it after the upgrade:

~~~powershell
docker exec ruvie-postgres psql -U ruvie -d ruvie -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
~~~

## Operate the database

Inspect the container and recent logs:

~~~powershell
docker ps --all --filter name=ruvie-postgres
docker logs --tail 100 ruvie-postgres
~~~

Stop, start, or restart the existing container as needed. Start the database
and wait for readiness before starting the backend or worker:

~~~powershell
docker stop ruvie-postgres
docker start ruvie-postgres
docker restart ruvie-postgres
~~~

Open an interactive SQL session (\q exits):

~~~powershell
docker exec -it ruvie-postgres psql -U ruvie -d ruvie
~~~

Run docker run only when creating the container. Changing POSTGRES_USER,
POSTGRES_PASSWORD, or POSTGRES_DB on a replacement container does not change
an already initialized volume; see the
[PostgreSQL image documentation](https://hub.docker.com/_/postgres).
Keep ruvie-postgres-data when replacing the container and reuse the same
mount. Removing that volume permanently deletes the database.

## Back up and restore

Create a PostgreSQL custom-format backup and copy it to the ignored local
logs/ directory. Use a new filename for each backup:

~~~powershell
New-Item -ItemType Directory -Force -Path logs/database-backups | Out-Null
docker exec ruvie-postgres pg_dump -U ruvie -d ruvie -Fc -f /tmp/ruvie.dump
docker cp ruvie-postgres:/tmp/ruvie.dump ./logs/database-backups/ruvie.dump
~~~

Copy important backups to private storage outside this machine. Database
backups do not include uploaded blobs; back up private blob storage separately.

To verify a backup, restore it into a new, empty database. Choose an unused
database name each time; the following leaves the running ruvie database
untouched:

~~~powershell
docker cp ./logs/database-backups/ruvie.dump ruvie-postgres:/tmp/ruvie-restore.dump
docker exec ruvie-postgres createdb -U ruvie ruvie_restore
docker exec ruvie-postgres pg_restore -U ruvie -d ruvie_restore --exit-on-error /tmp/ruvie-restore.dump
docker exec ruvie-postgres psql -U ruvie -d ruvie_restore -c "SELECT version_num FROM alembic_version;"
~~~

For recovery, stop the backend and worker before switching DATABASE_URL to
the restored database. Run Alembic's current and upgrade head commands
against that target before restarting the application.

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

