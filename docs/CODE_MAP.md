# Code Map

## Entry points

| Entry point | Vai tro |
|---|---|
| `src/routes/+layout.svelte` | Root frontend shell: config, i18n, socket, theme, pyodide worker. |
| `src/routes/(app)/+layout.svelte` | Authenticated shell: load user settings, models, tools, banners, terminals; pending-user overlay. |
| `src/routes/(app)/+page.svelte` | Main app page; renders `Chat.svelte`. |
| `src/routes/auth/+page.svelte` | Login/signup route. |
| `backend/ruvie/main.py` | FastAPI app entry, router mounting, chat completion, health/static serving. |
| `backend/ruvie/__init__.py` | Python package entry for `open-webui` script from `pyproject.toml`. |
| `backend/start.sh`, `backend/start_windows.bat`, `backend/dev.sh` | Backend startup scripts. |
| `package.json` | Frontend scripts/dependencies. |
| `pyproject.toml` | Backend Python package/dependencies/build config. |

## Thu muc / file quan trong

| Path | Chuc nang |
|---|---|
| `src/lib/apis/` | REST client wrappers grouped by backend resource. |
| `src/lib/components/chat/` | Core chat UI, message rendering, input, model selector, settings, citations, code blocks, file nav. |
| `src/lib/components/workspace/` | Workspace CRUD UIs for models, knowledge, prompts, tools, skills. |
| `src/lib/components/admin/` | Admin settings, users/groups, functions, analytics, evaluations. |
| `src/lib/components/channel/` | Channels, messages, threads, reactions, webhooks. |
| `src/lib/components/calendar/`, `src/lib/components/automations/` | Calendar and scheduled automation UIs. |
| `src/lib/stores/index.ts` | Shared Svelte stores for user/config/models/tools/socket/chats/ui state. |
| `src/lib/constants.ts` | Frontend base URLs, API URL constants, file support constants. |
| `backend/ruvie/routers/` | API layer. Each file maps to domain endpoints. |
| `backend/ruvie/models/` | SQLAlchemy tables and repository-like table classes. |
| `backend/ruvie/utils/middleware.py` | Main chat payload/response processing pipeline. |
| `backend/ruvie/utils/tools.py` | Tool parsing/execution support. |
| `backend/ruvie/retrieval/` | RAG, web loaders, embedding/vector search, document loaders. |
| `backend/ruvie/storage/provider.py` | Local/S3/GCS/Azure storage abstraction. |
| `backend/ruvie/internal/db.py` | Sync/async SQLAlchemy engine/session setup. |
| `backend/ruvie/config.py` | Runtime config defaults and persisted config mapping. |
| `backend/ruvie/env.py` | Environment parsing, data paths, DB URL, auth secret validation. |
| `backend/ruvie/socket/` | Socket.io server and realtime events. |
| `backend/ruvie/migrations/` | Alembic migrations. |
| `scripts/prepare-pyodide.js` | Prepares static Pyodide assets and PyPI wheels for browser code execution. |
| `.codex/skills/start-ruvie-assistant-dev/SKILL.md` | Local Codex skill documenting the repo-specific dev startup path. |

## Backend router map

| Router | Domain |
|---|---|
| `auths.py` | Signin/signup/signout, profile/password/timezone, LDAP/OAuth/admin auth config/API keys. |
| `users.py`, `groups.py` | User list/update/delete, groups, permissions, previews. |
| `chats.py` | Chat CRUD, search, archive, share, tags, stats/export, message edits. |
| `models.py` | Model registry, wrappers, tags, base model sync, access grants. |
| `files.py` | Upload, process status, content serving, rename/delete. |
| `knowledge.py` | Knowledge base CRUD, external knowledge, file attach, reindex, sync, directories, access. |
| `retrieval.py` | RAG/search/document retrieval endpoints and config. |
| `tools.py`, `functions.py`, `skills.py` | Extensibility definitions, valves, access, import/export/toggle. |
| `channels.py` | Channel CRUD, members, messages, reactions, pins, threads, webhooks. |
| `calendar.py`, `automations.py` | Calendar/events/RSVP/search and scheduled automations/runs. |
| `openai.py`, `ollama.py` | Provider/proxy endpoints. |
| `audio.py`, `images.py` | Audio STT/TTS and image generation/editing. |
| `configs.py`, `analytics.py`, `evaluations.py` | Admin/system config, analytics, model evaluation. |
| `terminals.py`, `tasks.py`, `utils.py`, `scim.py` | Terminal integrations, tasks, utilities/DB download, SCIM provisioning. |

## Business logic nen doc truoc

1. `README.md` de nam product surface upstream.
2. `src/routes/+layout.svelte`, `src/routes/(app)/+layout.svelte`, `src/routes/(app)/+page.svelte` de hieu app boot.
3. `src/lib/components/chat/Chat.svelte` va `MessageInput.svelte` de hieu luong chat.
4. `backend/ruvie/main.py` de hieu FastAPI app, router map, completion endpoint.
5. `backend/ruvie/utils/middleware.py` de hieu RAG/tools/files/chat processing.
6. `backend/ruvie/routers/auths.py`, `users.py`, `chats.py`, `files.py`, `knowledge.py`, `models.py` de hieu API chinh.
7. `backend/ruvie/models/users.py`, `chats.py`, `files.py`, `knowledge.py`, `models.py`, `config.py` de hieu persistence.
8. `backend/ruvie/config.py` va `env.py` de hieu runtime flags/env.

## Assumptions / Unknowns

- `backend/ruvie/utils/middleware.py` co qua nhieu concern, nen "business logic chinh" cua chat khong nam trong mot class/module nho gon.
- Mot so file UI rat lon; nen doc theo use case thay vi doc tu dau den cuoi.
- Co nhieu static assets/locales/emoji files khong can doc truoc de hieu architecture.
