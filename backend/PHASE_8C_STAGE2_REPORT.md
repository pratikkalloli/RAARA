
## Phase 8C Stage 2 — Official-source discovery and human evidence review

Stage 2 continued source discovery on public PES University websites and added a human-controlled, provenance-bound evidence review workflow. It does not change production RAG code, production SQLite/ChromaDB, prompt configurations, retrieval settings, or benchmark result artifacts. No OpenAI API calls were made.

The source inventory now has 44 records (15 official-verified source-origin records, 14 official-unverified leads, 7 wrong-institution records, and 8 third-party references). Three additional official/context PDFs were downloaded to the held-out discovery folder: the one-page 2025 Public Self Disclosure index, a 130-page CSE syllabus handbook, and a 96-page CSE course structure. These are discovery/context materials only, not current B.Tech AIML regulations. The downloaded item 3.3 index identifies “Statutes/ Ordinances Pertaining to Academics/ Examinations,” but its linked route remains inaccessible. Current AIML curriculum and calendar links resolve to Google Drive sign-in viewers; no sign-in or access-control bypass was attempted.

Three original candidate classifications are preserved: the University Act remains `EXTRACTION_BLOCKED`; the 2014 UGC Proforma remains `VERIFIED_OFFICIAL_CONTEXT_ONLY`; and the 2025–26 AIML curriculum remains `PENDING_HUMAN_AUTHORITY_REVIEW`. Four previously extracted evidence candidates remain `NOT_REVIEWED`. No candidate was approved or rejected, no human decision was entered, and the Phase 8A registry remains empty. No current B.Tech AIML regulations have been verified; dataset readiness is `EMPTY`.

The new review workflow displays source identity, PDF checksum, applicability fields, and the original page text; requires reviewer identity, explicit decision, rationale, and confirmation; rejects approval unless the source is verified-authoritative and current; and records decisions in a separate append-only hash-chained ledger. Candidate records and source PDFs are not mutated. The hash chain is tamper-evident, not a digital signature or identity authentication. The interactive review command was not run.

### Policy coverage and conflicts

The updated [policy evidence matrix](held_out/POLICY_EVIDENCE_MATRIX.md) covers attendance/ESA eligibility, ISA/ESA, grading/SGPA/CGPA, backlogs/supplementary exams, revaluation/grievances, registration/withdrawal, progression, credits, calendar, and governance. For every category the result remains **NO VERIFIED EVIDENCE FOUND** for an applicable, current, human-approved B.Tech AIML rule. This does not establish that such rules do not exist. The [missing-regulations report](held_out/MISSING_REGULATIONS_REPORT.md) now separates publicly located leads, downloaded files, direct receipt, official provenance, human review, rejection, and unavailable material. No current regulation was directly received; none was rejected in Stage 2.

Conflict analysis found zero evidenced overlapping current policy pairs, zero resolved conflicts, and zero evidenced unresolved conflicts. This is an evidence limitation, not proof that no conflicts exist. No version was chosen as controlling and no supersession was inferred.

### OCR capability

The Act PDF has 16 scanned pages and zero extractable text. Local PyMuPDF and Poppler rendering are available; the first page rendered successfully to a temporary file. Tesseract, OCRmyPDF, and the checked Python OCR wrappers/engines are unavailable. No OCR was run, no software was installed, and the original PDF remains unchanged. The Windows OCR capability check would require elevation and was not run elevated. See [OCR_REPORT.md](held_out/OCR_REPORT.md) for the local capability findings and a reproducible recovery route through a locally installed Tesseract engine; recovery was not performed.

### Validation and tests

- Focused authority/evidence review tests: **19 passed** (`evaluation/tests/test_policy_evidence.py` and `evaluation/tests/test_policy_evidence_review.py`).
- Full backend suite with isolated temporary SQLite, ChromaDB, and upload paths: **208 passed in 155.46 seconds**.
- Held-out validator: passed; 44 discovery records, 0 imported documents, 0 questions, 0 approved annotations; readiness `EMPTY`.
- Synthetic development dataset validator: passed; 12 questions (3 direct factual, 2 multi-passage, 1 multi-document, 2 unanswerable, 2 conflicting-version, 2 prompt-injection).
- PDF render smoke check: passed for all 16-page Act document opening and first-page rendering (temporary output only); OCR was not tested.
- A guessed validator module name (`evaluation.scripts.check_heldout_readiness`) was not present; the canonical `validate_heldout_dataset` command above was run successfully instead. This was a command-name mismatch, not a product/test failure.

The regression suite used `.venv311`, an empty OpenAI key, and isolated test storage. It did not use paid APIs. The held-out validator refreshed only its evaluation readiness report. No production SQLite or ChromaDB data was opened for writes; no production application code, prompt, retrieval configuration, benchmark result, or source PDF was changed.

### Stage 2 disposition

**Implementation: PASS.** **Human document/evidence review: PENDING; 0 approvals.** **Current official B.Tech AIML evidence: 0.** **Held-out dataset readiness: EMPTY / NOT READY.** **Regression: PASS (208/208).** This is a discovery and review-workflow milestone, not approval to annotate or evaluate against real university regulations. The next meaningful input is an authorized university-provided current regulation package or public links whose actual files and applicability can be verified, followed by independent human review.

For the source list and exact public-source findings see [SOURCE_INVENTORY.md](held_out/SOURCE_INVENTORY.md), [POLICY_EVIDENCE_MATRIX.md](held_out/POLICY_EVIDENCE_MATRIX.md), [HUMAN_AUTHORITY_REVIEW.md](held_out/HUMAN_AUTHORITY_REVIEW.md), and [CONFLICT_AND_VERSION_ANALYSIS.md](held_out/CONFLICT_AND_VERSION_ANALYSIS.md).

## Files and exact verification commands

Stage 2 implementation files: `evaluation/policy_evidence_review.py` (new), `evaluation/scripts/review_policy_evidence.py` (new), `evaluation/schemas/policy_evidence.py` (review metadata/schema update), `evaluation/policy_evidence.py` (ledger-backed authoritative selection), `evaluation/tests/test_policy_evidence_review.py` (new), and `evaluation/tests/test_policy_evidence.py` (ledger integration coverage). Documentation and discovery artifacts are listed in the final response. Three context PDFs were added under `evaluation/held_out/documents/discovery/`; no regulatory PDF was imported.

To reproduce the test suite from PowerShell in `backend` without touching production storage:

```powershell
$testRoot = Join-Path $env:TEMP ("raara-stage2-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $testRoot | Out-Null
$dbPath = (Join-Path $testRoot "backend-tests.sqlite").Replace("\", "/")
$env:DATABASE_URL = "sqlite:///$dbPath"
$env:CHROMA_PERSIST_DIR = Join-Path $testRoot "chroma"
$env:UPLOAD_DIR = Join-Path $testRoot "uploads"
$env:TIKTOKEN_CACHE_DIR = "C:\Users\Pratik Kalloli\AppData\Local\Temp\data-gym-cache"
$env:OPENAI_API_KEY = ""
.\.venv311\Scripts\python.exe -m pytest -v
```

Expected observed result for this run: **208 passed**. To run focused review tests instead, use:

```powershell
.\.venv311\Scripts\python.exe -m pytest -v evaluation\tests\test_policy_evidence.py evaluation\tests\test_policy_evidence_review.py
```

The isolated test directory is separate from the existing configured database, upload directory, and Chroma store.
