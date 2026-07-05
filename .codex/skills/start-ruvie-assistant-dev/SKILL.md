---
name: start-ruvie-assistant-dev
description: Start the Ruvie Assistant repository in local development mode on Windows inside Codex. Use when Codex needs to boot, restart, or verify this workspace's frontend and backend, especially when the normal frontend dev script fails because Pyodide fetching needs network access or when the backend rejects startup without WEBUI_SECRET_KEY.
---

# Start Ruvie Assistant Dev

Start this workspace in two separate long-lived sessions: backend first, then frontend. Prefer the repo-specific commands below over generic project scripts because this repository has two local quirks in Codex:

- `npm run dev` triggers `scripts/prepare-pyodide.js`, which tries to fetch remote assets and can fail in restricted environments.
- PowerShell expands `*` in `--forwarded-allow-ips "*"`, so the simplest reliable backend command for local dev is to omit that flag entirely.

## Quick Checks

Before starting anything:

1. Work from the repository root.
2. Confirm `node_modules` exists for the frontend and `.venv` exists for the backend.
3. Keep backend and frontend in separate persistent terminal sessions so one restart does not kill the other.

## Backend

If `.env` does not already define `WEBUI_SECRET_KEY`, add a long dev-only secret there before starting. If `backend/.webui_secret_key` exists, keep it aligned with the same value.

Start the backend with:

```powershell
.\.venv\Scripts\uvicorn.exe open_webui.main:app --app-dir backend --host 127.0.0.1 --port 8080 --reload
```

Treat `http://127.0.0.1:8080/health` as the backend readiness check.

Notes:

- A warning such as `No module named 'sentence_transformers'` is non-blocking if the health endpoint succeeds.
- If startup fails with a message about `WEBUI_SECRET_KEY`, repair the env value and retry.
- If Python dependencies are missing, install them into `.venv`, not into a global interpreter.
- If you specifically need `--forwarded-allow-ips *` for proxy testing, use PowerShell's stop-parsing form: `.\.venv\Scripts\uvicorn.exe --% open_webui.main:app --app-dir backend --host 127.0.0.1 --port 8080 --forwarded-allow-ips * --reload`.

## Frontend

Do not use `npm run dev` in this environment unless network access is confirmed and intentional. It runs a Pyodide fetch step first.

Start the frontend with:

```powershell
.\node_modules\.bin\vite.cmd dev --host 0.0.0.0
```

Treat `http://localhost:5173/` as the frontend readiness check.

Repo-specific reason: `src/lib/constants.ts` points the frontend to `http://<current-host>:8080` during dev, so the backend must already be listening on port `8080`.

## Verification

After both services are up:

```powershell
curl http://127.0.0.1:8080/health
curl -I http://localhost:5173/
```

Proceed only when the backend returns a healthy JSON response and the frontend returns an HTTP success status.

## Troubleshooting

Use these fixes first:

1. Frontend exits while fetching Pyodide: rerun with `.\node_modules\.bin\vite.cmd dev --host 0.0.0.0`.
2. Backend exits because `WEBUI_SECRET_KEY` is empty: set the value in `.env` and, if used, `backend/.webui_secret_key`.
3. Port `8080` or `5173` is busy: stop the stale process or restart the corresponding service cleanly.
4. Missing Python modules: install them into `.venv` and retry the backend.

## Fallback

If the backend command above stops working after upstream changes, try the repository's Windows helper at `backend/start_windows.bat`, but keep the direct `uvicorn` path as the first choice for Codex sessions in this workspace because it has been the most predictable here.
