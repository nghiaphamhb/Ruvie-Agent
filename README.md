# Ruvie Agent

Ruvie Agent lets project members upload PDF or text files, retrieve authorized
passages, and chat with citations. PostgreSQL with pgvector stores application
data and vectors; uploaded files stay in private blob storage.

## Requirements

- Python 3.11+ (installed directly or managed by uv)
- Node.js and npm
- PostgreSQL with the pgvector extension
- Docker Desktop with Linux containers (for a Docker database)

## Setup

Run commands in PowerShell from the repository root. Choose one backend method.

### Option 1: Install Python

Install [Python 3.11+](https://www.python.org/downloads/windows/) with
**Add python.exe to PATH** enabled. Reopen PowerShell, then run:

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
~~~

### Option 2: Use uv

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if missing:

~~~powershell
winget install --id astral-sh.uv -e
~~~

Reopen PowerShell in the repository root, then run. uv downloads Python if
needed; no separate Python installation is required.

~~~powershell
uv venv --python 3.11 .venv
uv pip install --python .\.venv\Scripts\python.exe -r backend\requirements.txt
~~~

### Frontend and configuration

Install frontend dependencies:

~~~powershell
Set-Location frontend
npm install
Set-Location ..
~~~

Create `.env` and set `DATABASE_URL`, the embedding profile/provider,
`AUTH_ALLOWED_ORIGINS` for the browser origin, and optional `LLM_*` server
fallback settings. Keep credentials local. The vector schema requires 1024-dimensional cosine
embeddings.

~~~powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
~~~

## Database

For PostgreSQL setup, migrations, database operations, backups and
troubleshooting, see [Database setup](docs/database-setup.md).

### Provision a user password

There is no public signup. Provision a password for an existing user:

~~~powershell
Set-Location backend
..\.venv\Scripts\python.exe -m ruvie.password_cli user@example.com
Set-Location ..
~~~

The command prompts for the password without displaying it.

## Run locally

Start each process in a separate terminal.

Backend, from the repository root:

~~~powershell
.\.venv\Scripts\uvicorn.exe ruvie.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
~~~

Frontend:

~~~powershell
Set-Location frontend
npm run dev
~~~

In another terminal, start the document ingestion worker:

~~~powershell
Set-Location backend
..\.venv\Scripts\python.exe -m ruvie.worker_cli
~~~

Check the backend at <http://127.0.0.1:8000/health>. Vite prints the frontend
URL when it starts.

## LLM connection and model selection

The provider must expose OpenAI-compatible `GET /models` and
`POST /chat/completions`. Enter its Base URL, for example
`https://provider.example.com/v1`, in **Kết nối LLM**. Add a key only when the
provider requires one. Click **Kết nối**, then choose one model in the Chat header. Search by name or ID. Use arrows and Enter to choose; Escape
closes the list. There is no multi-model chat.

Settings and the selected model are stored per account in PostgreSQL. Reload
or log in again to restore them. Chat sends only the message and model ID;
the backend supplies the saved URL/key and checks the current provider catalog.
If a model disappears, choose another model. A failed connection or model save
keeps the previous saved settings. Errors never expose provider keys.

For a server fallback, set `LLM_BASE_URL`. `LLM_MODEL` and `LLM_API_KEY` are
optional. With no saved preference, the backend uses the configured model if
available, otherwise the first returned model. With all `LLM_*` empty, connect
through the UI before chatting. **Gỡ kết nối** removes personal settings and
restores the server fallback. A failed personal provider reports an error; it
does not switch providers automatically.

Local HTTP/private endpoints require an exact origin in the server allowlist:

~~~dotenv
LLM_ALLOWED_LOCAL_ORIGINS=http://localhost:11434,http://127.0.0.1:11434
~~~

Then enter `http://localhost:11434/v1` in the form. The allowlist excludes the
path. `localhost` refers to the machine running the backend. Scheme, host and
port must match. The browser cannot change this allowlist. Public HTTPS needs
no allowlist entry; redirects and prohibited network destinations are blocked.

If a provider rejects the direct network connection but works through Hiddify,
set an explicit server proxy in the local `.env` and restart the backend:

~~~dotenv
LLM_PROXY_URL=socks5://127.0.0.1:12334
~~~

Use Hiddify's actual SOCKS5 or mixed port on the backend machine and keep it
running. Install the backend requirements again if this environment predates
SOCKS support (`httpx[socks]`). Empty `LLM_PROXY_URL` keeps direct connections.
HTTP/HTTPS proxy URLs and proxy credentials are not supported. Model discovery
and chat use this same server setting; the browser cannot supply a proxy.
LLM requests still ignore environment/system proxies and keep TLS verification,
redirect rejection, destination checks and DNS pinning. The proxy receives the
checked numeric IP, while TLS and HTTP Host use the original provider hostname.
There is no direct fallback if the configured proxy fails. Local providers still
need `LLM_ALLOWED_LOCAL_ORIGINS`; this proxy does not grant private-network access.

Legacy `references/backend/ruvie/routers/openai.py::send_get_request` uses
`aiohttp.ClientSession(trust_env=True)`. Its network behavior informed this fix;
the active guarded HTTPX adapter was reused instead of porting legacy runtime
code or environment-proxy trust.

Leave the key field empty to keep a saved personal key at the same URL.
**Xóa key đã lưu** explicitly removes it on the next save. Changing the URL
clears the typed key and does not reuse the previous provider's key. Saved
keys never refill the field and are not stored in localStorage.

Manual check with a provisioned account and a ready document:

1. Connect a provider and select model B. Send a question; inspect the citations.
2. Reload and log in again. Confirm B remains selected and the key field is empty.
3. Use another account. Confirm its connection, model and citations are separate.
4. Try an invalid key/URL or remove B at the provider. Confirm a safe error,
   no silent switch, and the ability to retry or choose a valid model.
5. Remove the personal connection. Confirm the server fallback, if configured.

The selector adapts search, tick and keyboard behavior from
`references/src/lib/components/chat/ModelSelector/Selector.svelte` and the
single-choice persistence idea from
`references/src/lib/components/chat/ModelSelector.svelte`. It uses Svelte 5,
plain search and the browser popover API. It uses active cookie/CSRF APIs and
PostgreSQL instead of legacy dependencies or browser token storage.

## Desktop UI and customization

The active frontend selectively ports the legacy layout in `references/`.
It has a persistent desktop sidebar with **Chat**, **Tải tài liệu** and
**Kết nối LLM**, plus the account name and logout. Chat opens by default.
There is no mobile menu or drawer. Panels stay mounted during navigation,
so drafts, selected files, uploads and streams keep their state. Hidden panels
cannot receive keyboard focus. Model metadata loads even before opening LLM.

Each chat question is independent. Chat history and drafts exist only in the
current page and disappear on reload. Saved connections and model choices
come back from the backend. Sources appear only after a completed response;
expand them to inspect revision/chunk metadata. There is no file preview or
content download. Upload supports the current PDF/UTF-8 contract (25 MiB),
polls every two seconds for up to five minutes, then offers status refresh.
The ingestion job continues on the server after that deadline. Logout or a
protected API's 401 clears account data and invalidates old responses.

Edit `frontend/src/app.css` variables for the shared theme:

| Variables | What changes |
| --- | --- |
| `--paper`, `--paper-gradient`, `--surface`, `--soft` | Page/sidebar background, panels and selected rows |
| `--ink`, `--muted`, `--border`, `--accent`, `--accent-hover` | Text, borders, focus and primary actions |
| `--error`, `--error-bg`, `--error-border` | Safe error presentation |
| `--font-family`, `--font-size` | System font stack and base text size |
| `--space`, `--radius` | Shared region spacing and corners |
| `--sidebar-width`, `--content-width`, `--form-width` | Desktop navigation, chat and form widths |

Change each component's scoped styles for local layout. `App.svelte` keeps
session, API, polling and stream orchestration. Presentational components do
not implement document authorization or provider requests. Keep the active
cookie/CSRF contract when customizing; there is no runtime import from legacy.

| Active file | Legacy source and selected port |
| --- | --- |
| `AppNavigation.svelte` | `layout/Sidebar.svelte`: brand, rounded navigation rows and account footer |
| `App.svelte` | `chat/Navbar.svelte`: compact header and model placement |
| `ChatConversation.svelte` | `chat/Placeholder.svelte`: centered welcome; active text conversation reused |
| `ChatComposer.svelte` | `chat/MessageInput.svelte`: round arrow-up send control; active textarea/IME retained |
| `CitationSources.svelte` | `chat/Messages/Citations.svelte`: source-count pill and numbered names; native details show active citation metadata |
| `DocumentUploadPanel.svelte` | `common/FileItem.svelte`: file card, document glyph, name/type/size and loading; no content link |
| `LoginForm.svelte` | `routes/auth/+page.svelte`: compact labeled login form; no signup or browser token |
| `LlmConnectionForm.svelte` | `AddConnectionModal.svelte` and `chat/Settings/Connections.svelte`: URL/key form appearance; active F006 save/key semantics retained |
| `ModelSelector.svelte` | `chat/ModelSelector/Selector.svelte`: rounded search/tick rows; active native popover retained |
| `app.css` | `references/src/app.css`: light paper background; local variables and system fonts |

Component names in this table are under `frontend/src/lib/components/`.
Legacy component paths are under `references/src/lib/components/`, except the
auth route and stylesheet. Legacy stores, routing, authentication, provider
calls, file URLs and unrelated controls were excluded. No UI library or font
asset dependency was added.

## Backend layout

- `api/` handles HTTP and SSE; `contracts/` defines request/response data.
- `models/` holds SQLAlchemy models grouped by data area.
- `services/` implements workflows; `adapters/` connects providers and storage.
- `main.py` starts the API; `worker_cli.py` starts ingestion separately.
- `references/` is read-only legacy source, not part of the runtime.

Document access is default-deny. The server determines identity and retrieval
scope. Chat/retrieval requests cannot supply provider URLs, keys or ACL scope.

## Tests

Run the backend suite from the repository root:

~~~powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
~~~

The end-to-end suite uses Docker and a disposable PostgreSQL/pgvector container.
Tests use fake providers; they do not connect to the development database or
external model APIs.

Run frontend tests from `frontend/`:

~~~powershell
npm test
~~~

Build the frontend before checking the desktop UI in a browser:

~~~powershell
Set-Location frontend
npm run build
node tests/llm-browser.mjs
Set-Location ..
~~~

The browser check uses fake APIs and does not access application data. It needs
an existing Playwright installation and Chromium. If they are outside the
frontend, set `RUVIE_PLAYWRIGHT_PATH` to the Playwright package directory and
`RUVIE_BROWSER_PATH` to the browser executable. No new runtime dependency is
required. API and form-render tests remain part of `npm test`.

### Browser to backend integration

Build the frontend and set the existing browser tool paths before the backend
suite. The F006 browser test starts the active API and serves the built UI. It
uses the disposable PostgreSQL/provider fixture from F005. It checks two
accounts, model/key isolation, citations, reload and login. It never uses `.env`
provider credentials or the development database.

~~~powershell
$env:RUVIE_PLAYWRIGHT_PATH = 'C:/path/to/node_modules/playwright'
$env:RUVIE_BROWSER_PATH = 'C:/path/to/msedge.exe'
Set-Location frontend
npm run build
Set-Location ..
.\.venv\Scripts\python.exe -m unittest discover -s tests
~~~

The integration test skips if Node, the Playwright path or the built UI is
missing. An installed Chromium can replace Edge; omit `RUVIE_BROWSER_PATH`
when Playwright already has its browser. Docker must be running. The fake-API
browser check covers missing models, failed saves/refresh, loading locks,
keyboard, long lists on desktop and stale responses. The same harness calls
`upload-browser.mjs` for multipart/status/deadline/session checks and
`layout-browser.mjs` for 1280x720, 1024x600 and 200% zoom-equivalent layout
(640x360 CSS pixels at 2x), theme variables and contrast. Backend unit/API tests
cover provider key failures, timeout, fallback, CSRF and authorization.

If npm is unavailable but Node and the existing `frontend/node_modules` are
present, run the same scripts directly from `frontend/`:

~~~powershell
$ruvieNode = 'C:/path/to/node.exe'
& $ruvieNode --experimental-strip-types --test 'tests/*.test.mjs'
& $ruvieNode node_modules/vite/bin/vite.js build
& $ruvieNode tests/llm-browser.mjs
~~~

For backend browser E2E, also add that Node directory to the process PATH so
the Python fixture can find it. Use the browser environment variables above.

~~~powershell
$env:PATH = (Split-Path -Parent $ruvieNode) + ';' + $env:PATH
~~~


## UI languages

Choose **Tiếng Việt**, **English** or **Русский** from the language selector on
the sign-in page or above the account controls in the sidebar. The selector
stays available during login, model/connection saves, document upload and chat.
Switching language updates labels, errors, notices, title, description and
`html lang` immediately while preserving drafts, selected files and active requests.

The browser stores only an explicit choice under `ruvie.ui.locale`. A supported
stored tag takes priority over the browser's ordered language preferences.
English, Russian and Vietnamese regional tags map to `en-US`, `ru-RU` and
`vi-VN`; unmatched preferences fall back to Vietnamese. Blocked storage keeps
the current selection usable for the session. Logout retains the choice.
It belongs to the browser origin, so accounts on the same origin share it.
Other open tabs apply it on reload; there is no live tab or account synchronization.

Only interface text is translated. Questions, answers, document/project/model/
account/file names, IDs and citation data retain their original content.
This setting does not choose the language of LLM answers or change API payloads.
Russian source counts use plural forms. File sizes keep binary B/KiB/MiB units
and use the active locale's number format.

### Maintaining translations

The only added runtime dependency is `i18next`. Static resources live in
`frontend/src/lib/i18n/locales/{vi-VN,en-US,ru-RU}/translation.json`; the
shared `languages.json` registry supplies native names. Use flat semantic keys
such as `auth.login`, with complete, nonempty English values. Add the same
logical key and interpolation placeholders to all three catalogs. Missing or
empty translations fall back to English. Plural siblings follow each locale's
rules; pass raw `count`, and the translator computes `formattedCount` at render.

Components subscribe to the `i18n` store. Persistent errors/notices use
`UiMessage` (key plus optional parameters) from `messages.ts`, so already shown
messages translate again. API clients keep status/error codes and safe keys;
they do not read the DOM or expose raw server/provider text.

The languageChanged/store pattern and selected
translations were adapted from `references/src/lib/i18n/`; no legacy detector,
dynamic resource backend, parser, SvelteKit routing or runtime imports were ported.

Run the frontend commands in the Tests section after editing catalogs. The
fake-API harness also runs `i18n-browser.mjs`: all three languages, detection/
storage failures, keyboard selection, retained inputs, delayed requests, errors,
SSE/upload/polling and nine locale/viewport combinations. Existing regressions
explicitly use `vi-VN`; catalog/plural/format checks are included in `npm test`.


## Visual specifications

See [Visual specifications](specs/visual/README.md) for the current runtime
architecture, PostgreSQL ER diagram and six sequence diagrams. Current behavior
and proposed admin/organization locale settings are labeled separately.
