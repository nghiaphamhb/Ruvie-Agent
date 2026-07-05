# Dependency Reuse Quickstart

## Mục tiêu

Tài liệu này tổng hợp cách cài lại dependency cho `Ruvie-Assistant` trên Windows để có thể dùng lại nhanh khi clone/move project sang máy mới.

Đây là đường dẫn đã dùng thành công trong workspace này:

* Frontend: `npm ci`
* Backend: `python -m pip install -r backend/requirements.txt`
* Dev run: backend `uvicorn`, frontend `vite`

## Yêu cầu

* Node.js: `>=18.13.0 <=22.x.x`
* npm: `>=6.0.0`
* Python: `>=3.11, <3.13.0a1`
* Windows PowerShell

Kiểm tra nhanh:

```powershell
node -v
npm -v
python --version
```

## 1. Tạo môi trường Python

Trong root project:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
```

## 2. Cài frontend dependencies

Nếu đã có `package-lock.json`, ưu tiên dùng lockfile:

```powershell
npm ci
```

Kiểm tra:

```powershell
.\node_modules\.bin\vite.cmd --version
```

## 3. Cài backend dependencies

Trong workspace này, cách ổn định và nhanh hơn là cài theo file runtime requirements:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

Nếu bạn muốn cài theo `pyproject.toml` thay vì file requirements:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
```

Lưu ý:

* `pip install -e .` có thể rất lâu vì backend có tập dependency lớn.
* Nếu mục tiêu là dev local nhanh, `backend/requirements.txt` thường dễ chịu hơn.

## 4. Tạo hoặc cập nhật `.env`

File `.env` nên nằm ở root project.

Mẫu đã dùng trong workspace này:

```env
OLLAMA_BASE_URL='http://localhost:11434'

OPENAI_API_BASE_URL=''
OPENAI_API_KEY=''
DATABASE_URL='sqlite:///D:/Github Repository/Ruvie-Assistant/backend/data/webui.db'
WEBUI_SECRET_KEY='dev-secret-key-dev-secret-key-dev-secret-key-dev-secret-key'

CORS_ALLOW_ORIGIN='http://localhost:5173;http://localhost:8080'

ENABLE_MEMORY_SYSTEM_CONTEXT=true
FORWARDED_ALLOW_IPS='*'

SCARF_NO_ANALYTICS=true
DO_NOT_TRACK=true
ANONYMIZED_TELEMETRY=false
```

Nếu project được move sang đường dẫn khác, hãy cập nhật `DATABASE_URL` cho đúng đường dẫn mới.

## 5. Chuẩn bị Pyodide assets

Chỉ cần nếu `static/pyodide/` bị thiếu hoặc build/dev báo lỗi liên quan Pyodide:

```powershell
npm run pyodide:fetch
```

Nếu muốn dev nhanh và bỏ qua bước fetch:

```powershell
.\node_modules\.bin\vite.cmd dev --host 0.0.0.0
```

## 6. Chạy dev mode

Backend:

```powershell
.\.venv\Scripts\uvicorn.exe ruvie.main:app --app-dir backend --host 127.0.0.1 --port 8080 --reload
```

Nếu bạn thật sự cần `--forwarded-allow-ips *` trong PowerShell, dùng:

```powershell
.\.venv\Scripts\uvicorn.exe --% ruvie.main:app --app-dir backend --host 127.0.0.1 --port 8080 --forwarded-allow-ips * --reload
```

Frontend:

```powershell
.\node_modules\.bin\vite.cmd dev --host 0.0.0.0
```

Kiểm tra:

```powershell
Invoke-WebRequest http://127.0.0.1:8080/health
Invoke-WebRequest http://localhost:5173/ -Method Head
```

## 7. Các tình huống thường gặp

### `vite.cmd` không tồn tại

Chưa cài frontend dependencies:

```powershell
npm ci
```

### `.venv\Scripts\uvicorn.exe` không tồn tại

Chưa tạo venv hoặc chưa cài backend dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

### Backend bị kẹt ở việc tải model embedding khi startup

Trong workspace này, cách an toàn là tạm thời ghi đè config embedding sang `ollama` và model nhẹ hơn trong SQLite config, hoặc bắt đầu backend với biến môi trường phù hợp cho dev.

Nếu chỉ cần lên nhanh để dev UI, dùng:

```powershell
$env:ENABLE_MEMORY_SYSTEM_CONTEXT='false'
```

## 8. Checklist nhanh

1. Kiểm tra Node/Python đúng version.
2. Tạo `.venv`.
3. Chạy `npm ci`.
4. Chạy `pip install -r backend\requirements.txt`.
5. Chuẩn bị `.env`.
6. Chạy backend bằng `uvicorn`.
7. Chạy frontend bằng `vite`.
8. Mở `http://localhost:5173`.

## Ghi chú

* Tài liệu này ưu tiên cho Windows PowerShell.
* Nếu chuyển sang Linux/macOS/WSL, đường dẫn `.venv` và lệnh activate sẽ khác.
* `backend/data/webui.db` và `node_modules/` có thể giữ lại để khỏi cài lại nếu bạn không xoá project.
