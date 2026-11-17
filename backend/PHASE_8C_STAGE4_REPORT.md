# RAARA — Phase 8C Stage 4 Report

**Implementation: PASS WITH LIMITATIONS**  
**Generic policies: 28**  
**Demonstration questions: 30**  
**Retrieval: PASS; deterministic local in-memory cosine retrieval**  
**Citation validation: PASS; IDs checked against retrieved dataset records**  
**Official-policy abstention: PASS in tested PES/batch cases**  
**Numerical calculations: PASS in tested attendance, weighted score, SGPA, and CGPA cases**  
**CLI smoke test: PASS for one answerable and one official-policy question**  
**Regression: 247 passed, 0 failed**  
**Production changes: NONE**

## Implementation summary

Added `evaluation/generic_policy_demo/`, an isolated offline question-to-answer pipeline over only `evaluation/datasets/project_authored_academic_policy/generic_academic_policy_dataset.json`. It uses the existing `DeterministicTfidfHashEmbedding` evaluation implementation, fits a process-local in-memory vector representation from validated policy text, and ranks by cosine similarity. It creates no persistent index and does not instantiate ChromaDB or SQLite. Demo-local defaults are top-K 5 and minimum relevance 0.12; both can be changed at CLI initialization without touching production settings.

Each retrieved record is revalidated for `PROJECT_AUTHORED`, `GENERIC_PROJECT_POLICY`, `NOT_OFFICIAL`, and `is_official_university_policy: false`. Results preserve the real policy/evidence IDs, titles, category, version, exact text, source labels, and cosine score. Scores are retrieval hints only; they do not indicate authority. Duplicate evidence IDs are suppressed.

The answerer is a deterministic local template and calculation engine, **not an LLM**. It does not make network or OpenAI calls. Citations are constructed only from retrieved records and checked again against their IDs and metadata. Citation objects have no page field, and the dataset has no claimed source URLs or PDF pages, so no page references or URLs are invented. Every result includes a nonofficial disclaimer.

## Retrieval and observed examples

The default relevance threshold is 0.12. On the demo corpus, the minimum-attendance query's top match scored **0.370917**, while the unrelated “next cricket match” query's highest lexical match scored **0.095672** and was dropped by the default threshold. A test also verifies deterministic inclusion/exclusion immediately below/above a result's score. This is a small synthetic-corpus check, not a universal threshold calibration.

Observed demonstration outcomes:

| Scenario | Outcome |
|---|---|
| Illustrative minimum attendance | `SUPPORTED`; answer uses the dataset's 75% project assumption and cites `GAP-E-ATT-001` |
| 72 of 90 classes | `SUPPORTED`; 80.00%, with attendance formula evidence |
| 63 of 90 classes vs. threshold | `SUPPORTED`; 70.00%, 5.00 percentage-point shortfall, citing formula and threshold evidence |
| Internal 34, end-semester 52 | `SUPPORTED`; 44.80/100 using weights read from the dataset |
| Example SGPA inputs | `SUPPORTED`; 8.10 |
| Example CGPA inputs | `SUPPORTED`; 7.70 |
| Backlog and revaluation process | `SUPPORTED` only from the retrieved generic records |
| Official PES attendance or examination dates | `NOT_FOUND`; no citations are used as official evidence |
| Applicability to a real 2025 AIML/admission batch | `NOT_FOUND` |
| Maximum supplementary attempts, specific deadlines, exemptions, promotion credits, credit-hours | `NOT_FOUND` where the dataset says the value is unspecified |
| Unrelated question | `NOT_FOUND` below threshold |
| Ambiguous question | `NEEDS_CLARIFICATION` |
| Compare project-authored versions 0.9 and 1.0 | `CONFLICTING_SOURCES`; both exact evidence IDs and version labels are returned |

The version conflict is deliberately project-authored and fictional: 70% in version 0.9 versus 75% in version 1.0. It does not represent a real university amendment.

## Calculations and abstention

Attendance, assessment weights, passing score, grade-point maximum, SGPA/CGPA formula examples, and the attendance threshold used in shortfall calculations are read from the dataset. Calculators reject invalid class counts, scores outside 0–100, empty course lists, zero/negative credits, and grade points outside the project scale; they guard against division by zero, display calculation steps, and round to two decimals. Verified examples: attendance 72/90 = 80.00%; weighted total = 44.80/100; SGPA = 8.10; CGPA = 7.70.

Official PES/university and batch-applicability queries abstain before using generic records as answer citations. Missing-value cases can cite a retrieved generic record that explicitly says the value is unspecified; this describes only the scope of this project dataset. Unknown, unsupported, or low-scoring retrievals do not get substituted evidence. Ambiguous and unrelated questions abstain or request clarification.

## Security, provenance, and isolation

- Invalid provenance metadata is rejected before indexing and rechecked during retrieval and answer construction.
- Known instruction-like override text in a policy record is rejected. The deterministic answerer executes no retrieved text as instructions and is not an LLM.
- Citation IDs/titles/versions must match retrieved records; fabricated IDs and page numbers cannot be emitted by the citation schema.
- Tests confirm generic records cannot pass the existing official evidence gate or enter the official held-out registry.
- No production route, prompt A/B/C, retriever configuration, database, vector store, or application setting was changed.
- No persistent vector index was created. The demo only keeps embeddings in process memory.
- Full backend tests ran with a unique temporary SQLite database, ChromaDB directory, and upload path; `OPENAI_API_KEY` was empty. No paid API calls were made.
- Phase 9A validator reported `production_storage_accessed: false`; Phase 9A content stayed byte-for-byte unchanged according to the pinned tree fingerprint regression test.
- The Phase 8A official registry remains empty; the held-out validator reports 0 documents and 0 questions (`EMPTY`).

## Test and validator results

| Verification | Actual result |
|---|---|
| Generic dataset validator: `python -m evaluation.scripts.validate_project_authored_policies` | **PASS** — 28 policies, 30 questions, 12 policy categories, numerical examples PASS, 0 official approvals |
| Focused Stage 4 pipeline tests: `python -m pytest -q evaluation/tests/test_generic_policy_demo.py` | **27 passed in 2.09s** |
| Stage 3 corpus + Stage 4 tests (combined earlier focused run) | **36 passed** at that point; later Stage 4 additions are covered in the final full suite |
| Existing Phase 8C policy evidence and review tests | **19 passed** in the focused run; also included in the final suite |
| Phase 9A validator: `python -m evaluation.synthetic_project_data.validate` | **PASS** — 50 questions, 86 evidence references, no exact development/held-out overlap, `production_storage_accessed: false` |
| Phase 8A held-out validator: `python -m evaluation.scripts.validate_heldout_dataset` | **PASS; EMPTY** — 0 imported documents, 0 official documents verified, 0 questions, 0 approvals |
| CLI answerable smoke command | **PASS** — `SUPPORTED`, citation `GAP-E-ATT-001` |
| CLI official-policy smoke command | **PASS** — `NOT_FOUND`, no citations |
| Focused Stage 4 + authored-policy + retrieval tests | **45 passed in 8.67s** with the cached tokenizer path |
| Full backend suite: `python -m pytest -v` | **247 passed in 152.06s; 0 failed** |

One earlier focused run omitted `TIKTOKEN_CACHE_DIR`: **31 passed, 2 failed**. Both failures were existing tokenizer-backed retrieval tests that attempted to download `cl100k_base.tiktoken` while network DNS was unavailable. No API call occurred. With the already cached tokenizer location configured, those tests passed; the final complete suite also passed.

The full suite command used PowerShell with a newly created `$env:TEMP` test root and set `DATABASE_URL`, `CHROMA_PERSIST_DIR`, and `UPLOAD_DIR` to paths beneath it; `OPENAI_API_KEY` was empty and `TIKTOKEN_CACHE_DIR` pointed to the existing local cache. The exact reproducible command is below.

During development, focused runs exposed ranking/intent-selection and test-expectation issues; these were investigated and corrected. The final focused Stage 4 run and full backend suite passed. No test was skipped or weakened.

## Files created and changed

Created:

- `evaluation/generic_policy_demo/__init__.py`
- `evaluation/generic_policy_demo/retriever.py`
- `evaluation/generic_policy_demo/provenance.py`
- `evaluation/generic_policy_demo/answerer.py`
- `evaluation/generic_policy_demo/pipeline.py`
- `evaluation/generic_policy_demo/cli.py`
- `evaluation/generic_policy_demo/README.md`
- `evaluation/tests/test_generic_policy_demo.py`
- `evaluation/retrieval/embeddings.py` — pure evaluation embedder module, separated so the isolated demo can reuse the existing deterministic embedder without importing application configuration.
- `PHASE_8C_STAGE4_REPORT.md`

Modified:

- `evaluation/project_authored_policies.py` — expanded conservative official/batch query detection for the isolated demo safeguard.
- `evaluation/retrieval/indexing.py` — preserved the existing embedder import symbol while extracting the implementation and deferring application settings imports until an indexer needs production-derived defaults. The Stage 4 demo import now avoids loading `app.config` or `.env` settings; a subprocess regression test verifies this boundary.
- `evaluation/datasets/project_authored_academic_policy/generic_academic_policy_dataset.json` — normalized mathematical symbols/arrows in authored text and expected answers to ASCII equivalents because Windows terminal output rendered those symbols as replacement glyphs. Values and meaning are unchanged; the generic dataset validator and arithmetic tests pass.
- `evaluation/README.md` — Stage 4 module, CLI, and isolation instructions.

No Phase 9A assets, official held-out files, application source/routes, prompts, production configuration, SQLite database, or production ChromaDB data were changed. The evaluation-only indexing module was refactored for a settings-free embedder import; its compatibility tests passed.

## Limitations

- Retrieval uses a deterministic lexical hash embedder over only 28 short authored records. Scores and ranking are not semantic guarantees and have not been calibrated on real university rules.
- The answerer uses keyword patterns and deterministic templates. It is not an LLM and may fail on paraphrases or unusual phrasing; official-query phrase detection is not a production security boundary.
- No Chroma persistence, PDF page citations, or live chat integration is included. The module is deliberately separate from `/api/chat` and prompts A/B/C.
- `PROJECT_AUTHORED_GENERIC_POLICY` is a context label, not an authority classification.
- There are still no current verified PES University B.Tech AIML regulations and no genuine held-out questions.

**Disposition:** The offline demonstration is complete with the stated limitations. No later phase was started.

## PowerShell verification commands

Run from `C:\prompt_mini_proj\backend`:

```powershell
.\.venv311\Scripts\python.exe -m evaluation.scripts.validate_project_authored_policies
.\.venv311\Scripts\python.exe -m pytest -v evaluation\tests\test_generic_policy_demo.py
.\.venv311\Scripts\python.exe -m pytest -v evaluation\tests\test_project_authored_policies.py
.\.venv311\Scripts\python.exe -m pytest -v evaluation\tests\test_policy_evidence.py evaluation\tests\test_policy_evidence_review.py
.\.venv311\Scripts\python.exe -m evaluation.synthetic_project_data.validate
.\.venv311\Scripts\python.exe -m evaluation.scripts.validate_heldout_dataset
.\.venv311\Scripts\python.exe -m evaluation.generic_policy_demo.cli --question "What is the illustrative minimum attendance?"
.\.venv311\Scripts\python.exe -m evaluation.generic_policy_demo.cli --question "What is the official PES University attendance requirement?"

$testRoot = Join-Path $env:TEMP ("raara-stage4-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $testRoot | Out-Null
$dbPath = (Join-Path $testRoot "backend-tests.sqlite").Replace("\", "/")
$env:DATABASE_URL = "sqlite:///$dbPath"
$env:CHROMA_PERSIST_DIR = Join-Path $testRoot "chroma"
$env:UPLOAD_DIR = Join-Path $testRoot "uploads"
$env:TIKTOKEN_CACHE_DIR = "C:\Users\Pratik Kalloli\AppData\Local\Temp\data-gym-cache"
$env:OPENAI_API_KEY = ""
.\.venv311\Scripts\python.exe -m pytest -v
```

Final full-suite result after the evaluation-only embedder isolation refactor: **247 passed in 152.06s**. CLI smoke tests were rerun after that refactor: the illustrative attendance question returned `SUPPORTED` with the real dataset evidence ID `GAP-E-ATT-001`; the official PES attendance question returned `NOT_FOUND` with no citations. Generic policy, Phase 9A, and held-out validators also passed after the refactor; held-out readiness remains `EMPTY`.
