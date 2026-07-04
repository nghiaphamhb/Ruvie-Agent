# Architecture

## So do tong quan

```mermaid
flowchart LR
    Browser["Browser / PWA\nSvelteKit UI"] --> FEAPI["src/lib/apis/*\nREST wrappers"]
    Browser --> Socket["socket.io client\nsrc/routes/+layout.svelte"]
    FEAPI --> FastAPI["FastAPI app\nbackend/open_webui/main.py"]
    Socket --> SocketServer["Socket server\nbackend/open_webui/socket/main.py"]
    FastAPI --> Routers["Routers\nbackend/open_webui/routers/*"]
    Routers --> Models["Persistence layer\nbackend/open_webui/models/*"]
    Models --> DB["SQLite / PostgreSQL\nbackend/data/webui.db or DATABASE_URL"]
    Routers --> Storage["File storage\nlocal/S3/GCS/Azure\nstorage/provider.py"]
    Routers --> Retrieval["RAG / loaders / vector\nbackend/open_webui/retrieval/*"]
    Retrieval --> VectorDB["Vector DB\nChroma default, PGVector, Qdrant, etc."]
    FastAPI --> Middleware["Chat pipeline\nutils/middleware.py"]
    Middleware --> Providers["Ollama / OpenAI-compatible / Anthropic / Google"]
    Middleware --> Tools["Tools / Functions / Skills\nutils/tools.py, functions.py"]
    Routers --> Workers["Background-ish tasks\nAPScheduler, automations, async handlers"]
```

## Runtime layers

- Frontend: SvelteKit/Vite app in `src/`. Routes live in `src/routes`, reusable UI in `src/lib/components`, stores in `src/lib/stores/index.ts`, REST clients in `src/lib/apis/*`.
- Backend: FastAPI app in `backend/open_webui/main.py`. It mounts `/ws`, includes all `/api/v1/*` routers, exposes OpenAI-compatible routes such as `/api/chat/completions`, serves static/frontend assets, and health endpoints `/health`, `/ready`, `/health/db`.
- Database: SQLAlchemy sync + async engines in `backend/open_webui/internal/db.py`. Default DB URL is SQLite under `DATA_DIR/webui.db` from `backend/open_webui/env.py`; PostgreSQL is supported by `DATABASE_URL`.
- Storage: `backend/open_webui/storage/provider.py` abstracts local upload storage plus S3, Google Cloud Storage, and Azure Blob. Upload directory is configured in `backend/open_webui/config.py`.
- RAG/vector: `backend/open_webui/retrieval/*` handles document loaders, web loaders, embeddings, rerankers, and vector DB adapters. Default `VECTOR_DB` is `chroma` in `backend/open_webui/config.py`.
- Realtime: `backend/open_webui/socket/main.py` is mounted at `/ws`; frontend connects in `src/routes/+layout.svelte`.
- Scripts/build: frontend scripts in `package.json`; backend packaging/deps in `pyproject.toml`; startup scripts in `backend/start.sh`, `backend/start_windows.bat`, `backend/dev.sh`; Pyodide asset preparation in `scripts/prepare-pyodide.js`.

## Module va thu muc chinh

| Path | Trach nhiem |
|---|---|
| `src/routes/+layout.svelte` | App shell, i18n, socket, theme/config/user bootstrap, pyodide worker. |
| `src/routes/(app)/+layout.svelte` | Authenticated layout; loads settings, models, tools, banners, terminals; handles pending users. |
| `src/routes/(app)/+page.svelte` | Main app route; renders chat. |
| `src/lib/components/chat/Chat.svelte` | Core chat state machine: selected models, message history, queue, files, submit/regenerate/share flows. |
| `src/lib/components/chat/MessageInput.svelte` | Prompt input, file upload/attach flows, commands, model/tool/knowledge insert UX. |
| `src/lib/apis/*` | Typed-ish frontend wrappers over backend REST endpoints. |
| `backend/open_webui/main.py` | Backend entry point, app lifecycle, router mounting, chat completion endpoint, static serving, health checks. |
| `backend/open_webui/routers/*` | HTTP API grouped by domain: auths, users, chats, files, knowledge, models, tools, functions, channels, calendar, automations, etc. |
| `backend/open_webui/models/*` | SQLAlchemy models and table repositories. Most files expose singleton repositories such as `Users`, `Chats`, `Files`, `Models`. |
| `backend/open_webui/utils/middleware.py` | Main chat processing pipeline: payload transformation, files/RAG/tools/functions, streaming response handling. |
| `backend/open_webui/retrieval/*` | RAG loaders, web search providers, vector DB adapters, embedding/reranking helpers. |
| `backend/open_webui/config.py` | Runtime config values and default config persisted to DB. |
| `backend/open_webui/env.py` | Env parsing, paths, DB URL, auth secret validation, Redis/websocket config. |
| `backend/open_webui/socket/*` | Realtime socket rooms/events for chat/channel/user activity. |

## Dong du lieu chat chinh

1. User nhap prompt trong `src/lib/components/chat/MessageInput.svelte`.
2. `src/lib/components/chat/Chat.svelte` gom history bang `createMessagesList`, quan ly `selectedModels`, `files`, `chatFiles`, queue va goi submit.
3. Neu chat moi, frontend tao record qua `src/lib/apis/chats/index.ts` -> `backend/open_webui/routers/chats.py`.
4. Completion request den `/api/chat/completions` trong `backend/open_webui/main.py`.
5. `main.py` lay user/model/metadata, goi `process_chat_payload` trong `backend/open_webui/utils/middleware.py`.
6. Middleware nap folder/knowledge/files, xu ly image/file context, tools/functions/filters, permissions, model params.
7. Backend forward sang provider (`backend/open_webui/routers/openai.py`, `ollama.py`, provider clients/config) hoac pipeline tuong ung.
8. `process_chat_response` xu ly streaming chunks, tool call results, files/citations/events; socket/task events cap nhat frontend khi can.
9. Chat/message/file metadata duoc luu qua `backend/open_webui/models/chats.py`, `chat_messages.py`, `files.py`.

## Assumptions / Unknowns

- Khong co worker process rieng theo kieu queue system doc lap trong repo. Automations dung APScheduler/task logic trong Python app; mot so handler la async/background handler trong request lifecycle.
- Docker va production deploy co nhieu compose variants, nhung tai lieu nay tap trung vao source architecture, khong phan tich tung compose file.
- `backend/open_webui/utils/middleware.py` la module rat lon va chua tach domain ro; architecture hien tai gan nhieu chat pipeline concern vao mot file.
