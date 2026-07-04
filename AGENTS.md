# AGENTS.md

## Project Context

This repository is `Ruvie-Assistant`, a customized/self-hosted Open WebUI-based AI assistant workspace.

Primary stack:

- Frontend: SvelteKit, Vite, TypeScript, Tailwind-style utility classes.
- Backend: FastAPI application under `backend/open_webui`.
- Database: default local SQLite database under `backend/data/webui.db`, with SQLAlchemy support for other database URLs.
- Static assets: served from `static/static` through routes referenced as `/static/...`.
- Local docs: project documentation lives in `docs/`.

Important documentation to read first:

- `docs/PROJECT_OVERVIEW.md`
- `docs/ARCHITECTURE.md`
- `docs/USE_CASES.md`
- `docs/SETUP_AND_RUN.md`
- `docs/REINSTALL.md`
- `docs/CODE_MAP.md`
- `docs/CHANGE_GUIDE.md`
- `docs/CODEX_HANDOFF.md`

## How To Run In Dev Mode

Prefer direct backend/frontend commands instead of `npm run dev` when pyodide downloads or network setup are flaky.

Backend:

```powershell
.\.venv\Scripts\uvicorn.exe open_webui.main:app --app-dir backend --host 127.0.0.1 --port 8080 --forwarded-allow-ips "*" --reload
```

Frontend:

```powershell
.\node_modules\.bin\vite.cmd dev --host 0.0.0.0
```

Expected local URLs:

- Backend API: `http://127.0.0.1:8080`
- Frontend dev UI: usually `http://localhost:5173`

Notes:

- `src/lib/constants.ts` points the frontend dev backend URL at port `8080`.
- A local Codex startup skill was created earlier at `.codex/skills/start-ruvie-assistant-dev/SKILL.md`.
- If ports are occupied, inspect ports `8080` and `5173` before starting new instances.

## Logo / Branding State

The app logo was replaced using source images from:

- `E:/Desktop/GitHub Repository/ruvie-asesst-old/light-mode.png`
- `E:/Desktop/GitHub Repository/ruvie-asesst-old/dark-mode.png`

Generated/replaced logo assets:

- `static/static/favicon.png`
- `static/static/favicon-dark.png`
- `static/static/favicon-96x96.png`
- `static/static/favicon.ico`
- `static/static/favicon.svg`
- `static/static/apple-touch-icon.png`
- `static/static/logo.png`
- `static/static/splash.png`
- `static/static/splash-dark.png`
- `static/static/web-app-manifest-192x192.png`
- `static/static/web-app-manifest-512x512.png`

Backup of previous logo assets:

- `static/static-logo-backup-before-ruvie/`

Logo usage locations:

- `src/app.html` uses splash, favicon, manifest, apple-touch icon.
- `src/routes/auth/+page.svelte` uses `/static/favicon.png` and `/static/favicon-dark.png`.
- `src/lib/components/layout/Sidebar.svelte` uses `/static/favicon.png`.
- `static/static/site.webmanifest` uses web-app manifest icons.

## Admin / Database Context

Earlier local database maintenance was performed:

- Backup created: `backend/data/webui.db.backup-before-admin-fix-20260704`
- Admin email configured: `phamdangtrungnghia@gmail.com`
- One duplicate user entry was removed.
- The retained user id was promoted/kept as admin.

Be careful with:

- `backend/data/webui.db`
- `backend/data/*.db*`
- any user/auth migration scripts

Do not reset or delete local database files unless explicitly requested.

## Code Areas

Main backend entry:

- `backend/open_webui/main.py`

Core backend routers:

- `backend/open_webui/routers/auths.py`
- `backend/open_webui/routers/users.py`
- `backend/open_webui/routers/chats.py`
- `backend/open_webui/routers/models.py`
- `backend/open_webui/routers/files.py`
- `backend/open_webui/routers/knowledge.py`
- `backend/open_webui/routers/tools.py`
- `backend/open_webui/routers/functions.py`
- `backend/open_webui/routers/skills.py`

Main frontend entries:

- `src/app.html`
- `src/routes/+layout.svelte`
- `src/routes/(app)/+layout.svelte`
- `src/routes/(app)/+page.svelte`
- `src/lib/components/chat/Chat.svelte`
- `src/lib/components/chat/MessageInput.svelte`

Admin/user access areas:

- `src/routes/(app)/admin/*`
- `src/lib/components/admin/*`
- `backend/open_webui/routers/users.py`
- `backend/open_webui/routers/auths.py`

## Working Rules For Future Agents

- Do not revert user changes unless explicitly requested.
- Do not delete local data files.
- Use `rg` for search when available.
- Use `apply_patch` for manual file edits.
- Keep documentation in `docs/` up to date when changing startup, branding, auth, database, or architecture.
- When changing UI branding, check splash, favicon, login, sidebar, and PWA manifest together.
- When moving the project directory, expect absolute paths in generated logs or old handoff notes to need updating.

## Known Gaps / Unknowns

- The logo source files currently live outside this repository in `E:/Desktop/GitHub Repository/ruvie-asesst-old/`; if the project is moved to another machine, copy those source logo files too if future regeneration is needed.
- The most recent dev-server restart was interrupted by the user while restarting. Verify whether backend/frontend are running before assuming dev mode is active.
- Some docs are based on source inspection, not full end-to-end verification of every feature.
