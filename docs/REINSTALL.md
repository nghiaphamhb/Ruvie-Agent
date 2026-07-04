# Reinstall Dependencies

## Muc dich

Tai lieu nay huong dan cach tai/cai lai dependencies de project `Ruvie-Assistant` co the chay sau khi di chuyen sang thu muc/may moi.

Project gom 2 phan dependency chinh:

- Backend Python: khai bao trong `pyproject.toml`, chay bang FastAPI/Uvicorn.
- Frontend Node: khai bao trong `package.json`, chay bang Vite/SvelteKit.

Ngoai ra co Pyodide assets cho tinh nang chay Python trong browser:

- Script: `scripts/prepare-pyodide.js`
- Output: `static/pyodide/`

## Yeu cau phien ban

Theo file `package.json`:

- Node.js: `>=18.13.0 <=22.x.x`
- npm: `>=6.0.0`

Theo file `pyproject.toml`:

- Python: `>=3.11, <3.13.0a1`
- Khuyen nghi dung Python `3.11` hoac `3.12`.

Kiem tra nhanh:

```powershell
node -v
npm -v
python --version
```

## Cach nhanh neu da copy day du project cu

Neu ban di chuyen ca thu muc project va van giu lai:

- `.venv/`
- `node_modules/`
- `static/pyodide/`
- `backend/data/`

thi co the khong can tai lai dependencies.

Kiem tra:

```powershell
Test-Path .\.venv\Scripts\python.exe
Test-Path .\node_modules\.bin\vite.cmd
Test-Path .\static\pyodide
```

Neu tat ca tra ve `True`, thu chay dev mode truc tiep:

```powershell
.\.venv\Scripts\uvicorn.exe open_webui.main:app --app-dir backend --host 127.0.0.1 --port 8080 --forwarded-allow-ips "*" --reload
```

Mo terminal khac:

```powershell
.\node_modules\.bin\vite.cmd dev --host 0.0.0.0
```

## Cai lai frontend dependencies

Chay trong root project:

```powershell
npm install
```

Neu muon cai dung theo lockfile, dung:

```powershell
npm ci
```

Luu y:

- `npm ci` se xoa va tao lai `node_modules/`.
- Dung `npm install` neu lockfile/dependency dang duoc sua trong qua trinh dev.
- Frontend dev server binary nam tai `node_modules/.bin/vite.cmd`.

Kiem tra:

```powershell
.\node_modules\.bin\vite.cmd --version
```

## Cai lai Pyodide assets

Project co script:

```powershell
npm run pyodide:fetch
```

Lenh nay goi:

```powershell
node scripts/prepare-pyodide.js
```

Script se tai/copy Pyodide va cac package browser-side vao:

- `static/pyodide/`

Khi nao can chay:

- Sau khi clone/move project ma `static/pyodide/` bi thieu.
- Khi `npm run dev` hoac `npm run build` bao loi lien quan Pyodide.
- Khi dependency `pyodide` trong `package.json` thay doi version.

Luu y quan trong:

- Script nay can internet.
- Script tai tu CDN/PyPI, nen co the loi neu proxy/firewall chan mang.
- Neu chi muon dev nhanh va `static/pyodide/` da co san, co the chay Vite truc tiep thay vi `npm run dev`.

Dev nhanh, bo qua fetch:

```powershell
.\node_modules\.bin\vite.cmd dev --host 0.0.0.0
```

Dev theo script mac dinh:

```powershell
npm run dev
```

## Cai lai backend Python dependencies

### Cach khuyen nghi: tao venv moi

Chay trong root project:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
```

Cai project/backend dependencies tu `pyproject.toml`:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
```

Kiem tra Uvicorn:

```powershell
.\.venv\Scripts\uvicorn.exe --version
```

### Cai optional dependencies

Neu can Postgres support:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[postgres]"
```

Neu can MariaDB support:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[mariadb]"
```

Neu can unstructured document parsing:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[unstructured]"
```

Neu can tat ca optional/test/development integrations:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[all]"
```

Can nhac:

- `.[all]` nang va tai nhieu dependency hon.
- Chi cai optional group neu thuc su can tinh nang do.

## Chay project sau khi reinstall

Backend:

```powershell
.\.venv\Scripts\uvicorn.exe open_webui.main:app --app-dir backend --host 127.0.0.1 --port 8080 --forwarded-allow-ips "*" --reload
```

Frontend:

```powershell
.\node_modules\.bin\vite.cmd dev --host 0.0.0.0
```

Mo app:

```text
http://localhost:5173
```

Backend health:

```powershell
Invoke-WebRequest http://127.0.0.1:8080/health
```

## Build / check / test sau khi cai lai

Frontend type check:

```powershell
npm run check
```

Frontend test:

```powershell
npm run test:frontend
```

Build frontend:

```powershell
npm run build
```

Lint:

```powershell
npm run lint
```

Luu y:

- `npm run build` va `npm run dev` mac dinh se chay `npm run pyodide:fetch` truoc.
- `npm run lint` co `eslint . --fix`, tuc la co the tu dong sua file frontend.

## Du lieu can giu lai khi di chuyen project

Neu muon giu users, admin, chats, uploads, knowledge, logo customization:

- `backend/data/`
- `static/static/`
- `static/static-logo-backup-before-ruvie/`
- `.codex/`
- `docs/`

Quan trong nhat:

- `backend/data/webui.db`
- `backend/data/uploads/`
- `backend/data/vector_db/`

Backup database hien co:

- `backend/data/webui.db.backup-before-admin-fix-20260704`

## Loi thuong gap

### `vite.cmd` khong ton tai

Nguyen nhan:

- Chua cai frontend dependencies.

Cach sua:

```powershell
npm install
```

### `.venv\Scripts\uvicorn.exe` khong ton tai

Nguyen nhan:

- Chua tao venv.
- Chua cai backend dependencies.

Cach sua:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
```

### `npm run dev` bi dung o Pyodide

Nguyen nhan:

- `scripts/prepare-pyodide.js` can internet de tai Pyodide/PyPI packages.
- Mang/proxy/firewall chan download.

Cach xu ly:

```powershell
npm run pyodide:fetch
```

Neu `static/pyodide/` da co san va chi can dev nhanh:

```powershell
.\node_modules\.bin\vite.cmd dev --host 0.0.0.0
```

### Port `8080` hoac `5173` bi chiem

Kiem tra:

```powershell
Get-NetTCPConnection -LocalPort 8080,5173 -ErrorAction SilentlyContinue
```

Neu co process dang dung port, dung process do hoac doi port dev.

### Sai Python version

`pyproject.toml` yeu cau:

```text
>=3.11, <3.13.0a1
```

Neu dung Python `3.13+`, mot so package co the khong cai duoc. Dung Python `3.11` hoac `3.12`.

## Checklist reinstall tu dau

1. Cai Node.js version `18.13` den `22.x`.
2. Cai Python `3.11` hoac `3.12`.
3. Mo terminal tai root project.
4. Chay `npm install`.
5. Chay `python -m venv .venv`.
6. Chay `.\.venv\Scripts\python.exe -m pip install --upgrade pip`.
7. Chay `.\.venv\Scripts\python.exe -m pip install -e .`.
8. Chay `npm run pyodide:fetch` neu `static/pyodide/` thieu.
9. Chay backend bang Uvicorn.
10. Chay frontend bang Vite.
11. Mo `http://localhost:5173`.

## Assumptions / Unknowns

- Tai lieu nay duoc viet cho Windows PowerShell vi project hien dang duoc thao tac tren Windows.
- Neu move sang Linux/macOS/WSL, lenh activate venv va binary path se khac.
- Khong bat buoc cai Docker de chay dev local theo cach hien tai.
- Neu dung PostgreSQL/Redis/vector DB ngoai SQLite/local Chroma, can bo sung bien moi truong rieng theo `docs/SETUP_AND_RUN.md`.
