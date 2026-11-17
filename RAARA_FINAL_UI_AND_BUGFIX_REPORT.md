# RAARA Final UI and Bug-Fix Report

**Project:** `C:\prompt_mini_proj`  
**Date:** 2026-11-14  
**Overall result:** **PASS WITH LIMITATIONS**

## Summary

The original React and FastAPI application was preserved. Greetings now bypass retrieval and model generation, attendance spellings are corrected and expanded for retrieval only, new conversations are no longer saved just because a user opens the composer, selected conversations restore after refresh, and the interface has a consistent readability and responsive-navigation pass.

Regression and acceptance results:

- Backend suite: **PASS — 182 passed, 0 failed**.
- Frontend unit suite: **PASS — 8 passed, 0 failed**.
- Mocked Playwright UI suite: **PASS — 5 passed, 0 failed**.
- Frontend production build: **PASS**.
- Live isolated synthetic attendance acceptance: **PASS** for registration, greeting, PDF upload/index, misspelled attendance retrieval, Gemini answer, canonical page/document metadata, follow-up, refresh persistence and conversation switching.
- Browser console: the initial acceptance found a missing-favicon 404. The RAARA favicon was added; a subsequent page-load check reported **zero console errors**.

All live documents and users used for this work were in the isolated acceptance store. The attendance value in the live acceptance PDF was fictional and clearly labelled as test-only. It is not a PES University policy.

## Bugs found and fixes

### Greetings incorrectly returned an academic abstention

**Root cause:** `AcademicChatService.answer` always called the retriever and generator. A greeting with no matching passage consequently followed the academic `NOT_FOUND` path.

**Fix:** The chat service recognizes exact greetings, thanks, introductions and help requests before retrieval. It returns a local `CONVERSATIONAL` response with empty evidence/source arrays and `NOT_APPLICABLE` citation status. It makes no embedding, retrieval or Gemini generation call. The API persists the greeting as a normal user/assistant exchange when a conversation ID is supplied. This behavior is independent of prompt configuration A, B or C. The model-facing schema remains restricted to the four academic answer statuses.

### Misspelled and informal attendance queries were embedded verbatim

**Root cause:** The retriever embedded the input question exactly as written. Queries such as `whats the attendence` lacked the standard spelling and related retrieval terms, making a relevant attendance passage less likely to rank high enough.

**Fix:** Retrieval now maps the requested common variants (`attendence`, `attendace`) to `attendance` and adds neutral academic search terms for attendance requirements, minimum percentage, criteria and examination eligibility. This expansion is sent only to the embedding service; the original question remains the `RetrievalResult.question`, model-visible question and persisted conversation text. Top-K, the cosine-distance threshold, Chroma collection selection and evidence/citation requirements were not weakened or changed. No percentage or policy fact is added by normalization.

**Observed live result:** `whats the attendence` retrieved the matching synthetic passage. The final persisted response was `PARTIALLY_SUPPORTED` because the source remains unverified; citation validation was `VERIFIED`, and the application-built evidence identified the uploaded synthetic document, page 1 and `unverified` status. A self-contained follow-up retrieved the same passage.

### Empty conversation entries and refresh selection

**Root cause:** The sidebar's “New conversation” action immediately created a database row before a user sent a message. A failed first request could also leave a zero-message conversation. The selected conversation ID lived only in React state, so a browser refresh returned to an empty assistant view even though server history remained saved.

**Fix:** “New conversation” now creates only a local draft. The server conversation is created on the first submitted message. If that first exchange fails, the UI reads the persisted message count and deletes the new record only when the server confirms it is empty; if the server cannot be reached, the record is retained so a retry cannot discard a possibly persisted exchange. The selected ID is kept in tab-scoped session storage and restored from the owned conversation endpoint on reload. Existing history counts remain calculated by the backend from persisted message rows; they were not replaced with a frontend estimate.

The existing backend conversation tests already cover ordered message persistence, idempotent retries, owner scoping, rename, delete, message counts and bounded follow-up context. New API tests confirm greetings persist as a two-message exchange for prompts A/B/C.

### Dense typography and narrow-screen navigation

**Root cause:** The shared styles used many 9–13px text sizes, tight metadata rows and small message padding. The mobile stylesheet hid all workspace navigation links.

**Fix:** Shared typography, paragraph line-height, card/form/chat spacing, evidence readability, focus indicators, wrapping and control sizing were improved across authentication, dashboard, assistant, history, documents, profile and admin views. At mobile widths the sidebar now provides a horizontally scrollable, visible workspace navigation. Responsive browser tests cover 1365px, 768px and 375px widths and assert there is no page-level horizontal overflow.

### Browser favicon 404

**Root cause:** `frontend/index.html` did not declare an icon, so Chrome requested `/favicon.ico` and Vite returned 404.

**Fix:** Added a small RAARA SVG favicon and linked it from the document head. The subsequent browser page-load check reported no console errors.

## Files created and modified

**Backend:**

- Modified `backend/app/services/chat.py` — local conversational response and retrieval-only question context.
- Modified `backend/app/services/retriever.py` — attendance typo correction and neutral query expansion.
- Modified `backend/app/services/generator.py` — added the `CONVERSATIONAL` response status while keeping the generated academic output schema limited to A/B/C academic statuses.
- Created `backend/tests/test_chat_behaviors.py` — prompt-independent greeting bypass, spelling normalization and safe no-evidence abstention tests.
- Modified `backend/tests/test_retriever.py` — spelling variants retrieve one identical synthetic page-level evidence passage without changing thresholds.
- Modified `backend/tests/test_conversations.py` — greeting persistence tests for prompt A, B and C.

**Frontend:**

- Modified `frontend/src/App.jsx` — conversational label, transient new conversations, safe cleanup of confirmed empty first attempts, mobile navigation markup and selected-conversation restoration.
- Modified `frontend/src/index.css` — base readability and keyboard focus treatment.
- Modified `frontend/src/App.css` — spacing, typography, chat/history/forms/admin refinements and desktop/tablet/mobile layouts.
- Modified `frontend/index.html` — RAARA icon and theme color metadata.
- Created `frontend/public/raara-icon.svg`.
- Modified `frontend/package.json` — added `test:e2e` script; existing Playwright dev dependency was reused.
- Created `frontend/e2e/ui.acceptance.cjs` — API-mocked browser UI tests; no Gemini/OpenAI requests.

**Report:**

- Created `RAARA_FINAL_UI_AND_BUGFIX_REPORT.md`.

The live synthetic PDF and one-off live acceptance script are under the ignored `backend/.raara_live_acceptance_20261114/` directory.

## Test and acceptance results

### Backend automated suite

**PASS — 182 passed, 0 failed.** Python 3.11.18, WSL `.venv-wsl311`. The test process used blank Gemini/OpenAI keys, the restored tokenizer cache, and fresh temporary SQLite, ChromaDB and upload paths under `/tmp/raara-ui-regression-final-20261114/`.

The suite includes greeting handling and persistence for all three prompts, typo/query expansion, same-page synthetic attendance retrieval, existing citation validation, retrieval thresholds, authentication, ingestion, document review, Gemini mock contracts and conversation persistence.

### Frontend automated tests

| Command | Result |
|---|---|
| `npm test` | **PASS — 8 passed, 0 failed** |
| `npm run test:e2e` | **PASS — 5 passed, 0 failed** |
| `npm run build` | **PASS** — Vite 6.4.5 |

The Playwright suite stubs every `/api` route and covers registration, login, dashboard/service status, greeting display and persisted history pair, history switching after reload, rename, delete confirmation, message counts, empty-first-chat cleanup, local new-conversation behavior, and viewport overflow at desktop/tablet/mobile sizes. These automated UI tests make no live model calls.

### Isolated live Gemini/PDF acceptance

The browser workflow used Chrome with a disposable student and a one-page PDF labelled **SYNTHETIC TEST DOCUMENT — NOT AN OFFICIAL UNIVERSITY POLICY**. Its only policy-like statement was a fictional minimum attendance threshold of 72 percent, written as invented test content.

| Step | Result |
|---|---|
| Registration and login | **PASS** |
| `hello` greeting | **PASS** — `CONVERSATIONAL`, no evidence, no fake citations; backend unit tests verify retriever and generator are not invoked |
| Synthetic PDF upload/extraction/indexing | **PASS** — 1 page, 1 chunk, indexed, still `unverified` |
| `whats the attendence` | **PASS** — live Gemini embedding and answer generated from the uploaded test passage |
| Returned answer/source | **PASS** — fictional 72 percent appears; status `PARTIALLY_SUPPORTED`; citation status `VERIFIED`; actual document name and page 1 returned; source remains unverified |
| `what about minimum attendance?` follow-up | **PASS** — same synthetic evidence/page returned |
| Refresh and saved history | **PASS** — greeting, both user questions and assistant responses remained available |
| Switch conversations | **PASS** — opened the original six-message synthetic test conversation after starting a second conversation |
| Browser console | **PASS after correction** — the full workflow's final console check initially found only the missing-favicon 404, after all its workflow assertions had passed. The favicon was added, and a subsequent Chrome page-load check recorded zero console errors. The full model-backed flow was not repeated because the uploaded PDF's hash is now correctly treated as a duplicate. |

The final read-only check of the isolated database confirmed the synthetic document was indexed with `verification_status=unverified`, the greeting response had `CONVERSATIONAL` and no evidence, and both attendance responses had `PARTIALLY_SUPPORTED`, `VERIFIED` citation metadata, and a page-1 reference to that synthetic source. This does not verify any actual university regulation.

## Gemini integration

Provider configuration was preserved: Gemini, chat model `gemini-3.5-flash-lite`, embedding model `gemini-embedding-001`, 768 dimensions, and the provider-specific Chroma collection. The previous phase's structured-output correction (`response_json_schema`) remains in place. The live PDF acceptance used the configured Gemini integration. No OpenAI calls were made. No keys or tokens were printed or returned.

## Known limitations and verification classification

| Area | Status | Limitation |
|---|---|---|
| Greeting behavior | **PASS** | Only the listed exact greetings, thanks, introduction and help phrases are routed conversationally; broader small-talk handling is not intended. |
| Attendance typo retrieval | **PASS** | Corrects the requested variants and expands attendance queries. This is not general-purpose spell correction. |
| Evidence/citation correctness for the synthetic test | **PASS** | Source identity/page metadata is validated against retrieved data. |
| Semantic faithfulness | **NOT TESTED** | Citation validation does not prove every generated claim is entailed; semantic faithfulness remains `NOT_VERIFIED`. |
| Real university attendance policy | **NOT TESTED** | No official policy was used or represented by the synthetic fixture. |
| Live unsupported attendance question | **NOT TESTED** in this acceptance run | The automated suite still verifies no-evidence abstention without calling Gemini. |
| OpenAI integration | **NOT TESTED** | No live OpenAI calls were made. |
| Responsive layouts | **PASS** | Mocked browser checks found no horizontal page overflow at the tested desktop, tablet and mobile widths. |

## Data safety

- Backend tests used fresh isolated SQLite, ChromaDB and upload paths under `/tmp`.
- Live PDF acceptance used the existing explicitly isolated acceptance paths under `%LOCALAPPDATA%\Temp\RAARA_LIVE_ACCEPTANCE_20261114_141801_aa135e6c\`.
- The synthetic PDF is stored in the ignored acceptance directory.
- Production SQLite, production ChromaDB, production uploads, production accounts/conversations, official evidence approvals and Phase 9A assets were not accessed or modified.
- Automated tests used blank provider keys and mocks. The separate live acceptance used Gemini only for the authorized synthetic upload and its two academic questions; greetings did not call the model.

## Exact verification commands

### Backend full suite (WSL PowerShell invocation)

```powershell
wsl.exe -e bash -lc 'cd /mnt/c/prompt_mini_proj/backend && root=/tmp/raara-ui-regression-final-20261114 && mkdir -p "$root/chroma" "$root/uploads" && env DATABASE_URL="sqlite:////tmp/raara-ui-regression-final-20261114/test.db" CHROMA_PERSIST_DIR="$root/chroma" UPLOAD_DIR="$root/uploads" AI_PROVIDER=gemini GEMINI_API_KEY= OPENAI_API_KEY= JWT_SECRET_KEY="raara-ui-test-signing-secret-material-2026" TIKTOKEN_CACHE_DIR="/mnt/c/Users/Pratik Kalloli/AppData/Local/RAARA/tiktoken-cache" .venv-wsl311/bin/python -m pytest tests -v'
```

### Frontend tests and build

```powershell
Set-Location C:\prompt_mini_proj\frontend
npm test
npm run test:e2e
npm run build
```

The UI test requires the local Vite site at `http://127.0.0.1:5173/` and installed Chrome. It mocks application API traffic and never requires model credentials.

### Live synthetic UI acceptance

The successful run used:

```powershell
node backend/.raara_live_acceptance_20261114/ui_live_acceptance.cjs
```

This command makes Gemini requests for the isolated synthetic PDF upload and the two attendance questions. Repeating it against the same isolated acceptance database will correctly encounter duplicate detection; use a fresh isolated database, Chroma directory and upload directory for a repeat run. Do not use it as an automated regression command or substitute a real university document.
