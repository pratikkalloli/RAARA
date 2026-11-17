# RAARA

RAARA (Retrieval-Augmented Academic Regulatory Assistant) is a document-grounded workspace for academic policy questions. Users can upload PDFs, ask questions against documents available to their account, inspect evidence and source metadata, and retain conversation history. Uploaded documents remain unverified until an administrator reviews them. Administrator review records an internal review decision; it does not establish that a document is an official university regulation.

## Requirements

- Python 3.11
- Node.js and npm
- A Groq API key for live Groq chat
- `sentence-transformers` and the `all-MiniLM-L6-v2` model for local embeddings
- Optional: a working `cl100k_base` tiktoken cache for offline backend tests

Provider credentials belong only in `backend/.env`. Do not put credentials in frontend variables, commit them, or send them in chat. Automated tests must run with provider keys blank and use mocks.

## Backend setup (PowerShell)

```powershell
cd C:\prompt_mini_proj\backend
py -3.11 -m venv .venv311
.\.venv311\Scripts\Activate.ps1
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Set `GROQ_API_KEY` and a Groq-supported `GROQ_CHAT_MODEL` locally in `backend/.env`. Keep `AI_PROVIDER=groq`, `EMBEDDING_PROVIDER=local`, `EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2`, and `EMBEDDING_DIMENSIONS=384`. Do not replace an existing `.env` with `.env.example`; update the provider settings in the existing file and retain its database, upload, and Chroma paths. Never expose the key in logs, screenshots, shell history, or frontend code. No Gemini or OpenAI credentials are used.

Start the API:

```powershell
cd C:\prompt_mini_proj\backend
.\.venv311\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health endpoints: `http://127.0.0.1:8000/api/health` and `/api/health/ai`. The AI health endpoint reports selected configuration and whether a credential is configured; it intentionally does not make a paid availability check.

## Frontend setup

```powershell
cd C:\prompt_mini_proj\frontend
npm ci
npm run dev
```

Vite uses `http://127.0.0.1:8000` for `/api` by default. To target an isolated backend, set `RAARA_API_PROXY_TARGET` before starting Vite, for example:

```powershell
$env:RAARA_API_PROXY_TARGET = 'http://127.0.0.1:8001'
npm run dev -- --host 127.0.0.1 --port 5174
```

## Storage and safety

The backend uses SQLite and persistent ChromaDB paths from its configuration. Treat the configured database, vector directory, and upload directory as application data. Do not point acceptance tests at them. For tests and acceptance work, set all three to a fresh temporary location and use synthetic PDFs clearly marked as test fixtures. Test accounts and fixtures should remain isolated and be removed only from their explicitly temporary directory.

The default registration flow creates student accounts. Administrator accounts are provisioned separately. The administrator review workflow can mark uploaded content reviewed or rejected; reviewed content is still not a guarantee of official provenance. Chat answers show evidence and verification state, and users should consult the original applicable regulation for consequential decisions.

### Switching an existing installation to local 384-dimensional embeddings

The active collection is `raara_documents_groq_local_384`, separate from prior provider/dimension collections. Existing Chroma collections and vectors are not deleted or converted automatically. To migrate retained PDFs, first back up the database, upload directory, and Chroma directory. Then run a read-only inventory/preflight from `backend`:

```powershell
.\.venv311\Scripts\python.exe .\reindex_local_embeddings.py
```

Review the ready/blocked counts and confirm the configured database, upload path, and Chroma path are the intended existing installation. Only then perform the write operation:

```powershell
.\.venv311\Scripts\python.exe .\reindex_local_embeddings.py --apply
```

The apply operation reads and checksums retained PDFs, creates/upserts vectors only in the new local collection, and updates each document's indexing metadata. It leaves old collections and PDF files in place. Do not run `--apply` against production until the backup and preflight have been reviewed.

The current ingestion path extracts PDF text; it does not perform OCR on image-only scans. Failed ingestion is synchronous and does not currently create a durable retry job. Keep a copy of the source PDF until upload and indexing complete.

## Verification

Frontend:

```powershell
cd C:\prompt_mini_proj\frontend
npm test
npm run build
```

Backend (Windows; tests use mocked providers and must not make live calls):

```powershell
cd C:\prompt_mini_proj\backend
$env:GROQ_API_KEY = ''
$env:TIKTOKEN_CACHE_DIR = "$env:LOCALAPPDATA\RAARA\tiktoken-cache"
.\.venv311\Scripts\python.exe -m pytest tests -v
```

On Windows, an environment-specific AnyIO/TestClient socketpair startup stall has been observed. If it occurs, do not report the run as passed. Run the same suite in the project’s working WSL Python 3.11 environment with database, ChromaDB, and uploads redirected to a fresh `/tmp` directory, provider keys empty, and `TIKTOKEN_CACHE_DIR` pointing to the valid cache. Do not alter production chunking to work around a missing tokenizer resource.

## Migration notes

Groq is the only external chat provider. Embeddings run locally and do not use a hosted embedding endpoint. Tests inject/mock both model boundaries; a live Groq request has not been verified by this migration. The sentence-transformers model may need to be downloaded once before first use if it is not already in the local model cache. Retain the prior Gemini collection as a rollback/reference until the local collection is verified; never mix 768-dimensional Gemini vectors with 384-dimensional local vectors.
