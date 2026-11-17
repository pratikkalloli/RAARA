# RAARA — Phase 8C Stage 5 Report

**Implementation: PASS WITH LIMITATIONS**  
**UI framework: Python standard library HTTP server with static HTML, CSS, and JavaScript**  
**Policy records: 28 project-authored, nonofficial records**  
**Demonstration questions: 30 existing dataset questions**  
**Five examiner cases: 5/5 expected statuses matched**  
**Focused Stage 5 UI tests: 18 passed**  
**Full backend regression: 265 passed in 160.13s**  
**Production changes: NONE**

## Implementation

Created `evaluation/raara_demo_ui/`, a standalone local web interface served at `http://127.0.0.1:8765`. No suitable installed UI framework was present, so the UI uses Python's standard library HTTP server and has no new dependency. It binds only to loopback and is not connected to `/api/chat` or the existing React frontend.

The server creates one `GenericPolicyDemo` instance and delegates every question to the existing Phase 8C Stage 4 pipeline. It does not duplicate retrieval or answer generation. Existing dataset questions, categories, policy assumptions, calculator functions, provenance checks, and citations are reused directly. Dataset evaluation results are computed on demand in memory; the evaluator does not rewrite the dataset or produce persistent benchmark artifacts.

The interface includes question entry, answer status, citations and provenance, retrieved evidence passages and IDs, exact example questions grouped by topic, a five-case examiner tour, four illustrative calculators, a 30-question evaluation table, and a visual workflow explanation. The table shows actual mismatches and IDs. Its automated test-suite field stays “Not measured by this UI session”; it does not guess a test result.

## Five examiner cases

| Case | Expected | Observed | Evidence/citation result |
|---|---|---|---|
| Direct factual: “What is the illustrative minimum attendance?” | `SUPPORTED` | `SUPPORTED` | Cites `GAP-E-ATT-001`; citation metadata validation passed; disclaimer says the 75% value is project-authored and nonofficial. |
| Numerical: 72 of 90 classes | `SUPPORTED` | `SUPPORTED` | Calculated `(72 / 90) x 100 = 80.00%`; citation metadata validation passed. |
| Multiple-policy: existing dataset shortfall question, GAP-Q-003 | `SUPPORTED` | `SUPPORTED` | Retrieved attendance formula and threshold evidence; reports 70.00% attendance and 5.00 percentage-point shortfall; citation metadata validation passed. |
| Official PES attendance requirement | `NOT_FOUND` | `NOT_FOUND` | No generic citation returned; explains that verified institutional evidence is required. |
| Unanswerable supplementary-attempt count question, GAP-Q-015 | `NOT_FOUND` | `NOT_FOUND` | Abstains with the dataset's caveat; returned citation metadata passed validation. |

The five cases were run through the same Stage 4 pipeline as arbitrary UI questions. Outcomes above are observed, not expected-output substitutions.

## Calculations

All calculations use the existing Stage 4 calculator functions and load assumptions from the validated project-authored dataset at runtime. The focused tests verified:

- Attendance: 72/90 = **80.00%**, with formula and evidence `GAP-E-ATT-002`.
- Weighted course total: internal 34/100 and end-semester 52/100 = **44.80/100**, using the dataset's 40:60 example weights and assessment evidence.
- Example SGPA inputs = **8.10**, with SGPA formula evidence.
- Example CGPA inputs = **7.70**, with CGPA formula evidence.

The UI displays input values, formula, intermediate arithmetic, result, and source text. Every result is labeled illustrative and nonofficial.

## Reproducible 30-question diagnostic

The run used the original 30 questions in dataset order. The combined pass rule is: expected status matches, citation metadata validates, and all expected evidence is retrieved for answerable questions. The run observed:

| Diagnostic | Result |
|---|---:|
| Combined pass / fail | **24 / 6** |
| Expected status matched | **26 / 30** |
| Citation metadata checks passed | **30 / 30** |
| Expected abstentions correct | **6 / 9** |
| Answerable items with all expected evidence retrieved | **18 / 21** |
| Numerical-question statuses matched | **6 / 6** |

Failed question IDs: **GAP-Q-014, GAP-Q-016, GAP-Q-020, GAP-Q-021, GAP-Q-028, GAP-Q-030**. These include three unanswerable prompts that the deterministic answerer marked `SUPPORTED`, two answerable questions missing their expected evidence, and a conflicting-version prompt for which the expected evidence was not retrieved. The interface shows each discrepancy and retrieved ID instead of hiding or correcting it.

The 30/30 citation result is only an ID/metadata consistency check against retrieved dataset rows. It does not prove semantic claim support or answer faithfulness. These figures describe this small project-authored demonstration corpus; they are not official-policy accuracy, general retrieval benchmarks, or LLM performance measurements.

## Validation and tests

| Check | Actual result |
|---|---|
| Generic policy validator | **PASS** — 28 policies, 30 questions, 0 official approvals |
| Stage 4 demo tests | **27 passed** |
| Stage 5 UI tests | **18 passed** |
| Citation verification tests | **14 passed** |
| Five examiner scenarios | **5/5 expected statuses matched; citation metadata validation passed for all five** |
| Phase 9A validator | **PASS** — 50 synthetic questions, 86 evidence references, `production_storage_accessed: false` |
| Phase 8A held-out validator | **PASS; readiness EMPTY** — 0 registered documents, 0 questions, 0 approvals |
| Full backend suite | **265 passed in 160.13s; 0 failed** |
| Local startup smoke | **PASS** — health `ok`, page HTTP 200, title present, official question `NOT_FOUND`, 0 answer citations |
| Browser JavaScript syntax: `node --check evaluation/raara_demo_ui/app.js` | **PASS** |

The complete backend suite was rerun after the default sandbox stalled at existing `TestClient` calls because loopback sockets were restricted. The completed run used the standard approval mechanism, `.venv311`, an empty `OPENAI_API_KEY`, the local tokenizer cache, and a unique temporary SQLite, ChromaDB, and upload root. No paid OpenAI calls were made. No production database or ChromaDB data was used. The held-out validator regenerated only its derived readiness report; the official registry, documents, and questions remain unchanged and empty.

## Isolation and limitations

- All corpus records remain `PROJECT_AUTHORED`, `GENERIC_PROJECT_POLICY`, and `NOT_OFFICIAL`; no official authority status or human review changed.
- No production route, prompt A/B/C, retriever threshold, production frontend, SQLite database, or production ChromaDB data changed.
- No Phase 9A dataset or expected answer changed. The existing generic question dataset was read only.
- The demo imports no application settings or `.env` credentials, calls no LLM, and exposes no approval/import feature.
- Retrieval is a small deterministic lexical hash/cosine baseline. The answerer is deterministic templates/calculations, not an LLM.
- The local UI is unauthenticated and intended only for a trusted local project demonstration. It binds to loopback and has no write endpoints.
- Semantic faithfulness is not measured. Citation metadata validity does not imply citation entailment.
- Official PES University B.Tech AIML policy is not verified in the corpus; the held-out dataset remains empty.

## Files created

- `evaluation/raara_demo_ui/__init__.py`
- `evaluation/raara_demo_ui/server.py`
- `evaluation/raara_demo_ui/runner.py`
- `evaluation/raara_demo_ui/evaluate.py`
- `evaluation/raara_demo_ui/index.html`
- `evaluation/raara_demo_ui/styles.css`
- `evaluation/raara_demo_ui/app.js`
- `evaluation/raara_demo_ui/test_run_result.json` — records the observed full-suite result displayed by the UI.
- `evaluation/raara_demo_ui/README.md`
- `evaluation/tests/test_raara_demo_ui.py`
- `PHASE_8C_STAGE5_REPORT.md`

No application source, frontend project, Stage 4 pipeline, prompts, retrieval settings, generic dataset, Phase 9A asset, or official document was modified. The existing held-out `readiness_report.json` and `.md` were refreshed by their validator and still report `EMPTY`.

## PowerShell verification commands

From `C:\prompt_mini_proj\backend`:

```powershell
$env:OPENAI_API_KEY = ""
$env:TIKTOKEN_CACHE_DIR = "C:\Users\Pratik Kalloli\AppData\Local\Temp\data-gym-cache"
.\.venv311\Scripts\python.exe -m evaluation.scripts.validate_project_authored_policies
.\.venv311\Scripts\python.exe -m pytest -v evaluation\tests\test_generic_policy_demo.py
.\.venv311\Scripts\python.exe -m pytest -v evaluation\tests\test_raara_demo_ui.py
.\.venv311\Scripts\python.exe -m pytest -v tests\test_citation_verifier.py
.\.venv311\Scripts\python.exe -m evaluation.synthetic_project_data.validate
.\.venv311\Scripts\python.exe -m evaluation.scripts.validate_heldout_dataset
.\.venv311\Scripts\python.exe -m evaluation.raara_demo_ui.evaluate
.\.venv311\Scripts\python.exe -m evaluation.raara_demo_ui.server
```

For the complete regression without production storage writes:

```powershell
$testRoot = Join-Path $env:TEMP ("raara-stage5-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $testRoot | Out-Null
$dbPath = (Join-Path $testRoot "backend-tests.sqlite").Replace("\", "/")
$env:DATABASE_URL = "sqlite:///$dbPath"
$env:CHROMA_PERSIST_DIR = Join-Path $testRoot "chroma"
$env:UPLOAD_DIR = Join-Path $testRoot "uploads"
.\.venv311\Scripts\python.exe -m pytest -q
```

**Disposition:** Stage 5's local demonstration interface is implemented. It is complete as a project demonstration with limitations: the underlying deterministic evaluator has six visible diagnostic failures, and no official policy data exists. No subsequent phase was started.
