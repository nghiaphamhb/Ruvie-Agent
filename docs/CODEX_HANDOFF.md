# Codex Handoff

## Purpose

This file preserves working context for future Codex sessions after the project is moved to a new location.

Repository at the time of this handoff:

- Old/current path: `E:/Desktop/GitHub Repository/Ruvie-Assistant`
- Project type: customized Open WebUI-based assistant app
- Main app name/brand in current customization: Ruvie

## What Was Done In Recent Sessions

### 1. Project documentation created

The following documentation files were created under `docs/`:

- `docs/PROJECT_OVERVIEW.md`
- `docs/ARCHITECTURE.md`
- `docs/USE_CASES.md`
- `docs/QUICK_SETUP.md`
- `docs/REINSTALL.md`
- `docs/CODE_MAP.md`
- `docs/CHANGE_GUIDE.md`

These files summarize:

- What the project does.
- Main users and workflows.
- Frontend/backend architecture.
- Main use cases and related files.
- Setup and dev commands.
- File/module map.
- Change guide and technical risks.

### 2. Admin/user database state fixed

The local database had a duplicate/admin-access issue. The current expected state is:

- Admin email: `phamdangtrungnghia@gmail.com`
- Database backup before the fix: `backend/data/webui.db.backup-before-admin-fix-20260704`
- Main database: `backend/data/webui.db`

Important caution:

- Do not delete or reset `backend/data/webui.db`.
- Do not overwrite `backend/data` when moving the project unless the intention is to lose local users/chats/settings.

### 3. Dev startup skill created

A local Codex skill was created to remember how to start this project:

- `.codex/skills/start-ruvie-assistant-dev/SKILL.md`

Use that skill or the commands in `AGENTS.md` when a future session asks to start dev mode.

### 4. Logo assets replaced

User-provided logo source files:

- `E:/Desktop/GitHub Repository/ruvie-asesst-old/light-mode.png`
- `E:/Desktop/GitHub Repository/ruvie-asesst-old/dark-mode.png`

Generated app assets:

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

Backup of previous assets:

- `static/static-logo-backup-before-ruvie/`
- `static/static-logo-backup-before-ruvie/refresh-20260704/`

Implementation detail:

- `logo.png` preserves the full square source image used by the app manifest metadata.
- Full square logo images are used for splash screens.
- Cropped `RV` mark is used for small icons so favicon/sidebar remain readable.
- `favicon.svg` was regenerated as an SVG wrapper embedding a PNG rendition; it is valid for browser use but is not a true vector reconstruction.

Logo references in code:

- `src/app.html`
- `src/routes/auth/+page.svelte`
- `src/lib/components/layout/Sidebar.svelte`
- `static/static/site.webmanifest`

Branding/background sync note:

- Dark mode logo and splash assets now use the same navy background tone as the app shell (`#0f172a`).
- The shared `theme-paper-bg` surface class in `src/app.css` keeps splash and auth background styling aligned with the refreshed brand background.
- Sidebar and chat containers now reuse `theme-paper-bg` so the main surfaces stay visually consistent.
- Chat model avatars now use circular theme-colored badges instead of square tiles, which keeps the logo treatment consistent across placeholder, model picker, and messages.
- New-chat and assistant avatars now use a dedicated circular brand badge instead of the model-image fallback route, which avoids the square white fallback tile in dark mode.

### 5. Dev restart was attempted but interrupted

The user requested logo replacement and dev-mode restart. Logo replacement completed. Dev restart was attempted, but the turn was interrupted while starting backend/frontend with separate log files.

Do not assume dev servers are currently running. Check ports first:

```powershell
Get-NetTCPConnection -LocalPort 8080,5173 -ErrorAction SilentlyContinue
```

## Recommended Dev Commands

Backend:

```powershell
.\.venv\Scripts\uvicorn.exe ruvie.main:app --app-dir backend --host 127.0.0.1 --port 8080 --reload
```

Frontend:

```powershell
.\node_modules\.bin\vite.cmd dev --host 0.0.0.0
```

If PowerShell proxy testing needs `--forwarded-allow-ips *`, use:

```powershell
.\.venv\Scripts\uvicorn.exe --% ruvie.main:app --app-dir backend --host 127.0.0.1 --port 8080 --forwarded-allow-ips * --reload
```

Avoid `npm run dev` if it triggers `scripts/prepare-pyodide.js` and network-sensitive dependency download steps. Direct Vite startup is usually faster for this local setup.

## Important Files And Directories

Frontend:

- `src/app.html`
- `src/routes/+layout.svelte`
- `src/routes/(app)/+layout.svelte`
- `src/routes/(app)/+page.svelte`
- `src/routes/auth/+page.svelte`
- `src/lib/components/chat/Chat.svelte`
- `src/lib/components/chat/MessageInput.svelte`
- `src/lib/components/layout/Sidebar.svelte`
- `src/lib/apis/*`
- `src/lib/stores/index.ts`
- `src/lib/constants.ts`

Backend:

- `backend/ruvie/main.py`
- `backend/ruvie/env.py`
- `backend/ruvie/config.py`
- `backend/ruvie/internal/db.py`
- `backend/ruvie/routers/*`
- `backend/ruvie/models/*`
- `backend/ruvie/utils/middleware.py`
- `backend/ruvie/storage/provider.py`

Local data:

- `backend/data/webui.db`
- `backend/data/uploads/`
- `backend/data/cache/`
- `backend/data/vector_db/`

Static branding:

- `static/static/*`
- `static/static-logo-backup-before-ruvie/`

## After Moving The Project

Run this checklist:

1. Confirm `.venv` still works from the new path.
2. Confirm `node_modules` still works from the new path.
3. Confirm `backend/data/webui.db` moved with the repository.
4. Check if any logs or docs still mention the old absolute path.
5. Start backend on port `8080`.
6. Start frontend on port `5173`.
7. Open the frontend and verify the Ruvie logo appears on splash, login/sidebar, and browser tab.
8. Log in with the admin account and verify pending-user/admin behavior.

## Useful Verification Commands

Check assets:

```powershell
Get-ChildItem -LiteralPath 'static\static' | Where-Object { $_.Name -match 'favicon|splash|apple-touch|web-app-manifest|logo' } | Select-Object Name,Length
```

Check dev ports:

```powershell
Get-NetTCPConnection -LocalPort 8080,5173 -ErrorAction SilentlyContinue
```

Check backend health after startup:

```powershell
Invoke-WebRequest http://127.0.0.1:8080/health
```

Check frontend:

```powershell
Invoke-WebRequest http://127.0.0.1:5173
```

## Current Assumptions / Unknowns

- This handoff assumes the local database fix remains present in `backend/data/webui.db`.
- This handoff assumes the user wants to preserve local data, logo assets, docs, and Codex skill when moving the project.
- The dev server was not confirmed running after logo replacement because the user interrupted the restart step.
- The external logo source directory may not move with this repository unless copied separately.
