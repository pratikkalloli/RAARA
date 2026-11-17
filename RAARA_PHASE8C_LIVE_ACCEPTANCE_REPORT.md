# RAARA Phase 8C — Live Gemini Acceptance and Regression Report

## Result

**Full backend regression: PASS — 170 passed.**  
**Live Gemini acceptance: INCOMPLETE — intent and selected-document checks exposed failures.**  
**Production storage: untouched.**

The WSL regression used the project’s existing Python 3.11 environment, verified its local `cl100k_base` cache, blanked both API keys in the test process, and directed SQLite, ChromaDB, and uploads to a unique temporary directory. The running backend reused for live acceptance was also confirmed to use an isolated temporary database, Chroma directory, and upload directory.

Live acceptance used the existing Gemini configuration. The API key was confirmed configured without reading or printing its value. It was never requested or exposed.

## Environment

| Item | Observed value |
|---|---|
| Backend | `C:\prompt_mini_proj\backend` |
| WSL Python | 3.11.18 at `.venv-wsl311/bin/python` |
| AI provider | `gemini` |
| Chat model | `gemini-3.5-flash-lite` |
| Embedding model | `gemini-embedding-001` |
| Gemini credential | Configured in existing backend environment; value not read or displayed |
| Tokenizer cache | `/tmp/data-gym-cache`, one cache file; `tiktoken.get_encoding("cl100k_base")` succeeded |
| Test storage | `/tmp/raara-phase8c-tests-ZxIg5Z/` for SQLite, ChromaDB, and uploads |
| Reused live backend storage | `/mnt/c/Users/Pratik Kalloli/AppData/Local/Temp/RAARA_LIVE_ACCEPTANCE_20261114_141801_aa135e6c/` for SQLite, ChromaDB, and uploads |

No tokenizer package or application behavior was changed. No network download was needed to restore the cache.

## Full backend regression

The complete suite ran in WSL Python 3.11.18 and finished successfully:

```text
170 passed in 104.43s
```

No tests were skipped or interrupted. API-key variables were blank during the suite, so its Gemini and OpenAI calls used mocks. The test database, Chroma collection, and upload directory were all under the unique `/tmp/raara-phase8c-tests-ZxIg5Z/` path.

Command executed:

```bash
wsl.exe -e bash -lc 'set -e; cd /mnt/c/prompt_mini_proj/backend; ISOLATION=$(mktemp -d /tmp/raara-phase8c-tests-XXXXXX); export GEMINI_API_KEY= OPENAI_API_KEY=; export DATABASE_URL="sqlite:///$ISOLATION/backend.db"; export CHROMA_PERSIST_DIR="$ISOLATION/chroma"; export UPLOAD_DIR="$ISOLATION/uploads"; export TIKTOKEN_CACHE_DIR=/tmp/data-gym-cache; mkdir -p "$CHROMA_PERSIST_DIR" "$UPLOAD_DIR"; ./.venv-wsl311/bin/python -m pytest tests -v'
```

The selected tokenizer cache was checked before this command:

```bash
wsl.exe -e bash -lc 'cd /mnt/c/prompt_mini_proj/backend && ./.venv-wsl311/bin/python -c "import os,tempfile,tiktoken; p=os.environ.get(\"TIKTOKEN_CACHE_DIR\") or os.environ.get(\"DATA_GYM_CACHE_DIR\") or os.path.join(tempfile.gettempdir(),\"data-gym-cache\"); print(\"CACHE_DIR=\"+p); print(\"CACHE_PRESENT=\"+str(os.path.isdir(p))); print(\"CACHE_FILES=\"+str(len(os.listdir(p)) if os.path.isdir(p) else 0)); print(\"CL100K=\"+tiktoken.get_encoding(\"cl100k_base\").name)"'
```

## Live Gemini acceptance

The existing backend on port 8000 was checked before use. It was already running with `AI_PROVIDER=gemini`, `gemini-3.5-flash-lite`, and `gemini-embedding-001`. Its SQLite, Chroma, and upload paths were all under the isolated live-acceptance directory shown above. Its health endpoint returned `{"status":"ok","service":"RAARA"}`; AI health reported Gemini and a configured credential.

The live harness created two disposable student accounts and three one-page PDFs. Every PDF stated **SYNTHETIC TEST ONLY — NOT OFFICIAL UNIVERSITY POLICY**. Two PDFs belonged to the test student; one belonged to the second account. All three uploads indexed successfully and remained `unverified`. The files contained only fabricated test values. They were not presented as real university rules.

| Case | Actual result |
|---|---|
| Natural greeting | HTTP 200, but status was `NOT_FOUND`, with no evidence or sources. The stored answer was the empty-evidence abstention. **FAIL:** Gemini did not route this as a conversational response. |
| Conversational follow-up | HTTP 200, but status was `NOT_FOUND`, with no evidence or sources. The stored answer was the empty-evidence abstention. **FAIL:** it also entered the evidence-required path. |
| Synthetic PDF uploads | **PASS:** two documents indexed for the first disposable student; one indexed for the second; all remained `unverified`. |
| Question about the selected synthetic PDF | **NOT TESTED to completion:** the request returned HTTP 422. The harness stopped rather than retrying or making additional chat calls. No answer or citation was validated. |
| Whole-PDF summary | **NOT TESTED:** stopped after the HTTP 422 result. |
| Unsupported question | **NOT TESTED:** stopped after the HTTP 422 result. |
| Question about a different accessible document | **NOT TESTED:** stopped after the HTTP 422 result. |
| Cross-user document selection | **NOT TESTED live:** the live case was not reached. Automated ownership tests passed in the full backend suite. |
| Conversation persistence | **PARTIAL PASS:** the isolated database contains the greeting and follow-up user/assistant pairs (four messages total). Both assistant turns persisted with `NOT_FOUND` results. |
| Citation and page verification | **NOT VERIFIED live:** no successful evidence-bearing answer was returned. Automated citation tests passed in the regression suite. |

The 422 response body was not captured by the harness, so this report does not attribute it to a specific validation error. No attempt was made to repeat the failed request. The two incorrect conversational classifications also were not repeated.

The live harness command was:

```powershell
wsl.exe -e bash -lc 'cd /mnt/c/prompt_mini_proj/backend && ./.venv-wsl311/bin/python /mnt/c/prompt_mini_proj/backend/.phase8c_live_acceptance_tmp.py'
```

The temporary harness file was removed after execution. It kept passwords and bearer tokens in memory and printed neither. Its output contained only statuses, evidence counts, page/document identifiers, and synthetic upload outcomes.

## Frontend verification

Frontend files were not changed. Frontend tests and build were not rerun because the requested work was backend environment repair and live Gemini validation, and no frontend changes were made.

## Safety and data boundaries

- The regression suite used only temporary storage.
- Live acceptance used the backend process’s existing isolated temporary storage, not production SQLite, ChromaDB, or upload paths.
- Live uploads belonged to disposable authenticated test users and were explicitly synthetic and unverified.
- No official evidence approval, held-out dataset, or Phase 9A asset was modified.
- No API key was printed, logged by the harness, or returned to the client.
- No live API calls occurred during automated tests.

## Limitations and next action

The automated regression is green, but the live feature is not ready to claim acceptance. Gemini returned an evidence-abstention response to two ordinary conversational turns, and the first selected-document chat returned HTTP 422. Because the user requested a bounded, non-repeated live run, summaries, unsupported-question behavior, successful citations, and live cross-user denial remain untested. The live response body for the 422 should be captured safely before any correction or further live attempt.

No source code, frontend files, model settings, embeddings configuration, or production data were changed during this validation phase.
