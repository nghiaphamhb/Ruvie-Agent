---
name: dev-mode-toggle
description: Toggle the Ruvie Agent development app. Start backend, frontend, and worker when stopped; stop only this app's processes and ports when running.
---

# Dev mode toggle

Work from the active repository root. Read `README.md` (especially **Run locally**) and `AGENTS.md` before acting.

1. The app must end each invocation in exactly one of two states: **fully on** (every app component required by `README.md` is running and verified) or **fully off** (all those app components are stopped and their app-owned ports are free). Never leave a partial state intentionally.
2. Inspect all app components from `README.md`, including backend, frontend, ingestion worker, and any other app-owned services. Classify as fully on only if every required component is healthy; classify as fully off only if none is running. If fully on, use **Stop mode**. If fully off, use **Start mode**. If partially running or unhealthy, first stop and verify all app components, then use **Start mode** to reach fully on. If you cannot verify the intermediate fully-off state, do not start more components; report that cleanup failed and identify what remains.

## Start mode

1. Remind the user to start their existing PostgreSQL Docker container. Use the read-only `docker ps` check from `README.md` to confirm it is running. If it is not running, tell the user which prerequisite is missing and stop; do not create a container, query the dev database directly, or run migrations.
2. Check that `.env`, the Python virtual environment, and frontend dependencies exist without displaying secrets. Report missing setup instead of inventing credentials or changing provider settings.
3. Reuse healthy Ruvie processes; never start a second backend on port 8000. On Windows, an old Uvicorn `spawn_main` worker can keep port 8000 after its parent stops: identify the Ruvie process tree before stopping it, and verify the port is clear. Leave unrelated processes alone.
4. Start the backend, Vite frontend, and ingestion worker using the working directories and commands in `README.md`. If detached with `Start-Process`, use `-WindowStyle Hidden`, separate logs under `logs/dev/`, and one backend without `--reload`. Keep the frontend on an origin allowed by `AUTH_ALLOWED_ORIGINS` (normally port 5173).
5. Verify that one backend listens on port 8000, `/health` and `/ready` return `status: ok`, the frontend serves its URL, and the ingestion worker stays running. Report URLs, process identifiers, log locations, and any missing component. These health endpoints do not prove database or provider calls; perform login, upload, or chat checks only when requested.
6. If any start step fails or any required component fails verification, immediately stop every app component started or left running during this invocation, including child processes. Verify all app-owned ports are free and no worker remains. The final state must be fully on or fully off; report an explicit failure if fully off cannot be verified. Do not claim success with a partially running app.
7. Report the exact command line actually used to start each component (backend, frontend, worker, and any additional required service), its working directory, and result or PID. Include verification commands and outcomes in copyable code blocks. If a process was started through `Start-Process`, show its executable and arguments as a runnable command, and say it was detached. Mark skipped commands/checks. Never report a planned command as executed; redact secret-bearing arguments or output.

## Stop mode

1. Identify processes by actual command lines and parent/child relationships, not by port number alone. Stop all app components listed in `README.md`, including the Ruvie backend (and Uvicorn child processes), Vite frontend, and ingestion worker. Do not stop PostgreSQL/Docker or unrelated processes unless README explicitly identifies them as app-owned.
2. Verify every app component is stopped, ports owned by the app are free, and no app worker remains. If a port is held by an unrelated process, do not kill it; report that fully off could not be verified. If any app process remains, continue identifying and stopping only that app process tree, then verify again.
3. Keep the response concise: report the final state as fully off only when all checks pass; otherwise identify the remaining component/port and say the state is not fully off. Do not include a command transcript for Stop mode.

Never print `.env`, passwords, API keys, authorization headers, private documents, or provider response bodies. Do not run the legacy app in `references/`.
