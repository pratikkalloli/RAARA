# RAARA Final Release Completion Report

**Date:** 2026-11-14  
**Project:** `C:\prompt_mini_proj`  
**Release result:** **PASS WITH LIMITATIONS**

## Summary

The student-facing RAARA site is live at [http://127.0.0.1:5173/](http://127.0.0.1:5173/), backed by the Gemini-enabled API on port 8000. The frontend and API use Vite's `/api` proxy. Backend health, AI health, the frontend, and the frontend-to-backend proxy returned HTTP 200 in the final check.

The generator's Gemini request compatibility issue was diagnosed and fixed. A live embedding request and a live structured generation request both succeeded after the corrections. Synthetic PDF upload, Gemini indexing and retrieval, citation metadata validation, a supported answer, follow-up answer, and persisted conversation messages were exercised against isolated acceptance storage. Production SQLite, ChromaDB and upload storage were not used.

Automated regression results are **139 backend tests passed**, **8 frontend tests passed**, and a successful production frontend build. Browser checks verified page rendering and registration, login, dashboard and logout. The extended Playwright upload/chat flow reached the indexed synthetic document and persisted a two-turn conversation, but its script did not exit with its final result summary; full browser workflow acceptance is therefore recorded as **PARTIALLY VERIFIED**, not a clean end-to-end pass. Semantic faithfulness was not independently verified.

## Gemini diagnosis and correction

The configured credential was checked without displaying or logging its value. No key was copied into the frontend or test output.

Two provider request incompatibilities were found:

1. The Gemini adapter sent the structured answer schema through `response_schema`. The API rejected its `additional_properties` representation with HTTP **400**, Google code **`INVALID_ARGUMENT`**. The safe provider message identified `generation_config.response_schema` and the unsupported field. The Gemini adapter now passes the schema through `response_json_schema`, the API's JSON Schema field.
2. With schema submission corrected, `gemini-2.5-flash-lite` returned HTTP **404**, Google code **`NOT_FOUND`**, stating the model was no longer available to this account/new users and recommending a newer model. The configured chat model was changed to `gemini-3.5-flash-lite` in the local backend `.env` and the application default/example. This model supports structured output per Google's model documentation.

| Diagnostic call | Safe captured details |
|---|---|
| Old schema field | Exception `ClientError`; HTTP 400; Google status `INVALID_ARGUMENT`; model `gemini-2.5-flash-lite`; safe message: `Invalid JSON payload received. Unknown name "additional_properties" at 'generation_config.response_schema': Cannot find field.` |
| Old model name | Exception `ClientError`; HTTP 404; Google status `NOT_FOUND`; model `gemini-2.5-flash-lite`; safe message: `This model models/gemini-2.5-flash-lite is no longer available to new users. Please update your code to use models/gemini-3.5-flash-lite ...` |

After both changes, one minimal call through RAARA's existing generator succeeded with `gemini-3.5-flash-lite`, JSON MIME type, the existing strict answer JSON schema passed as `response_json_schema`, 1,200 maximum output tokens, a 30-second timeout and one retry. The generated structured answer used the supplied synthetic unverified passage. A separate live embedding call to `gemini-embedding-001` succeeded and returned one 768-dimensional vector. No further model-availability retries were made after success.

The request field and model availability were checked against Google's [Generate Content API](https://ai.google.dev/api/generate-content), [structured output guidance](https://ai.google.dev/gemini-api/docs/structured-output), and [Gemini 3.5 Flash-Lite model documentation](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite). Google's model page describes structured outputs as supported.

## Automated verification

| Check | Result |
|---|---|
| Full backend suite | **PASS — 139 passed, 0 failed** |
| Backend environment | WSL `.venv-wsl311`, Python 3.11.18 |
| Backend command | `.venv-wsl311/bin/python -m pytest tests -v` |
| Backend test storage | Isolated `/tmp/raara-final-regression-rerun-20261114/` paths for SQLite, ChromaDB and uploads |
| External credentials during tests | Gemini and OpenAI keys blank; provider calls mocked |
| Tokenizer cache | `TIKTOKEN_CACHE_DIR=/mnt/c/Users/Pratik Kalloli/AppData/Local/RAARA/tiktoken-cache` |
| Frontend tests | **PASS — 8 passed, 0 failed** (`npm test`) |
| Frontend production build | **PASS** (`npm run build`, Vite 6.4.5) |

The backend suite completed in **133.19 seconds**. The frontend checks were rerun after adding Playwright as a development-only dependency. Playwright installation reported **0 vulnerabilities**. Automated tests made no paid API calls.

## Live Gemini probes

| Probe | Result |
|---|---|
| Gemini embedding | **PASS** — `gemini-embedding-001`, one vector, 768 dimensions |
| Gemini structured generation after fixes | **PASS** — `gemini-3.5-flash-lite`, structured JSON answer generated from the supplied synthetic unverified context |
| Previous generation failures | HTTP 400 `INVALID_ARGUMENT` for schema encoding; then HTTP 404 `NOT_FOUND` for unavailable `gemini-2.5-flash-lite`; both corrected before the successful probe |
| OpenAI live calls | **None** |

Credentials were not printed, logged, or returned in API output.

## Isolated live PDF and chat acceptance

Acceptance used a temporary directory under `%LOCALAPPDATA%\Temp\RAARA_LIVE_ACCEPTANCE_20261114_141801_aa135e6c\`. Its SQLite database, ChromaDB directory and upload directory were confirmed from the running process environment. They are separate from production paths. The active provider-specific Chroma collection is `raara_documents_gemini_gemini-embedding-001_768d`.

The synthetic test PDF is prominently labelled **NOT OFFICIAL UNIVERSITY POLICY**. It contains a fictional attendance value and is not an institutional regulation.

| Acceptance item | Result |
|---|---|
| Disposable student registration and login | **PASS** |
| Synthetic PDF upload, extraction and indexing | **PASS** — one page, one chunk, indexed |
| Document verification handling | **PASS** — remained `unverified`; no approval was applied |
| Duplicate detection | **PASS** — a repeat upload of an identical PDF hash returned HTTP 409 |
| Provider-specific Chroma collection | **PASS** — configured collection confirmed; indexed document was retrieved in chat |
| Gemini answer generation | **PASS** — returned the fictional value present in the synthetic PDF |
| Evidence/source metadata | **PASS** — actual document identity and page 1 were returned from retrieved metadata |
| Citation validation | **PASS** — live response reported citation validation `VERIFIED` against the retrieved context |
| Unverified-source labeling | **PASS** — answer status was `PARTIALLY_SUPPORTED` and source remained explicitly unverified |
| Follow-up | **PASS** for a self-contained follow-up repeating the requested fact; an earlier vague follow-up correctly abstained as `NOT_FOUND` |
| Conversation persistence | **PASS** — both turns persisted (four user/assistant messages) and conversation history was available through the API |
| Unsupported-question live abstention | **NOT TESTED** with the live generator in this final acceptance sequence |
| Semantic faithfulness | **NOT VERIFIED** independently |

The answer was limited to the content of the synthetic test PDF. No claim about an actual university policy was tested or made.

## Browser acceptance

Playwright was added as a development-only frontend dependency and run with the installed Chrome browser; Computer Use was not used.

| Browser check | Result |
|---|---|
| Load `http://127.0.0.1:5173/`, HTTP 200, RAARA title and sign-in view | **PASS** |
| Student registration form rendering | **PASS** |
| Disposable account registration, login and dashboard | **PASS** |
| Backend connected status | **PASS** in the captured dashboard view |
| Logout and access-token clearing | **PASS** — separate bounded Playwright browser check |
| Synthetic PDF/chat browser flow | **PARTIALLY VERIFIED** — isolated database records show the browser test document indexed and the two question/answer turns persisted; the longer Playwright script did not finish by emitting its final JSON result, so its overall workflow is not marked PASS |
| Browser console error audit | **NOT VERIFIED** — the interrupted long script produced no final console summary |

The dashboard was rendered in Chrome and a screenshot was saved under the ignored isolated acceptance directory. The HTTP/API checks independently verified the live upload and chat behaviors. Because the longer browser script did not exit cleanly, report the integrated visual browser acceptance as partial rather than complete.

## Running application and storage safety

At final verification, one backend instance and one loopback-only Vite instance remained running. The backend process uses the isolated acceptance paths listed above. Vite on port 5173 proxies `/api` to `http://127.0.0.1:8000`. The extra wildcard-bound Vite process for this same project was stopped; the loopback-only process remains and responds HTTP 200.

Final endpoint checks:

| URL | Result |
|---|---|
| `http://127.0.0.1:8000/api/health` | HTTP 200 |
| `http://127.0.0.1:8000/api/health/ai` | HTTP 200 |
| `http://127.0.0.1:5173/` | HTTP 200 |
| `http://127.0.0.1:5173/api/health` (Vite proxy) | HTTP 200 |

No production SQLite, ChromaDB or upload data was used or modified. Official evidence approvals and Phase 9A assets were left unchanged. Acceptance PDFs, temporary accounts and conversations are in isolated acceptance storage only.

## Implemented features retained

The existing application includes Gemini and optional OpenAI provider adapters; model/dimension-specific Gemini Chroma storage; document upload, extraction and chunking; authentication and role-aware routes; administrator review/synchronization; ownership-aware document operations; persisted conversations and bounded follow-up context; structured answers with application-built citations; citation/evidence validation; A/B/C prompt configurations; and the frontend dashboard, assistant, document library, history, profile and administrator views. This is an implementation inventory, not a claim that every edge case was live-tested.

## Final blocker-resolution file changes

This release fix changed `backend/app/services/generator.py` (Gemini JSON Schema request field), `backend/app/config.py` (chat model default), `backend/.env.example` (documented Gemini model), `backend/.env` (chat model setting only; credential value was neither changed nor shown), `backend/tests/test_gemini_provider.py` (request contract assertion), `frontend/package.json` and `frontend/package-lock.json` (Playwright development dependency), and this completion report. The one-off Playwright script and synthetic PDFs are under the ignored isolated acceptance directory.

## Remaining limitations

1. Full browser workflow is **PARTIALLY VERIFIED** because the extended Playwright run did not emit a clean completion summary, although isolated acceptance metadata confirms the PDF was indexed and a two-turn conversation persisted. Its console-error assertion is not verified.
2. Semantic faithfulness was not independently evaluated; valid citations prove citation-to-context matching, not that every answer claim is semantically entailed.
3. No live unsupported-question / abstention scenario was completed after the Gemini corrections.
4. The acceptance corpus was deliberately synthetic and must not be interpreted as official PES University content.
5. Live OpenAI integration was not tested.

## Exact commands to start the isolated site

The commands below use a fresh temporary test database, ChromaDB and upload directory. They do not change production storage. Gemini credentials are loaded by the backend from `backend/.env`; do not print or copy them into the frontend. The current servers are already running, so do not start duplicates on the same ports.

### WSL terminal — backend, Python 3.11

```bash
cd /mnt/c/prompt_mini_proj/backend
root="/tmp/raara-final-site-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$root/chroma" "$root/uploads"
export DATABASE_URL="sqlite:////${root#/}/raara.db"
export CHROMA_PERSIST_DIR="$root/chroma"
export UPLOAD_DIR="$root/uploads"
export AI_PROVIDER=gemini OPENAI_API_KEY=
export JWT_SECRET_KEY="$(.venv-wsl311/bin/python -c 'import secrets; print(secrets.token_urlsafe(48))')"
export TIKTOKEN_CACHE_DIR="/mnt/c/Users/Pratik Kalloli/AppData/Local/RAARA/tiktoken-cache"
unset GEMINI_API_KEY
.venv-wsl311/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### PowerShell terminal — frontend

```powershell
Set-Location C:\prompt_mini_proj\frontend
$env:RAARA_API_PROXY_TARGET = 'http://127.0.0.1:8000'
npm run dev -- --host 127.0.0.1 --port 5173
```

Open **[http://127.0.0.1:5173/](http://127.0.0.1:5173/)**. For a fresh verification instance, start the backend first and confirm its health endpoint before starting Vite.
