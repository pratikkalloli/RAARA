# RAARA Phase 9A — Synthetic Academic Policy Corpus and Evaluation Dataset

## Result

**Classification: PASS WITH LIMITATIONS.** A clearly labeled, project-authored synthetic corpus and 50-question evaluation dataset are generated and validated. This is an academic demonstration only; it is **not an official PES University policy system** and does not verify actual university rules.

## Corpus and question dataset

- Dataset version: `9A.1.0`.
- Current-model policy documents: **10**, each available as source Markdown and a generated, text-extractable PDF. Every document carries `dataset_type: SYNTHETIC_PROJECT_DATA`, `is_official_university_policy: false`, `source_type: PROJECT_AUTHORED`, a synthetic document ID, version and academic year.
- Separate superseded conflict fixtures: **2**. They are not in the primary manifest/index.
- Questions: **50**, each with unique ID, question, category, deterministic expected answer (or null for unsupported items), answerability, exact evidence, expected citations, rationale, difficulty and synthetic classification.
- Exact evidence references checked against their PDF page: **86**.
- Question partitions: **36 development**, **11 synthetic held-out**, and **3 separate conflict scenarios**. The synthetic held-out split is separate from the real-source held-out registry and was not scored or used for tuning.

Category counts:

| Category | Count |
|---|---:|
| Direct factual | 8 |
| Attendance and eligibility | 6 |
| ISA/ESA calculations | 6 |
| Grading and SGPA/CGPA | 6 |
| Backlogs and supplementary | 5 |
| Lateral entry and progression | 5 |
| Multi-passage | 4 |
| Multi-document | 3 |
| Version/scope conflicts | 3 |
| Unanswerable | 2 |
| Prompt injection | 2 |

The regular-entry 72-credit Semester 4 requirement and lateral-entry 24-credit Semesters 3–4 requirement are separately scoped. Conflict scenarios identify both source versions, effective dates, applicability, expected resolution and evidence. The primary current corpus contains no unresolved temporal conflicts. The two unanswerable topics have no ground-truth answer or citations and are absent from the primary policy text.

## Numerical and retrieval validation

- Numerical question calculations independently recomputed: **2** (weighted final score 77; CGPA 8.50).
- Worked policy examples independently recomputed: **2** (SGPA 8.57; CGPA 8.50). The weighted final-score example is also independently computed as 77.
- The existing schema, PDF/page validator and exact evidence-span checks were reused. Manifest SHA-256 and page counts were checked. Question IDs, answerability, citations, split separation and required provenance labels were checked.
- The A/B/C diagnostic runner used existing Phase 7D experiment code, the same existing prompt definitions and answer schema, and the same evidence/retrieval result per question. It ran **36 development questions** under `CONTROLLED_EVIDENCE` and `END_TO_END_RAG`, using an isolated temporary Chroma collection.
- The deterministic mock does not interpret A/B/C prompts; the outputs tie. The local TF/hash embedding substitute is not `text-embedding-3-small`. These diagnostics do not measure real-model prompt effects, semantic faithfulness, or real university-policy accuracy. No statistically significant winner is claimed.

Detailed counts, checksums, metric denominators and diagnostic results are in [`benchmark_validation_report.json`](evaluation/synthetic_project_data/results/benchmark_validation_report.json), [`benchmark_validation_report.md`](evaluation/synthetic_project_data/results/benchmark_validation_report.md), and [`synthetic_prompt_comparison.json`](evaluation/synthetic_project_data/results/synthetic_prompt_comparison.json).

## Separation and production safety

- Existing Phase 7 development data and historical benchmark artifacts remain separate and were not overwritten.
- Synthetic current and superseded documents are in `evaluation/synthetic_project_data/`; none was added to the official Phase 8A held-out registry or production document database.
- The production retrieval threshold, chunking settings, prompts, citation verifier, SQLite data, and ChromaDB data were not changed by this phase. Evaluation indexing and tests used temporary Chroma/SQLite/upload paths.
- No live OpenAI call was made. `OPENAI_API_KEY` was set empty for the full regression run.
- The synthetic held-out split is not evidence about actual PES University regulations. It was not used for tuning or scored by the Phase 9A runner.

## Tests and validation

- Synthetic builder: **10 primary policy PDFs, 2 conflict PDFs, 50 questions** generated.
- Synthetic dataset validator: **PASS**; 50 questions and all category/split totals validated; 86 exact page-level evidence references; numerical checks passed; development/held-out exact ID and text overlap absent.
- Focused Phase 9A/schema/prompt tests: **25 passed** before the final additional evidence reference; the complete final run below includes the corrected final corpus.
- Complete backend suite on final assets: **198 passed, 0 failed** (`108.64s`). The run used a unique temporary SQLite database, temporary ChromaDB and upload paths, the verified local `cl100k_base` cache, and an empty OpenAI API key.
- Production storage access by the synthetic benchmark: **none**. Production configuration values remained unchanged.

## Files created and modified

Created the isolated corpus in `evaluation/synthetic_project_data/`:

- Ten Markdown policy sources in `corpus/` and ten generated PDFs in `corpus/pdfs/`.
- Two historical conflict Markdown/PDF fixtures in `conflicts/`, conflict manifest and machine-readable conflict scenarios.
- `synthetic_dataset_manifest.json`, `synthetic_conflict_manifest.json`, master `datasets/synthetic_questions.json`, and separate development/held-out/conflict question files.
- `SYNTHETIC_DATASET_DOCUMENTATION.md`, `SYNTHETIC_POLICY_REGISTER.md`, `SYNTHETIC_CONFLICT_SCENARIOS.md`, dataset builder/validator/runner, benchmark validation reports, and prompt comparison reports.
- `evaluation/tests/test_synthetic_project_data.py`.

Modified:

- `evaluation/schemas/dataset.py` — backward-compatible optional synthetic question/evidence metadata, synthetic category labels, and calculation ground-truth field.
- `evaluation/retrieval/indexing.py` — carries document source/provenance metadata into evaluation-only chunks while preserving legacy defaults.
- `evaluation/README.md` — documents the isolated Phase 9A dataset and commands.

No production RAG, prompt, citation, API, frontend, or database implementation was changed.

## Verification commands

Run from `C:\prompt_mini_proj\backend` in PowerShell:

```powershell
$env:TIKTOKEN_CACHE_DIR = 'C:\Users\Pratik Kalloli\AppData\Local\Temp\data-gym-cache'
.\.venv311\Scripts\python.exe -m evaluation.synthetic_project_data.build_dataset
.\.venv311\Scripts\python.exe -m evaluation.synthetic_project_data.validate
.\.venv311\Scripts\python.exe -m evaluation.synthetic_project_data.run_benchmark
```

Run the complete suite with isolated storage and no API credentials:

```powershell
$testRoot = Join-Path $env:TEMP ('raara-phase9a-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $testRoot -Force | Out-Null
$dbPath = (Join-Path $testRoot 'backend-tests.sqlite').Replace('\', '/')
$env:DATABASE_URL = "sqlite:///$dbPath"
$env:CHROMA_PERSIST_DIR = Join-Path $testRoot 'chroma'
$env:UPLOAD_DIR = Join-Path $testRoot 'uploads'
$env:TIKTOKEN_CACHE_DIR = 'C:\Users\Pratik Kalloli\AppData\Local\Temp\data-gym-cache'
$env:OPENAI_API_KEY = ''
.\.venv311\Scripts\python.exe -m pytest -q
```

