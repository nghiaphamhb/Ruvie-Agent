# Ruvie Assistant

![Ruvie Assistant Banner](./banner.png)

Ruvie Assistant is a customized, self-hosted AI workspace based on Open WebUI. This fork keeps the core chat, RAG, tools, notes, channels, calendar, and automation flows, but the backend package now lives under `backend/ruvie`.

## Current Stack

- Frontend: SvelteKit, Vite, TypeScript.
- Backend: FastAPI in `backend/ruvie`.
- Database: SQLite by default at `backend/data/webui.db`; PostgreSQL is supported through `DATABASE_URL`.
- Static assets: served from `static/static`.
- UI languages: Vietnamese, Russian, and English (US) only.

## What This Repo Covers

- Chat UI and multi-model conversations.
- File upload, knowledge bases, and RAG.
- Tools, functions, skills, and external tool servers.
- Notes, channels, calendar, and automations.
- Admin screens for users, models, settings, analytics, and evaluations.
- PWA-friendly frontend and local-first workflows.

## Run Locally

Prereqs:

- Python 3.11+
- Node.js 18.13+

Backend:

```powershell
.\.venv\Scripts\uvicorn.exe ruvie.main:app --app-dir backend --host 127.0.0.1 --port 8080 --reload
```

Frontend:

```powershell
.\node_modules\.bin\vite.cmd dev --host 0.0.0.0
```

Open:

- Frontend: `http://localhost:5173`
- Backend API: `http://127.0.0.1:8080`

## Important Paths

- `backend/ruvie/main.py`
- `backend/ruvie/routers/*`
- `backend/ruvie/utils/middleware.py`
- `src/routes/+layout.svelte`
- `src/routes/(app)/+layout.svelte`
- `src/lib/components/chat/Chat.svelte`
- `src/lib/components/chat/MessageInput.svelte`
- `src/lib/i18n/index.ts`
- `src/lib/i18n/locales/languages.json`
- `docs/PROJECT_OVERVIEW.md`
- `docs/ARCHITECTURE.md`
- `docs/QUICK_SETUP.md`

## Notes For This Fork

- `backend/dev.sh` and `backend/start_windows.bat` are intentionally not part of the repo.
- `backend/start.sh` is the shell/container entrypoint.
- The frontend dev backend URL is hardcoded to port `8080` in `src/lib/constants.ts`.
- Do not delete `backend/data/webui.db` or other local DB files unless explicitly asked.
- If you change startup, branding, auth, database, architecture, or i18n, update the docs in `docs/`.
- Keep `src/lib/i18n/locales/languages.json` in sync with `src/lib/i18n/index.ts` and the language selector UI.
