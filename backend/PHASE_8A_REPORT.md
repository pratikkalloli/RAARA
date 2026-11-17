# RAARA Phase 8A — Real-World Held-Out Dataset Preparation

## Outcome

**Classification: PASS WITH LIMITATIONS.**

The held-out dataset schema, document provenance registry and import flow, annotation/review workflow, validation, split checks, and readiness reporting are implemented and tested. There are **0 genuine documents**, **0 held-out questions**, **0 annotated questions**, **0 approved questions**, and **0 incomplete annotations**. The held-out dataset is **EMPTY** and is **not ready for Phase 8B** because no authorized real university policy documents have been supplied or independently verified. No questions or documents were fabricated to fill the target.

Infrastructure criteria for Phase 8A pass. Research data collection and annotation remain outstanding; this report does not claim a benchmark, policy validation, or semantic validation.

## Repository audit and reuse

Before editing, I reviewed the Phase 7E report, final research report, evaluation README, existing held-out README/template, development schemas/validator/tests, and the complete `evaluation/` tree.

Already present and retained:

- The 12-question Phase 7A development JSONL and its manifest.
- Two labeled synthetic PDFs, explicitly not official university regulations.
- Development JSONL/PDF evidence validation and retrieval/answer/prompt evaluation.
- An empty held-out workflow directory and a placeholder annotation template.
- Existing isolated evaluation test patterns and `.venv311`.

Repository file search found only the two synthetic PDFs plus `requirements.txt` among PDF/document-like files. No genuine or authorized university policy, examination guideline, or academic regulation document is present. The production SQLite database and Chroma collection were not inspected or modified for this phase.

The held-out path uses the existing development split only for leakage comparison and the existing `PageReference`/`ExpectedStatus` types where applicable. It keeps a separate held-out question schema because held-out records require additional answerability, document version, provenance, and independent review fields. Production application routes/services, prompt A/B/C, retrieval settings, benchmark result artifacts, SQLite, and ChromaDB were not changed.

## Implemented functionality

### Document provenance and import

- `documents.json` is a versioned registry that records document ID/title, original filename, version, publication/effective dates when available, official/unofficial classification, authority review status, reviewer/date, page count, SHA-256, source URL or supplied-source provenance, retrieval date, permission/access basis, and superseded document IDs.
- The PDF importer copies original bytes without extraction, rewriting, redaction, or conversion; validates the PDF; computes SHA-256; records page count; refuses duplicate IDs, byte-identical documents, and path overwrites.
- Registry validation checks required provenance, checksum format and actual file hash, PDF readability/page count, path containment, unique document IDs and checksums, and that superseded IDs exist.
- An imported `official` claim remains `pending` until an independent source review is recorded. `unofficial_reference` documents remain explicitly `not_official` and cannot support an approved regulatory annotation as authoritative evidence.

The provenance record is an auditable human attestation; the importer cannot independently establish that a URL is genuinely controlled by a university or that a permission record is legally sufficient. A reviewer must perform that source verification.

### Held-out schema, annotation and validation

- Added held-out question categories for direct factual, multi-passage, multi-document, unanswerable, conflicting policy, version-sensitive, academic eligibility, examination/assessment, policy interpretation, and prompt-injection questions.
- Records capture unique IDs, question, answerability/status, expected answer, relevant document IDs, exact evidence text, document version, one-based page, section, expected claims, annotation notes, attack surface, dataset version, annotator/date, reviewer/date, and `pending`/`reviewed`/`approved` status.
- Answerable annotations require an expected answer and exact evidence. Unanswerable annotations require `NOT_FOUND`, no expected answer, and no mandatory supporting documents/pages/evidence/claims.
- The interactive authoring command lists registered documents and creates only pending annotations. It validates proposed evidence against the actual PDF page, manifest version, and normalized exact development overlap before saving.
- An independent review command enforces separate annotator/reviewer identities and complete review metadata. Approval requires all cited documents to be independently verified official sources. Approved records cannot be modified through this workflow; issue a new dataset version to amend labels.
- The validator checks duplicate question IDs, missing/invalid evidence, page bounds, source provenance and checksum, document versions, exact evidence text on the specified page, duplicate evidence mappings, unanswerable evidence contamination, incomplete approval, supersession references, and exact normalized question/ID overlap with development data.
- Exact ID/text overlap is detectable automatically; paraphrased or semantically reworded development leakage still requires independent human review.

### Dataset readiness

Current report: [readiness_report.md](evaluation/datasets/held_out/readiness_report.md) and JSON companion.

| Measure | Current count/status |
|---|---:|
| Genuine documents imported | 0 |
| Official documents independently verified | 0 |
| Unofficial reference documents | 0 |
| Valid held-out questions | 0 |
| Annotated questions | 0 |
| Approved questions | 0 |
| Incomplete annotations | 0 |
| Target | 40–60 questions |
| Phase 8B ready | No |
| Phase 8C ready (40+ approved) | No |

The held-out question JSONL is empty. The registry contains no documents. Synthetic PDFs used by unit tests are generated only under temporary test directories and are never written to the held-out registry or reported as genuine sources.

## Verification

- Held-out validator: passed on the empty split; reports `EMPTY`, zero documents/questions/annotations/approvals, and Phase 8B/8C not ready.
- Held-out workflow tests: **18 passed, 0 failed** (included in the evaluation test suite).
- Complete evaluation tests (existing Phase 7A–7E plus Phase 8A): **70 passed, 0 failed**.
- Full backend test suite: **175 passed, 0 failed** under Python 3.11.9, with temporary SQLite, ChromaDB, and upload paths.
- Import/annotation tests used generated PDFs labeled **SYNTHETIC TEST DOCUMENT — NOT OFFICIAL POLICY**, in temporary directories only.
- No live OpenAI API calls, production DB/Chroma writes, or production application changes occurred.

## Files created and modified

Created:

- `backend/PHASE_8A_REPORT.md`
- `backend/evaluation/schemas/held_out.py`
- `backend/evaluation/heldout.py`
- `backend/evaluation/scripts/import_heldout_document.py`
- `backend/evaluation/scripts/annotate_heldout.py`
- `backend/evaluation/scripts/review_heldout_annotation.py`
- `backend/evaluation/scripts/validate_heldout_dataset.py`
- `backend/evaluation/datasets/held_out/documents.json`
- `backend/evaluation/datasets/held_out/questions.jsonl` (empty)
- `backend/evaluation/datasets/held_out/readiness_report.json`
- `backend/evaluation/datasets/held_out/readiness_report.md`
- `backend/evaluation/tests/test_heldout_workflow.py`

Modified:

- `backend/evaluation/README.md`
- `backend/evaluation/datasets/held_out/README.md`
- `backend/evaluation/datasets/held_out/annotation_template.json`

No production code, frontend code, SQLite data, ChromaDB data, or prior benchmark results were modified.

## Outstanding manual work and recommendation

1. Supply authorized original university regulations, examination/assessment guidance, and academic policy documents; record source/permission details and retain original PDFs.
2. Independently verify issuing authority, version, publication/effective dates, and supersession relationships.
3. Import documents with the provided workflow; official status stays pending until source review.
4. Independently annotate and review approximately 40–60 genuine questions across the required categories. Keep labels unavailable during tuning.
5. Run the readiness validator until the dataset has enough approved annotations for its intended evaluation. Human reviewers must check semantic leakage and evidence interpretation.

**Recommendation:** Phase 8A is ready to close as an infrastructure deliverable with limitations. The dataset itself is not ready for Phase 8B; wait for authorized documents and independent source verification before annotation. Phase 8C live OpenAI evaluation must remain out of scope until a later explicit approval.

## PowerShell verification commands

Run from `C:\prompt_mini_proj\backend`:

```powershell
.\.venv311\Scripts\python.exe -m evaluation.scripts.validate_heldout_dataset
.\.venv311\Scripts\python.exe -m pytest -v evaluation\tests\test_heldout_workflow.py
.\.venv311\Scripts\python.exe -m pytest -v evaluation\tests
```

Full backend regression with isolated stores (local Windows sockets are needed by existing TestClient tests):

```powershell
$testRoot = Join-Path $env:TEMP ('raara-phase8a-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $testRoot | Out-Null
$dbPath = (Join-Path $testRoot 'raara-test.sqlite').Replace('\', '/')
$env:DATABASE_URL = "sqlite:///$dbPath"
$env:CHROMA_PERSIST_DIR = Join-Path $testRoot 'chroma'
$env:UPLOAD_DIR = Join-Path $testRoot 'uploads'
$env:TIKTOKEN_CACHE_DIR = 'C:\Users\Pratik Kalloli\AppData\Local\Temp\data-gym-cache'
.\.venv311\Scripts\python.exe -m pytest -v
```

To import a real document, use the command example in `evaluation/datasets/held_out/README.md` only after confirming permission and source provenance. No Phase 8B or 8C work was started.
