# Ruvie Assistant

Ruvie Assistant is a local RAG app for asking questions over a document knowledge base. It uses a FastAPI backend, a React/Vite frontend, ChromaDB for vector search, FastEmbed for embeddings, and an OpenRouter-compatible chat model for answers.

## Features

- Upload documents from the UI.
- Convert supported files to Markdown with MarkItDown before indexing.
- Ingest Markdown into a local Chroma vector database.
- Ask questions and get grounded answers with source previews.
- Keep local chat history in the browser.
- Rebuild the knowledge base manually from the UI.

Supported upload formats include `.md`, `.txt`, `.pdf`, `.docx`, `.pptx`, `.xlsx`, `.html`, `.csv`, and `.json`.

## Repository Layout

```text
backend/
  app/
    api/routes.py          # API endpoints: ask, ingest, upload
    core/config.py         # environment settings
    services/
      converter.py         # MarkItDown conversion
      ingest.py            # Markdown loading, splitting, embedding
      retriever.py         # Chroma retrieval
      llm.py               # LLM answer generation
    main.py                # FastAPI app and CORS
  data/
    markdown/              # source Markdown files
    markdown/converted_md/ # converted Markdown files
    uploads/               # uploaded original files
  requirements.txt

frontend/
  src/
    api/                   # backend API client
    components/            # chat, document, and layout UI
    App.jsx
    index.css
    main.jsx
  package.json
```

## Quick Start

Run backend and frontend in separate terminals.

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env-example .env
python -m uvicorn app.main:app --reload
```

Backend URL: `http://localhost:8000`

### Frontend

```bash
cd frontend
npm install
copy .env.example .env
npm run dev
```

Frontend URL: `http://localhost:5173`

## Environment

Backend settings live in `backend/.env`.

```env
LLM_API_KEY=your_api_key_here
LLM_MODEL=gpt-4o-mini
MARKDOWN_DIR=data/markdown
CHROMA_DIR=chroma_db
CHROMA_COLLECTION=ruvie_markdown
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
APP_NAME=Ruvie
APP_URL=http://localhost:8000
FRONT_END_URLS=http://localhost:5173,http://127.0.0.1:5173
RAW_DOCUMENT_DIR=data/uploads
CONVERTED_MARKDOWN_DIR=data/markdown/converted_md
```

Frontend settings live in `frontend/.env`.

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Pipeline

1. A user uploads a document.
2. Non-Markdown files are saved in `data/uploads/`.
3. MarkItDown converts supported files into `.md` files under `data/markdown/converted_md/`.
4. The ingest pipeline loads Markdown from `data/markdown/**/*.md`.
5. Documents are split into chunks, embedded with FastEmbed, and stored in Chroma.
6. Questions retrieve relevant chunks and send them to the LLM for grounded answers.

## API

- `GET /health` checks backend status.
- `POST /upload` uploads, converts, and indexes a document.
- `POST /ingest` rebuilds the knowledge base from Markdown files.
- `POST /ask` retrieves relevant chunks and returns an answer with sources.

Example ask request:

```json
{
  "question": "What is Ruvie Assistant?"
}
```

## Useful Commands

Frontend checks:

```bash
cd frontend
npm run lint
npm run build
```

Backend import check:

```bash
cd backend
python -c "import app.main; print('backend ok')"
```
