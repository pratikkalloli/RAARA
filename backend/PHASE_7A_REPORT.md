# RAARA Phase 7A — Evaluation Foundation Report

## Result

Phase 7A establishes a versioned synthetic development dataset, source/evidence schema and validator, deterministic metric functions, and reproducibility documentation. It does **not** run production RAG or score model answers. Production retrieval, prompts, citation verification, API behavior, SQLite, and ChromaDB were not modified.

## Evaluation directory

Created `backend/evaluation/` with:

- `datasets/development/`: version `0.1.0` JSONL, manifest, and generated source PDFs.
- `datasets/held_out/README.md`: explicit empty held-out split; no test labels were fabricated.
- `schemas/dataset.py`: typed question/evidence schema, JSONL loader, dataset/manifest/source validator.
- `metrics/`: retrieval, answer, citation, and performance functions.
- `scripts/`: synthetic source builder and dataset validation CLI.
- `tests/`: deterministic schema and metric tests.
- `evaluation_config.json`, `README.md`, and `results/README.md`.

This is separate from the existing prompt experiment runner at `app/evaluation/experiments.py`, which was inspected and left unchanged.

## Dataset and source documents

No permitted academic policy source files were present in the project’s `documents/` or `documentation/` directories, and the existing root `evaluation_dataset/` directory had no dataset files. The starter therefore contains **12 synthetic development questions**, not the suggested ~50-question benchmark and not real university policy.

| Category | Questions |
|---|---:|
| Direct factual | 3 |
| Multi-passage | 2 |
| Multi-document | 1 |
| Unanswerable | 2 |
| Conflicting/version-sensitive | 2 |
| Prompt-injection resistance | 2 |
| **Total** | **12** |

Two reproducibly generated PDF fixtures accompany the dataset: synthetic Academic Guide versions 1 and 2. Every page states that it is a synthetic test document and not official university policy. Facts, dates, percentages, sample tokens, version changes, and injection strings are fictional. The manifest includes stable evaluation document IDs, version/effective date, page count, source type, PDF path, and SHA-256. Stable evidence IDs are evaluation labels; they are not production SQLite document IDs or Chroma chunk IDs.

## Schema and validation

Each JSONL record supports `question_id`, `question`, `category`, `expected_status`, optional `reference_answer`, relevant document IDs, one-based page/section references, exact evidence text and stable evidence IDs, expected claims, notes, dataset version, source type, and adversarial attack surface.

Validation checks schema/category/status, nonblank questions, unique IDs, manifest/dataset version agreement, document/page references, page bounds, source file containment and existence, source hashes, and that evidence text appears on the declared PDF page. Unanswerable examples must use `NOT_FOUND` and have no fabricated answer, claims, documents, pages, or evidence. The validator passed for all **12 records** with the distribution above.

## Metrics implemented

- **Precision@K:** unique relevant retrieved IDs in the first K results divided by K; duplicate IDs retain their first position.
- **Recall@K:** unique relevant hits divided by the number of gold relevant IDs; unavailable (`None`) when the gold set is empty.
- **Reciprocal rank and MRR:** first unique relevant rank; MRR averages queries with nonempty gold sets and excludes unanswerable queries.
- **Citation precision/recall:** set-based matching of unique evidence IDs; citation recall is unavailable for an empty gold evidence set.
- **Document identification accuracy:** exact document-ID set match.
- **Page accuracy:** proportion of predicted unique `(document_id, page)` pairs present in the gold page set.
- **Normalized exact match:** binary Unicode/case/punctuation/whitespace-normalized string equality only.
- **Semantic assessment interface:** optional externally supplied human or future LLM-judge values for claim correctness, faithfulness, and answer relevance. No judge is implemented or invoked, and no semantic scores were produced.
- **Performance helpers:** retrieval/generation/total latency, input/output tokens, and estimated API cost. Unknown measurements remain unavailable; cost requires explicit usage counts and a caller-supplied rate snapshot.

The README defines formulas, empty-result behavior, duplicate handling, and the distinction between structural citation matching and semantic support. A future runner must map runtime Chroma IDs/passages to stable gold evidence labels; that alignment is not implemented in Phase 7A.

## Reproducibility and held-out separation

`evaluation_config.json` records K=5, relevance threshold 0.35, cosine distance, embedding model `text-embedding-3-small`, `OPENAI_CHAT_MODEL` with current project-config default `gpt-4.1-mini`, prompt types A/B/C, duplicate policy, seed status, and the absence of a cost-rate snapshot. These are evaluation records only; production configuration was not changed.

The held-out directory is empty. Development data must not be relabelled as held-out or used to claim an unbiased test result. Phase 6E reported live OpenAI behavior untested; Phase 7A makes no live API calls and does not change that status.

## Test results

- Evaluation-only test suite: **24 passed, 0 failed**.
- Full backend suite: **129 passed, 0 failed**.
- Dataset CLI validation: **12 records validated**, 6 categories, no validation failures.
- Live OpenAI calls: **0**.
- Production database/Chroma writes: **0**. Full backend tests used process-only temporary database, Chroma, and upload paths to isolate application import-time schema setup.

The 24 new tests include dataset loading and rejection cases, duplicate ID/version/page/evidence checks, Precision@K, Recall@K, MRR, citation metrics, page/document accuracy, empty retrieval, unanswerable cases, multiple relevant IDs, duplicate results, exact-match limitations, semantic-assessor requirements, and missing latency/token/cost data.

## Files created or modified

Created:

- `backend/evaluation/README.md`
- `backend/evaluation/evaluation_config.json`
- `backend/evaluation/datasets/development/manifest.json`
- `backend/evaluation/datasets/development/raara_synthetic_starter_v0.1.0.jsonl`
- `backend/evaluation/datasets/development/sources/SYNTHETIC_NOT_OFFICIAL_Academic_Guide_v1.pdf`
- `backend/evaluation/datasets/development/sources/SYNTHETIC_NOT_OFFICIAL_Academic_Guide_v2.pdf`
- `backend/evaluation/datasets/held_out/README.md`
- `backend/evaluation/results/README.md`
- `backend/evaluation/schemas/` package and dataset schema/validator
- `backend/evaluation/metrics/` package and metric modules
- `backend/evaluation/scripts/` source builder and validation CLI
- `backend/evaluation/tests/test_dataset.py`
- `backend/evaluation/tests/test_metrics.py`
- `backend/PHASE_7A_REPORT.md`

No existing project source files were modified. No dependencies were added.

## Commands

Run from `C:\prompt_mini_proj\backend`:

```powershell
.\.venv311\Scripts\python.exe -m evaluation.scripts.build_synthetic_sources
.\.venv311\Scripts\python.exe -m evaluation.scripts.validate_dataset --dataset evaluation\datasets\development\raara_synthetic_starter_v0.1.0.jsonl --manifest evaluation\datasets\development\manifest.json
.\.venv311\Scripts\python.exe -m pytest -v evaluation\tests
```

Full backend regression command:

```powershell
.\.venv311\Scripts\python.exe -m pytest -v
```

For the full-suite run in this phase, process-only `DATABASE_URL`, `CHROMA_PERSIST_DIR`, and `UPLOAD_DIR` pointed to a newly generated directory under `$env:TEMP\raara-phase7a-regression-*`; this avoids the production defaults while `app.main` is imported during tests.

## Limitations and Phase 7B

- Only synthetic sources are available; the starter is intentionally small and not representative of real regulations.
- No held-out set exists.
- No production retrieval/generation evaluation run, live OpenAI call, latency/cost benchmark, claim-level semantic scoring, or faithfulness measurement was performed.
- Runtime Chroma-passage to stable gold-evidence matching remains to be designed and validated before passage-level production scores can be reported.

Phase 7B can add a reproducible evaluation runner that records retrieval/generation outputs and configuration, calculates these deterministic metrics, supports separately attributed human/judge assessments, and writes versioned results without using the held-out set for tuning. Do not begin it without approval.
