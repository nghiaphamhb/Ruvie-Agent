# Project Overview

## Project nay giai quyet van de gi?

Project nay la mot self-hosted AI workspace dua tren Open WebUI. Code hien tai cung cap mot giao dien web de nguoi dung noi chuyen voi cac model AI, ket noi Ollama/OpenAI-compatible APIs, quan ly model tuy bien, upload file, tao knowledge base cho RAG, dung tool/function/skill, lam viec voi notes, channels, calendar va automations.

Bang chung chinh:

- `README.md` mo ta Open WebUI la "self-hosted AI platform" ho tro Ollama, OpenAI-compatible APIs, RAG, plugins, models/agents, notes, channels, calendar, automations.
- `backend/open_webui/main.py` tao FastAPI app va dang ky cac router cho `auths`, `users`, `chats`, `models`, `knowledge`, `files`, `tools`, `skills`, `functions`, `channels`, `calendar`, `automations`.
- `src/routes/(app)/+page.svelte` render `src/lib/components/chat/Chat.svelte` lam man hinh app chinh.

## Nguoi dung chinh

- End user: dang nhap, chat voi AI, upload/gan file, dung knowledge, notes, channels, calendar, automations.
- Admin: quan ly users/groups/roles, cau hinh auth, model connections, web search, documents, code execution, tools/functions va analytics. UI nam trong `src/routes/(app)/admin/*` va backend dung `get_admin_user` trong nhieu router.
- Builder/power user: tao model wrapper, prompt, tool, skill, function, knowledge base trong workspace routes `src/routes/(app)/workspace/*`.
- Operator/self-host maintainer: cai dat env, database, storage, vector DB, Redis/WebSocket, Docker/dev server qua `pyproject.toml`, `package.json`, `backend/start.sh`, `backend/start_windows.bat`, `docker-compose*.yaml`.

## Chuc nang chinh

- Auth va user access: signup/signin/signout, LDAP/OAuth/trusted headers, API key, admin config trong `backend/open_webui/routers/auths.py`, user/group management trong `backend/open_webui/routers/users.py` va `backend/open_webui/routers/groups.py`.
- Chat AI: UI tai `src/lib/components/chat/Chat.svelte`, message input tai `src/lib/components/chat/MessageInput.svelte`, chat CRUD tai `backend/open_webui/routers/chats.py`, completion endpoint tai `backend/open_webui/main.py`.
- Model registry va connections: frontend API `src/lib/apis/models/index.ts`, backend `backend/open_webui/routers/models.py`, provider proxy `backend/open_webui/routers/openai.py`, `backend/open_webui/routers/ollama.py`.
- Files va knowledge/RAG: upload/process files trong `backend/open_webui/routers/files.py`, knowledge CRUD/reindex/sync trong `backend/open_webui/routers/knowledge.py`, retrieval/vector logic trong `backend/open_webui/retrieval/*`.
- Tools, functions, skills: UI trong `src/lib/components/workspace/*` va `src/lib/components/admin/Functions*`, API trong `backend/open_webui/routers/tools.py`, `functions.py`, `skills.py`, execution helpers trong `backend/open_webui/utils/tools.py`, `backend/open_webui/functions.py`.
- Collaboration: channels va realtime messages trong `backend/open_webui/routers/channels.py`, socket app in `backend/open_webui/socket/main.py`.
- Notes, calendar, automations: routers `notes.py`, `calendar.py`, `automations.py`; UI under `src/routes/(app)/notes`, `src/routes/(app)/calendar`, `src/routes/(app)/automations`.
- Admin analytics/evaluations: routes `src/routes/(app)/admin/analytics`, `src/routes/(app)/admin/evaluations`; backend `analytics.py`, `evaluations.py`.

## Luong hoat dong tong quan

1. User mo web app. SvelteKit root `src/routes/+layout.svelte` khoi tao i18n, socket.io, config, theme, pyodide worker va app state.
2. Neu chua co token/user, app dieu huong den `src/routes/auth/+page.svelte`; frontend goi `src/lib/apis/auths/index.ts` toi `backend/open_webui/routers/auths.py`.
3. Sau khi co session user, `src/routes/(app)/+layout.svelte` tai user settings, models, banners, tools, terminal/tool servers. Neu role khong phai `user`/`admin`, component `AccountPending.svelte` hien overlay pending.
4. Main app render `src/lib/components/chat/Chat.svelte`. User chon model, nhap prompt trong `MessageInput.svelte`, optionally attach files/knowledge/notes/chats/web pages.
5. Frontend tao/cap nhat chat qua `src/lib/apis/chats/index.ts` va gui completion den backend endpoint `/api/chat/completions` trong `backend/open_webui/main.py`.
6. Backend `chat_completion` goi `process_chat_payload` trong `backend/open_webui/utils/middleware.py` de nap model, files, knowledge, tools, filters, permissions, metadata; sau do forward request sang Ollama/OpenAI-compatible/provider pipeline.
7. Streaming/non-streaming response di qua `process_chat_response`, tool calls, file outputs, citations, task/status events; frontend cap nhat message tree trong `Chat.svelte`.
8. Khi task chinh hoan tat, chat/messages/files duoc luu vao database qua models nhu `backend/open_webui/models/chats.py`, `chat_messages.py`, `files.py`; UI cho phep share/archive/tag/pin/export/tiep tuc chat.

## Assumptions / Unknowns

- Ten repo la `Ruvie-Assistant`, nhung branding trong code va docs van chu yeu la Open WebUI (`src/lib/constants.ts`, `README.md`). Chua thay tai lieu rieng mo ta cac thay doi "Ruvie" ngoai local setup/DB state.
- Tai lieu nay dua tren source code hien tai, khong xac minh tat ca tinh nang bang end-to-end UI.
- Mot so chuc nang enterprise/production nhu SCIM, Redis multi-node, cloud storage, vector DB ngoai Chroma co code/config, nhung chua duoc chay kiem thu trong moi truong hien tai.
