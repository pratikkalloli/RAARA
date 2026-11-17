# RAARA Phase 6E — System Integration and Acceptance Report

**Final classification: PASS WITH LIMITATIONS**

Core automated regression tests and isolated API acceptance checks passed. Live OpenAI integration and browser-based frontend acceptance were not completed. The RAG acceptance checks used deterministic local substitutes and do not establish semantic faithfulness.

## 1. Environment and isolation

- Project: `C:\prompt_mini_proj`
- Backend interpreter: `backend\.venv311`, Python 3.11.9
- Backend: FastAPI; frontend: React + Vite
- `backend\.env` was absent at inspection time. No database, Chroma, JWT, or OpenAI overrides were present in the inspecting process. Secret values were not printed.
- Default settings resolve SQLite to `backend\raara.db` and ChromaDB to `backend\chroma_data`.
- The existing SQLite database was inspected read-only: **0 users, 0 documents, 0 conversations, and 0 conversation messages**. `documents\raw` existed and contained 0 files.
- Acceptance writes used fresh temporary SQLite, ChromaDB, and upload directories. The existing database and configured Chroma directory were not used for acceptance writes.
- Synthetic PDFs were explicitly labelled as test documents, not official regulations.
- No application source files were changed. This report is the only project file added for Phase 6E.

## 2. Baseline regression results

| Check | Result |
|---|---:|
| Backend `pytest -v` | **105 passed, 0 failed** |
| Frontend `npm test` | **7 passed, 0 failed** |
| Frontend `npm run build` | **Passed** |

Backend tests ran with process-only `DATABASE_URL`, `CHROMA_PERSIST_DIR`, and `UPLOAD_DIR` values pointing to a fresh temp directory. This isolated FastAPI’s import-time schema initialization from the existing database. Frontend tests use mocked API responses; the build verifies compilation and bundling only.

The existing backend suite includes tests for authentication and authorization, upload/ingestion, document review, vector synchronization, retrieval, citation validation, prompt injection handling, A/B/C prompts, and conversation persistence. These are automated regression tests, not proof of live OpenAI behavior.

## 3. Isolated API acceptance results

**Result: 48 checks passed.** The harness used authenticated FastAPI requests through `TestClient`, a temporary database and persistent Chroma collection, synthetic PDFs, deterministic local embeddings, and a deterministic evidence-only generator. It made **0 OpenAI calls**.

### Authentication and authorization — PASS

- Student registration assigned the student role.
- Duplicate username and duplicate email registrations were rejected.
- Public registration with `role=admin` was rejected.
- Username and email login both succeeded for the synthetic student and resolved to the same account.
- The documented administrator bootstrap entry point created the isolated test administrator; login and `/api/auth/me` returned the administrator role.
- Invalid, expired, and inactive-user tokens were rejected.
- Student requests to administrator review and synchronization endpoints were denied.

Invalid-password behavior is covered by the backend regression tests. Test accounts were synthetic and credentials are intentionally omitted.

### Upload, ownership, and review — PASS

- Unauthenticated and invalid-token uploads were rejected.
- Unsupported file type, invalid PDF, and text-empty PDF uploads were rejected. The database remained without records for those failures.
- A valid two-page synthetic PDF was extracted and indexed. The upload response reported the expected page count and indexed/unverified state.
- The uploader could list the document; a second student could not see it.
- Duplicate content was rejected.
- Administrator pending-list, verification, reviewer identity, review timestamp, review note, and synchronized Chroma metadata checks passed.
- Invalid document ID and repeated verification transition returned the expected errors.
- A second synthetic document was rejected by an administrator and then excluded from retrieval.
- A one-time synchronization failure was injected in the isolated store. The decision remained visible with synchronization pending; retry synchronized metadata without changing the chunk count.

### Retrieval, responses, and citations — PASS WITH MOCKED GENERATION

- The deterministic local embedding substitute retrieved the synthetic deadline, attendance, and student-portal passages through authenticated `/api/chat` requests. Returned answers, evidence pages, and source document names matched the synthetic fixture for the assertions performed.
- A question about an absent hostel curfew returned `NOT_FOUND` with no evidence.
- A fabricated passage/document/page reference injected by the deterministic test generator was rejected by the integrated citation verifier, which returned `NOT_FOUND` and no sources.
- A synthetic document containing prompt-injection text was used in a chat request. The deterministic test generator returned the selected portal fact and did not echo the injected instruction. **This does not test an LLM’s resistance to prompt injection.**
- A cross-page question returned the expected deadline text. The harness did not assert that evidence from both pages was present; complete multi-page evidence coverage is therefore **NOT TESTED**.
- The library-fine query was performed after the only synthetic library-fine document had been rejected. A separate absent-library-fine query against a corpus that never contained that fact was **NOT TESTED** in the isolated harness.
- Unverified-source chat behavior, conflicting versions in a live request, and questions requesting hidden prompts/secrets were not exercised by the isolated API harness. Related unit-level behavior is present in the existing backend suite where covered.

Citation identity validation and semantic faithfulness are distinct. Citation tests establish that selected references match retrieved passages; they do **not** prove that every natural-language claim is entailed by those passages.

### Conversation history and idempotency — PASS

- A persistent exchange stored the user question and assistant response, including structured response and evidence.
- Replaying the same request with the same idempotency key returned the prior response without duplicating the exchange.
- A new key created a new exchange.
- Another student and the administrator could not read or delete the student’s conversation.
- A failed mocked generation returned an error and left the conversation without a successful exchange.
- Deleting an owned conversation removed its messages while leaving the user’s documents intact.

The isolated API harness did not separately verify activity ordering or persistence across a logout/login cycle; the relevant endpoint behavior is covered by regression tests where indicated.

## 4. Frontend acceptance

Frontend test command and production build passed, but those checks do not exercise the rendered application workflows.

**Browser workflow result: NOT TESTED.** The browser automation tool stopped before interacting with the application because it could not establish the current browser URL safely. A separate isolated browser-server attempt also did not provide a usable test environment: the temporary backend script could not import `app`, and Vite moved to port 5174 because port 5173 was already occupied. No application UI actions were completed. The temporary Vite launcher was stopped; the existing listener on port 8000 was left untouched.

### Manual browser acceptance checklist — NOT TESTED

Use only an isolated backend database/Chroma/upload path, synthetic accounts, and the labelled synthetic PDF. Check each item in the browser and record the result:

- [ ] Student registration and login; dashboard loads the authenticated profile.
- [ ] Student upload, loading/error feedback, unverified status, and document list refresh.
- [ ] A student cannot see another student’s document.
- [ ] Create a conversation, submit chat, and inspect status, evidence, citation page, and source metadata.
- [ ] Select/reload conversation history and verify message order and structured evidence.
- [ ] Retry the same failed chat request and confirm the same idempotency key is reused.
- [ ] Open a conversation delete confirmation and verify cancel leaves it intact. Confirming deletion is destructive and requires an explicit test-time approval.
- [ ] Student logout clears visible user-specific state; signing in as another student does not reveal cached data.
- [ ] Student navigation or direct `/admin` URL does not expose admin actions.
- [ ] Expired-token and API-error states are shown clearly.
- [ ] Administrator login, role-aware dashboard, pending queue, verification, and rejection.
- [ ] Administrator synchronization-failure message and retry action.
- [ ] Administrator logout clears the session and returns to the signed-out view.
- [ ] Confirm no duplicate chat submission occurs while a request is pending.

## 5. Live OpenAI integration

**Result: NOT TESTED.** No OpenAI API key was configured in the current process, and no live calls were authorized or made. The API acceptance run used deterministic local embedding and generation substitutes. No OpenAI model invocation, token usage, latency, or live RAG result is claimed.

### Future live OpenAI validation checklist

Run only after credentials and live-call authorization are available. Keep credentials out of output and logs.

- [ ] Use a fresh temporary SQLite database, Chroma directory, and upload directory.
- [ ] Confirm configured embedding and chat model identifiers without displaying credentials.
- [ ] Upload and administrator-verify only the synthetic two-page PDF.
- [ ] Confirm an embedding request occurs during ingestion and record the model, response status, and latency.
- [ ] Ask the deadline, attendance, and portal questions; compare each answer to its exact PDF sentence, evidence text, page, source name, and verification metadata.
- [ ] Ask hostel-curfew and library-fine questions and check for abstention without invented policy.
- [ ] Ask a question spanning both pages and verify each answer clause has matching evidence from the correct page.
- [ ] Test a question containing a request for secrets and the prompt-injection text in the synthetic PDF. Verify no credentials, system prompt, or unsupported regulation is returned.
- [ ] Record model identifiers, prompt type, latency, token usage where available, and sanitized errors. Do not claim semantic faithfulness solely from valid citations.

## 6. Defects and fixes

- **Application defects reproduced:** None in the exercised automated and isolated API checks.
- **Application fixes applied:** None; no source behavior was changed.
- **Test-environment limitation:** The browser acceptance harness did not start its isolated backend because Python could not resolve the `app` package from the temporary script location. This was a harness setup failure, not a reproduced application defect. The browser automation safety check separately halted before UI interaction.

## 7. Commands and exact results

Backend baseline (run from `C:\prompt_mini_proj\backend`):

```powershell
.\.venv311\Scripts\python.exe -m pytest -v
```

Result: **105 passed, 0 failed**. For isolation during this run, the process environment set `DATABASE_URL`, `CHROMA_PERSIST_DIR`, and `UPLOAD_DIR` to a newly generated directory under `$env:TEMP\raara-phase6e-*` before invoking pytest.

Frontend (run from `C:\prompt_mini_proj\frontend`):

```powershell
npm test
npm run build
```

Results: **7 passed, 0 failed**; production build **passed**.

The isolated API acceptance harness was run inline with `backend\.venv311\Scripts\python.exe -` and process-only temporary database, Chroma, upload, and JWT settings. Its 48 assertion names/results are recorded in Sections 3–4 above; the inline harness body was not retained as a project test file.

## 8. Remaining limitations and acceptance decision

- UI registration, upload, chat, history, admin review, and logout workflows remain **NOT TESTED** in a browser.
- Live OpenAI embeddings and generation remain **NOT TESTED**.
- RAG response checks used deterministic substitutes, not the configured OpenAI models; semantic faithfulness was not independently measured.
- Some specific acceptance assertions are listed as **NOT TESTED** above, including complete multi-page evidence validation and a true LLM prompt-injection run.

**Final classification: PASS WITH LIMITATIONS.** The automated regression suites and 48 isolated API assertions passed, but the system is not fully accepted for live model or browser behavior based on these results alone.
