# RAARA Phase 8D — Human Authority Review Support and Offline Test Recovery

**Implementation status:** PASS. **Human review status:** NOT REVIEWED. **Dataset readiness:** EMPTY. **Regression status:** PASS — complete backend suite finished.

Phase 8D prepared the review package and recovered the tokenizer data cache without changing production behavior. No source/document/evidence approval was made, no held-out questions were created, and nothing was imported into the Phase 8A registry.

## Human authority review preparation

Reviewed the Phase 8C report, matrix, checklist, OCR/conflict reports, evidence records, schemas, and all three candidate PDFs. SHA-256 checksums matched the inventory:

| Candidate | SHA-256 | Current disposition |
|---|---|---|
| University Act PDF, 16 pages | `1d66332a097f0b2033fffb8398df6328cd1641cd6a9d75e0f0fedf9656948038` | `EXTRACTION_BLOCKED`; image-only, no OCR text |
| 2014 PES University UGC Proforma, 475 pages | `3558ac4222cea3a770a74dedc53510a74318b55842878ad9bf9ee1e7b9d01b06` | `VERIFIED_OFFICIAL_CONTEXT_ONLY`; historical context, mixed institutional scope |
| AIML Curriculum 2025-26, 118 pages | `c9fae00eb4c9e7ba6d0adb0686fe681a709119c72ace361dee707c0c58ec1c4f` | `PENDING_HUMAN_AUTHORITY_REVIEW`; exact file linkage/campus scope remain unresolved |

The new [human review package](evaluation/held_out/HUMAN_REVIEW_PACKAGE.md) includes source URLs, issuer assessment, scope fields, versions/dates, the four exact page-anchored passages, reviewer questions, and recommended classifications. Recommendations are explicitly not decisions. All four evidence records remain `NOT_REVIEWED`; no Phase 8A registry document was added.

## Tokenizer diagnosis and recovery

Backend `.venv311` runs Python 3.11.9 with `tiktoken 0.14.0`. Production `TokenChunker` uses `cl100k_base`. The Python package does not ship its mergeable-ranks resource. Before recovery, no cache was found in the configured/default locations and the package cache had no local resource. The installed tiktoken source specifies:

- Resource: `https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken`
- SHA-256: `223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7`
- `tiktoken` cache key: `9b5ad71b2ce5302211f9c61530b329a4922fc6a4`

An exact copy was obtained from that public upstream resource through the normal reviewer path, verified against the pinned SHA-256, and loaded offline by `tiktoken.get_encoding("cl100k_base")`. This was static tokenizer data, not a live OpenAI API call. No tokenizer implementation or chunking configuration was replaced. See [tokenizer diagnosis and offline recovery](evaluation/TOKENIZER_OFFLINE_RECOVERY.md) for the verification and transfer commands.

## Regression tests

All test commands used unique temporary SQLite, ChromaDB, and upload locations. `OPENAI_API_KEY` was empty. The full suite needed the standard approved execution mechanism for local FastAPI test sockets; it completed without making OpenAI calls.

- Phase 8C evidence + Phase 8A/8B held-out workflow tests: **32 passed, 0 failed** (`26.04s`).
- Evaluation tests: **84 passed, 0 failed** (`40.80s`).
- Complete backend suite: **189 passed, 0 failed** (`111.20s`).
- Offline tokenizer smoke check: `cl100k_base` loaded from the verified cache and encoded a sample string (3 tokens).
- Dataset validator: completed; **EMPTY**, 0 imported documents, 0 questions, 0 approvals, 38 discovered sources.

Before the cache recovery, evaluation tests had **80 passed and 4 failed**, each from the missing tokenizer data and DNS failure. After recovery, all 84 evaluation tests passed. The initial unprivileged full run also stalled at local FastAPI `TestClient` socket setup; the full run completed after invoking the normal approved local-socket execution mechanism.

## Isolation and data integrity

- Test SQLite, ChromaDB, and uploads were directed to a unique temporary root; production storage was not selected by the test processes.
- Evaluation retrieval tests use their own `tmp_path` ChromaDB.
- No production SQLite or ChromaDB data was modified.
- No OpenAI API key was read or printed; the test process received an empty `OPENAI_API_KEY`.
- No live model request, benchmark-result edit, production RAG/prompt change, question generation, or annotation occurred.
- `documents.json` remains `{"registry_version":"1.0","documents":[]}` and `questions.jsonl` remains empty.

## PowerShell verification commands

From `backend`, after making the verified cache file available at the indicated cache path:

```powershell
$env:TIKTOKEN_CACHE_DIR = Join-Path $env:TEMP 'raara-phase8d-tiktoken-cache'
$cacheFile = Join-Path $env:TIKTOKEN_CACHE_DIR '9b5ad71b2ce5302211f9c61530b329a4922fc6a4'
if ((Get-FileHash -LiteralPath $cacheFile -Algorithm SHA256).Hash.ToLowerInvariant() -ne '223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7') { throw 'Tokenizer resource checksum mismatch' }
$testRoot = Join-Path $env:TEMP ('raara-tests-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $testRoot -Force | Out-Null
$env:DATABASE_URL = 'sqlite:///' + ((Join-Path $testRoot 'backend-tests.sqlite').Replace('\','/'))
$env:CHROMA_PERSIST_DIR = Join-Path $testRoot 'chroma'
$env:UPLOAD_DIR = Join-Path $testRoot 'uploads'
$env:OPENAI_API_KEY = ''
.\.venv311\Scripts\python.exe -m pytest -v evaluation\tests\test_policy_evidence.py evaluation\tests\test_heldout_workflow.py
.\.venv311\Scripts\python.exe -m pytest -v evaluation\tests
.\.venv311\Scripts\python.exe -m pytest -v
.\.venv311\Scripts\python.exe -m evaluation.scripts.validate_heldout_dataset
```

The full backend suite may require the approved execution mechanism for local TestClient sockets on this Windows setup. The command does not require a live API credential; keep `OPENAI_API_KEY` empty.

## Readiness and final status

| Dimension | Status |
|---|---|
| Implementation and review package | **PASS** |
| Human authority review | **NOT REVIEWED**; zero approvals |
| Dataset readiness | **EMPTY**; 0 imported docs, 0 questions |
| Regression tests | **PASS**; 189/189 backend tests passed with verified tokenizer cache |

Phase 8D is complete. The reviewer package supports a human decision, but it does not approve any document or evidence. Do not begin live evaluation or held-out annotation until the applicable documents have been independently approved.
