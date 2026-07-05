# AGENTS.md

## Project Context

Ruvie Assistant is a self-hosted AI workspace based on Open WebUI. The backend package now lives under `backend/ruvie`; imports, startup commands, and docs should use `ruvie.*`, not `open_webui.*`.

Primary stack:

- Frontend: SvelteKit, Vite, TypeScript, Tailwind-style utility classes.
- Backend: FastAPI application under `backend/ruvie`.
- Database: default local SQLite database under `backend/data/webui.db`, with SQLAlchemy support for other database URLs.
- Static assets: served from `static/static` through routes referenced as `/static/...`.
- i18n: current exposed UI languages are `vi-VN`, `ru-RU`, and `en-US`. Keep `src/lib/i18n/locales/languages.json`, `src/lib/i18n/index.ts`, and `src/lib/components/chat/Settings/General.svelte` aligned if the list changes.
- Local docs: project documentation lives in `docs/`.

Important documentation to read first:

- `docs/PROJECT_OVERVIEW.md`
- `docs/ARCHITECTURE.md`
- `docs/USE_CASES.md`
- `docs/QUICK_SETUP.md`
- `docs/REINSTALL.md`
- `docs/CODE_MAP.md`
- `docs/CHANGE_GUIDE.md`
- `docs/CODEX_HANDOFF.md`

## How To Run In Dev Mode

Prefer direct backend/frontend commands instead of `npm run dev` when pyodide downloads or network setup are flaky.

Do not recreate `backend/dev.sh` or `backend/start_windows.bat` unless the user explicitly asks.

Backend:

```powershell
.\.venv\Scripts\uvicorn.exe ruvie.main:app --app-dir backend --host 127.0.0.1 --port 8080 --reload
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
- `backend/start.sh` is the shell/container entrypoint; no Windows batch or `dev.sh` helper is kept in this repo.
- If ports are occupied, inspect ports `8080` and `5173` before starting new instances.
- If forwarded proxy testing is needed in PowerShell, use `--%` before `ruvie.main:app` to prevent `*` from expanding.
- Keep the locale list and selector in sync when changing supported UI languages.

## Branding / UI State

The app uses these generated/replaced logo assets:

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

- `backend/ruvie/main.py`

Core backend routers:

- `backend/ruvie/routers/auths.py`
- `backend/ruvie/routers/users.py`
- `backend/ruvie/routers/chats.py`
- `backend/ruvie/routers/models.py`
- `backend/ruvie/routers/files.py`
- `backend/ruvie/routers/knowledge.py`
- `backend/ruvie/routers/tools.py`
- `backend/ruvie/routers/functions.py`
- `backend/ruvie/routers/skills.py`

Main frontend entries:

- `src/app.html`
- `src/routes/+layout.svelte`
- `src/routes/(app)/+layout.svelte`
- `src/routes/(app)/+page.svelte`
- `src/lib/components/chat/Chat.svelte`
- `src/lib/components/chat/MessageInput.svelte`

I18n and locale control:

- `src/lib/i18n/index.ts`
- `src/lib/i18n/locales/languages.json`
- `src/lib/components/chat/Settings/General.svelte`

Admin/user access areas:

- `src/routes/(app)/admin/*`
- `src/lib/components/admin/*`
- `backend/ruvie/routers/users.py`
- `backend/ruvie/routers/auths.py`

## Working Rules For Future Agents

- Do not revert user changes unless explicitly requested.
- Do not delete local data files.
- Use `rg` for search when available.
- Use `apply_patch` for manual file edits.
- Keep documentation in `docs/` up to date when changing startup, branding, auth, database, architecture, or i18n.
- When changing UI branding, check splash, favicon, login, sidebar, and PWA manifest together.
- When changing supported UI languages, update `src/lib/i18n/locales/languages.json`, `src/lib/i18n/index.ts`, and the selector UI together.
- When moving the project directory, expect absolute paths in generated logs or old handoff notes to need updating.
- Legacy Open WebUI literals still exist in some package metadata and historical docs; do not rename them blindly unless the user asks.

## Known Gaps / Unknowns

- The most recent dev-server restart was interrupted by the user while restarting. Verify whether backend/frontend are running before assuming dev mode is active.
- Some docs are based on source inspection, not full end-to-end verification of every feature.
