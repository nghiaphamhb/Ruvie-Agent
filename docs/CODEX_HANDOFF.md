# Codex Handoff

## Purpose

This file preserves working context for future Codex sessions, especially when the user changes ChatGPT/Codex accounts. Repository files and Git state are the source of truth; do not rely on account chat history being available.

Repository at the time of this handoff:

- Current path: `D:/Github Repository/Ruvie-Assistant`
- Project type: customized Open WebUI-based assistant app
- Main app name/brand in current customization: Ruvie

## Current Snapshot — 2026-07-28

### Git state

- Branch: `dev-frontend`
- HEAD: `8445ff6a96fe6ff618d26002cc1025191e844cb3`
- Latest commit: `8445ff6 refactor: reset config based project`
- There are no staged changes.
- The working tree has substantial pre-existing, uncommitted work. Do not discard, reset, clean, or overwrite it.

Tracked changes:

- `backend/ruvie/routers/chats.py`
- `package-lock.json`
- `package.json`
- `src/lib/apis/chats/index.ts`
- `src/lib/components/chat/Settings/SyncStatsModal.svelte` (deleted; backup exists under `archived/`)
- `src/lib/constants.ts`
- `src/routes/+layout.svelte`
- `static/favicon.png`
- `static/opensearch.xml` (deleted; backup exists under `archived/`)

Untracked paths:

- `CHANGELOG.md`
- `archived/`
- `conversation_history/`
- `docs/DESTINATION.md`
- `tmp/`

Treat `conversation_history/` as potentially sensitive account/chat data. Review it before copying, uploading, or committing it. Treat `tmp/` as generated working material until its purpose is confirmed.

### Work in progress inferred from the diff

- User-facing `Open WebUI` branding has been replaced with `Ruvie`; upstream package IDs,
  compatibility identifiers, repository URLs, and infrastructure prefixes remain unchanged.
- Archive the Sync Usage Stats feature across backend routes, frontend API helpers, modal wiring, and community window-message handling.
- Disable desktop/Electron-only layout hooks for the browser-focused build.
- Archive OpenSearch integration files.
- Add `openwiki` as a frontend development dependency.
- Add the enterprise-oriented product direction in `docs/DESTINATION.md`.

These changes have not been validated or committed in the current snapshot. Confirm their intended scope with the user before broad cleanup or refactoring.

### Local environment

- `.env` exists. Do not print or commit its secrets; transfer required values through an approved secure channel.
- `.venv/Scripts/uvicorn.exe` exists.
- `node_modules/.bin/vite.cmd` exists.
- Neither port `8080` nor `5173` was listening when this snapshot was created.
- The dev servers are not assumed to be running.

### Signup behavior updated — 2026-07-28

- New-user signup is enabled in the current database.
- New accounts receive the configured `pending` role and still require admin approval.
- Creating the first admin no longer automatically disables future signup.
- Database backup before enabling signup: `backend/data/webui.db.backup-before-enable-signup-20260728-232847`.
- Verification: public config returned `enable_signup=true`; an invalid-email signup probe reached validation and returned HTTP 400 instead of the previous access-prohibited HTTP 403.

### Documentation drift already identified

- `docs/REINSTALL.md` does not exist and was removed from the required-reading list in `AGENTS.md`.
- Some older docs still mention removed helpers such as `backend/start_windows.bat` and `backend/dev.sh`. The supported backend entrypoint is `ruvie.main:app`; use the commands in `AGENTS.md`.
- Historical notes below may contain the old `E:/Desktop/...` workspace path. The current repository path is the `D:/Github Repository/...` path above.

### Next session bootstrap

Start a new Codex session in this repository with:

> Read `AGENTS.md` and `docs/CODEX_HANDOFF.md` first. Inspect `git status` and the current diff without reverting anything. Treat the existing working tree as user-owned work. Summarize the intended Ruvie branding and Sync Usage Stats archival changes, then ask for or continue the next concrete task.

Recommended first checks:

```powershell
git status --short --branch
git diff --stat
Get-NetTCPConnection -LocalPort 8080,5173 -ErrorAction SilentlyContinue
```

## What Was Done In Recent Sessions

### 1. Project documentation created

The following documentation files were created under `docs/`:

- `docs/PROJECT_OVERVIEW.md`
- `docs/ARCHITECTURE.md`
- `docs/USE_CASES.md`
- `docs/QUICK_SETUP.md`
- `docs/CODE_MAP.md`
- `docs/CHANGE_GUIDE.md`

`docs/REINSTALL.md` was referenced historically but is not present in the current repository.

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

## Auth Landing Redesign — 2026-07-29

- `src/routes/auth/+page.svelte` now presents Ruvie as an enterprise document workspace rather than a generic AI chat product.
- The visual system uses navy, slate, white, and blue in place of the previous green/beige palette.
- The landing copy explains the document workflow: company files, permission-aware knowledge, and answers linked to sources.
- Short desktop viewports now use compact spacing and type; the page scrolls instead of clipping content.
- Sign-in, account-request, OAuth, and administrator-approval behavior remain unchanged.
- The new landing copy is translated in the `en-US`, `vi-VN`, and `ru-RU` locale files.
- Remaining Open WebUI references are categorized in `docs/OPEN_WEBUI_LEGACY_AUDIT.md`.
