# Setup And Run

## Yeu cau co ban

- Node.js: `package.json` khai bao `node >=18.13.0 <=22.x.x`, `npm >=6.0.0`.
- Python: `pyproject.toml` khai bao `>=3.11, <3.13.0a1`.
- Backend dependencies: `pyproject.toml`, `backend/requirements.txt`, `backend/requirements-min.txt`.
- Frontend dependencies: `package.json` va `package-lock.json`.
- Optional services: Ollama, OpenAI-compatible APIs, Redis, PostgreSQL, vector DB ngoai Chroma, S3/GCS/Azure storage tuy cau hinh.

## Cai dependency

Frontend:

```powershell
npm install
```

Backend, mot cach pho bien trong repo local nay:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

Neu dung packaging/dependency tu `pyproject.toml`, co the cai project bang tool Python phu hop voi workflow cua team. Repo hien co `uv.lock`, nhung tai lieu nay chua xac minh day du lenh `uv sync` trong moi truong hien tai.

## Chay dev

Frontend script chinh trong `package.json`:

```powershell
npm run dev
```

Lenh nay se chay `npm run pyodide:fetch && vite dev --host`. `scripts/prepare-pyodide.js` co fetch tu jsDelivr/PyPI de chuan bi `static/pyodide`, nen moi truong khong co network co the fail o buoc Pyodide.

Backend script Windows chinh:

```powershell
backend\start_windows.bat
```

Backend Linux/macOS/WSL:

```bash
cd backend
./start.sh
```

Backend dev reload:

```bash
cd backend
./dev.sh
```

## Cach chay da kiem chung trong workspace hien tai

Trong Codex/local Windows workspace nay, cach on dinh da duoc kiem chung:

Backend:

```powershell
.venv\Scripts\uvicorn.exe open_webui.main:app --app-dir backend --host 127.0.0.1 --port 8080 --forwarded-allow-ips "*" --reload
```

Frontend:

```powershell
node_modules\.bin\vite.cmd dev --host
```

Ly do: `src/lib/constants.ts` trong dev mode tro frontend den backend `http://<hostname>:8080`, con `npm run dev` co buoc fetch Pyodide co the bi chan network.

Kiem tra:

```powershell
curl http://127.0.0.1:8080/health
curl -I http://localhost:5173/
```

## Build / test / lint

Frontend:

```powershell
npm run build
npm run check
npm run test:frontend
npm run lint:frontend
```

Lint tong hop:

```powershell
npm run lint
```

Luu y: `npm run lint` goi `lint:backend` bang `pylint backend/`; can backend dependencies day du.

Format:

```powershell
npm run format
npm run format:backend
```

Docker/compose:

```powershell
docker compose up -d
```

Hoac Makefile:

```bash
make install
make start
make stop
make startAndBuild
```

## Bien moi truong quan trong

| Bien | Y nghia | Noi doc |
|---|---|---|
| `WEBUI_SECRET_KEY` | Bat buoc khi `WEBUI_AUTH=True`; dung cho auth/session/encryption. | `backend/open_webui/env.py` |
| `WEBUI_AUTH` | Bat/tat auth. Default `True`. | `backend/open_webui/env.py` |
| `ENABLE_SIGNUP` | Bat/tat signup khi co auth. | `backend/open_webui/config.py` |
| `DEFAULT_USER_ROLE` | Role mac dinh cho user moi, default `pending`. | `backend/open_webui/config.py` |
| `DATA_DIR` | Thu muc data backend, default `backend/data` trong dev. | `backend/open_webui/env.py` |
| `DATABASE_URL` | SQLite/PostgreSQL connection, default `sqlite:///{DATA_DIR}/webui.db`. | `backend/open_webui/env.py` |
| `REDIS_URL` | Redis cho scaling/session/websocket options neu dung. | `backend/open_webui/env.py` |
| `OLLAMA_BASE_URL`, `OLLAMA_BASE_URLS` | Ollama backend endpoints. | `backend/open_webui/config.py` |
| `OPENAI_API_KEY`, `OPENAI_API_BASE_URL(S)` | OpenAI-compatible provider config. | `backend/open_webui/config.py` |
| `VECTOR_DB` | Vector store, default `chroma`; cac adapter khac trong `retrieval/vector/dbs`. | `backend/open_webui/config.py` |
| `STORAGE_PROVIDER` | `local`, `s3`, `gcs`, `azure` theo provider code. | `backend/open_webui/config.py`, `storage/provider.py` |
| `CORS_ALLOW_ORIGIN` | Dev/prod CORS origins. Example trong `.env.example`. | `.env.example`, `backend/open_webui/config.py` |

## Loi setup thuong gap

- Backend fail voi `WEBUI_SECRET_KEY is not set`: set `WEBUI_SECRET_KEY` trong `.env` hoac dung `backend/start_windows.bat`/`start.sh` de script tao/doc `.webui_secret_key`.
- Frontend fail o `scripts/prepare-pyodide.js`: moi truong bi chan network khi fetch Pyodide/PyPI. Trong local dev co the chay truc tiep `node_modules\.bin\vite.cmd dev --host` neu `static/pyodide` da du dung cho nhu cau hien tai.
- Frontend khong noi backend: dev frontend mac dinh goi `http://<hostname>:8080` trong `src/lib/constants.ts`; backend phai lang nghe port `8080`.
- User bi man hinh pending: `DEFAULT_USER_ROLE` default la `pending`; admin can doi role user trong Admin Users. Neu DB khong co admin, can sua du lieu/bootstrap admin.
- Missing Python modules khi start backend: cai thieu backend requirements vao `.venv`.
- Vector/RAG loi khi dung provider ngoai default: can env rieng cho `VECTOR_DB`, embedding provider, OCR/document loaders.

## Assumptions / Unknowns

- Chua test lai toan bo `npm run build`, lint, Docker build trong lan tao tai lieu nay.
- Repo local hien co `.venv`, `node_modules`, `.env`, `backend/data/webui.db`; cac file nay co the khac voi clean checkout.
- `uv.lock` ton tai nhung workflow uv chinh thuc cho repo nay chua duoc xac minh trong code/scripts doc duoc.
