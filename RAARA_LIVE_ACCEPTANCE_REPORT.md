# RAARA Live Acceptance Report

**Status: PARTIALLY PREPARED — LIVE AI ACCEPTANCE BLOCKED**  
**Date:** 2026-11-14  
**Application:** Original RAARA React/Vite + FastAPI app; the Phase 8C examiner demo was not used.

This report records work completed so far. No live OpenAI requests have been made. The remaining paid test and OpenAI-dependent browser steps require the owner to enter an API key locally and explicitly approve the calls.

## Isolated environment

Acceptance root (temporary, no production data copied):

`C:\Users\Pratik Kalloli\AppData\Local\Temp\RAARA_LIVE_ACCEPTANCE_20261114_141801_aa135e6c`

- SQLite: `C:\Users\Pratik Kalloli\AppData\Local\Temp\RAARA_LIVE_ACCEPTANCE_20261114_141801_aa135e6c\raara_test.db`
- ChromaDB: `C:\Users\Pratik Kalloli\AppData\Local\Temp\RAARA_LIVE_ACCEPTANCE_20261114_141801_aa135e6c\chroma_data`
- Uploads: `C:\Users\Pratik Kalloli\AppData\Local\Temp\RAARA_LIVE_ACCEPTANCE_20261114_141801_aa135e6c\uploads`
- Synthetic test fixture: `C:\Users\Pratik Kalloli\AppData\Local\Temp\RAARA_LIVE_ACCEPTANCE_20261114_141801_aa135e6c\SYNTHETIC_RAARA_ACCEPTANCE_NOT_OFFICIAL.pdf`
- Backend regression storage is separately isolated under `...\regression\`.

The PDF has an explicit title and repeated statements that its fictional 73% example is synthetic and not an official university regulation. It has **not** been uploaded or indexed.

Configuration checks:

| Check | Result |
|---|---|
| `JWT_SECRET_KEY` for running backend | **PASS** — fresh, process-only test secret; value not recorded or printed |
| OpenAI API key | **BLOCKED** — not configured; value not requested in chat or stored in a file |
| Chat model | **PASS** — `gpt-4.1-mini` |
| Embedding model | **PASS** — `text-embedding-3-small` |
| Database, ChromaDB, upload locations | **PASS** — all configured to the isolated temporary root |
| Production paths | **PASS** — production SQLite, ChromaDB, and uploads were not selected |
| `backend/.env` | **PASS** — absent; no credential written there |
| Git ignore/tracking inspection | `.gitignore` lists `.env`. **UNVERIFIABLE** whether it is tracked because this project directory has no `.git` metadata; `git status`, `git check-ignore`, and `git ls-files` cannot run here. |

The isolated test database has one disposable student created through the original UI, zero documents, zero conversations, and zero conversation messages (read-only count inspection). No administrator account was created. Existing production databases and ChromaDB were not modified.

## Automated regression

| Check | Result |
|---|---|
| Full backend suite (`backend\.venv311\Scripts\python.exe -m pytest -v`) | **PASS** — 276 passed, 0 failed, 30.83 seconds |
| Frontend suite (`npm test`) | **PASS** — 8 passed, 0 failed |
| Frontend production build (`npm run build`) | **PASS** — Vite 6.4.5 |
| OpenAI calls in automated tests | **PASS** — tests use mocks; no paid calls |

Backend regression storage was isolated beneath the acceptance root. Tests did not use production SQLite, ChromaDB, or uploaded documents.

## Running application and browser observations

| Check | Result |
|---|---|
| Original FastAPI process | **PASS** — listening on `127.0.0.1:8000`, PID 32148 |
| `GET http://127.0.0.1:8000/api/health` | **PASS** — `{"status":"ok","service":"RAARA"}` |
| Original Vite process | **PASS** — listening on `127.0.0.1:5173`, PID 28228 |
| Frontend HTTP response | **PASS** — HTTP 200; original RAARA page served |
| Vite `/api` proxy connectivity | **PASS** — original dashboard displayed “Backend connected” |
| Browser registration/login/dashboard | **PASS** — a disposable student was registered and logged in against the isolated DB; dashboard loaded |
| Browser console errors/warnings | **PASS** — none observed in the app tab |
| OpenAI-dependent browser acceptance | **BLOCKED** — no key and no authorization for paid calls yet |

The disposable account identifier and password are intentionally omitted. The app was tested in the original frontend at `http://127.0.0.1:5173/`.

## Live AI, ingestion, and RAG outcomes

| Check | Result |
|---|---|
| Model access check | **NOT TESTED** — would contact OpenAI |
| Minimal embedding request | **NOT TESTED** — would be billable |
| Minimal Responses API request | **NOT TESTED** — would be billable |
| Synthetic PDF upload/embedding/indexing | **NOT TESTED** — requires OpenAI embedding call |
| Live retrieval and generated supported answer | **NOT TESTED** |
| Live citation/source/page rendering | **NOT TESTED** |
| Live follow-up generation | **NOT TESTED** |
| Live unsupported-question abstention | **NOT TESTED** |
| Browser conversation reload/persistence/logout/login | **NOT TESTED** |
| Token usage/API cost | **NOT AVAILABLE** — no live requests |

The existing mocked synthetic pipeline is covered by the backend tests, but that does not establish real model access, semantic faithfulness, or live browser RAG behavior.

## Current blockers and required owner action

The app currently runs without an OpenAI key so health, registration, login, and dashboard have been verified. PDF embedding and AI chat cannot be tested until a key is supplied. The key must remain local; do not send it through this conversation.

In a **local PowerShell window**, stop only the isolated no-key backend, enter the key via `Read-Host -AsSecureString`, then start the backend with the temporary paths below. Keep the backend window open. The prompt will not echo the key:

```powershell
Stop-Process -Id 32148 -Confirm:$false
Set-Location C:\prompt_mini_proj\backend
$root = 'C:\Users\Pratik Kalloli\AppData\Local\Temp\RAARA_LIVE_ACCEPTANCE_20261114_141801_aa135e6c'
$apiKey = Read-Host 'Enter the OpenAI API key privately (input is hidden)' -AsSecureString
$apiKeyPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($apiKey)
try { $env:OPENAI_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($apiKeyPtr) }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($apiKeyPtr) }
$dbPath = (Join-Path $root 'raara_test.db').Replace('\','/')
$env:DATABASE_URL = "sqlite:///$dbPath"
$env:CHROMA_PERSIST_DIR = Join-Path $root 'chroma_data'
$env:UPLOAD_DIR = Join-Path $root 'uploads'
$env:JWT_SECRET_KEY = (& .\.venv311\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))").Trim()
$env:OPENAI_CHAT_MODEL = 'gpt-4.1-mini'
$env:OPENAI_EMBEDDING_MODEL = 'text-embedding-3-small'
```

Before any paid API request, send a separate approval in this conversation confirming both that the key was entered locally and that you approve the live acceptance calls. Those calls include one small embedding and one small Responses API smoke request, plus the embedding and chat requests needed for the synthetic-PDF upload, supported question, follow-up, and unsupported-question browser checks. The API key itself is neither needed nor wanted here.

Once the owner confirms, start the configured backend in that same PowerShell window:

```powershell
.\.venv311\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Because that restart creates a fresh JWT secret, sign back into the already-registered disposable student in the open browser before continuing acceptance.

The Vite frontend is still running on port 5173 (PID 28228). If it is stopped, restart it with:

```powershell
Set-Location C:\prompt_mini_proj\frontend
npm.cmd run dev -- --host 127.0.0.1
```

## Stop and cleanup commands

The currently running no-key backend can be stopped with `Stop-Process -Id 32148 -Confirm:$false`; Vite can be stopped with `Stop-Process -Id 28228 -Confirm:$false`. If PIDs have changed, first check the listener on the corresponding port and confirm its command line belongs to this RAARA run.

After all live/browser acceptance is complete and the report is finalized, remove only the named temporary acceptance directory (this permanently deletes its disposable test account, database, vectors, upload, logs, and synthetic PDF):

```powershell
$root = 'C:\Users\Pratik Kalloli\AppData\Local\Temp\RAARA_LIVE_ACCEPTANCE_20261114_141801_aa135e6c'
$resolvedRoot = [IO.Path]::GetFullPath($root)
$expectedParent = [IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA '..\Local\Temp'))
if (-not $resolvedRoot.StartsWith($expectedParent, [StringComparison]::OrdinalIgnoreCase)) { throw 'Unexpected cleanup target; refusing removal.' }
Remove-Item -LiteralPath $resolvedRoot -Recurse -Confirm
```

Do not run cleanup until acceptance is complete and the report has been updated.

## Classification

- **Application preparation:** PASS.
- **Automated regression:** PASS.
- **Original frontend/backend health and browser login:** PASS.
- **Live OpenAI integration:** BLOCKED pending local key entry and explicit approval.
- **PDF/RAG browser acceptance:** BLOCKED pending live OpenAI configuration and approval.
- **Production data safety:** PASS; only isolated temporary storage was used.
