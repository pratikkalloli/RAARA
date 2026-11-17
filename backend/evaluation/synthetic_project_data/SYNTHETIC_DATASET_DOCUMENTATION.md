# Synthetic Academic Policy Corpus and Evaluation Dataset

## Classification and scope

The `SYNTHETIC_PROJECT_DATA` corpus is an academic demonstration built from user-provided values and explicitly identified defaults. It is **not an official PES University policy system** and must not be used for real student decisions. Every document, question, expected answer, evidence reference, manifest and conflict scenario carries `dataset_type: SYNTHETIC_PROJECT_DATA`, `is_official_university_policy: false`, `source_type: PROJECT_AUTHORED`, and version `9A.1.0`.

## Contents

- 10 current-model synthetic policy documents in Markdown and generated one-page PDF form.
- 2 older synthetic PDFs stored separately as controlled conflict/version fixtures; they are not in the primary corpus manifest or index.
- 50 synthetic questions with deterministic answer keys, evidence spans, expected citations, rationale, difficulty, and split metadata.
- 86 exact evidence references validated against the specified PDF page and section/chunk.
- Question splits: 36 synthetic development, 11 synthetic held-out, and 3 separate controlled-conflict questions.
- The 11-question synthetic held-out split is distinct from `evaluation/datasets/held_out/`, which remains reserved for independently sourced/approved real documents. Synthetic held-out data must not be represented as that real-source set.

The category totals are: direct factual 8; attendance/eligibility 6; ISA/ESA calculations 6; grading/SGPA/CGPA 6; backlogs/supplementary 5; lateral entry/progression 5; multi-passage 4; multi-document 3; version/scope conflicts 3; unanswerable 2; prompt injection 2.

## Modelled rules and declared defaults

All details are project-model data, not claims about PES University. The provided eight-semester, 24-credits-per-semester, 192-credit regular-entry structure, lateral-entry Semester 3 entry, Mathematics bridge classes, entry-specific progression thresholds (72 regular / 24 lateral), attendance 75%, and ISA/ESA/lab weights are represented as specified.

Grade boundaries, 35% pass threshold, E/F handling, CGPA 8-to-72.5% illustration, credit-weighted formulas, and backlog/supplementary behavior are labeled project defaults. Revaluation deadline (7 calendar days), fee (₹500 per subject), processing time (15 working days), and no-decrease assumption are explicitly synthetic defaults because exact source rules were not supplied.

The PDF builder uses extractable ASCII equivalents for certain typographic characters: multiplication `×` becomes `*`, dash variants become `-`, and the rupee symbol is rendered as `INR`. Source Markdown retains the human-readable supplied symbols. Ground-truth evidence strings match the generated, extractable PDF text exactly.

## Dataset separation and evaluation discipline

- `corpus/` contains only current project-model documents.
- `conflicts/` contains two historical project-model PDFs and three version/scope scenarios, with document versions, effective dates, applicability and expected resolution.
- `datasets/development/questions.json` is the only question split used by the Phase 9A benchmark runner.
- `datasets/held_out/questions.json` is not used for prompt or retrieval tuning and is not scored by the current runner.
- `datasets/conflict/questions.json` is separate from both question splits.
- No synthetic document enters the official Phase 8A held-out registry or production application storage.

## Reproducible build, validation and offline comparison

Run from `backend`:

```powershell
$env:TIKTOKEN_CACHE_DIR = 'C:\Users\Pratik Kalloli\AppData\Local\Temp\data-gym-cache'
.\.venv311\Scripts\python.exe -m evaluation.synthetic_project_data.build_dataset
.\.venv311\Scripts\python.exe -m evaluation.synthetic_project_data.validate
.\.venv311\Scripts\python.exe -m evaluation.synthetic_project_data.run_benchmark
```

The builder regenerates PDFs, hashes, manifests and question splits from committed Markdown and the deterministic question bank. The validator reuses `EvaluationQuestion` and `validate_dataset` to check schemas, provenance, file hashes, page count, exact PDF evidence, expected citations, answerability, category counts, split overlap and numerical arithmetic. The runner reuses existing Phase 7D prompt comparison, retriever, chunker, evaluation indexer, citation verifier, metrics and deterministic mock generation. It indexes only the 10-document primary corpus into a temporary Chroma directory and runs only development questions. Existing production retrieval parameters and prompt definitions are unchanged.

No live OpenAI calls are made. A/B/C use `deterministic-extractive-mock-v1`, which does not interpret prompts; equal results do not show prompt equivalence or real-model performance. Retrieval uses `deterministic-tfidf-hash-v1`, not `text-embedding-3-small`. This benchmark is a pipeline diagnostic, not semantic validation. Automated exact-text and lexical heuristics do not prove claim entailment, answer correctness, or faithfulness.

## Artifacts

- `synthetic_dataset_manifest.json`
- `synthetic_conflict_manifest.json`
- `datasets/synthetic_questions.json` and split-specific `questions.json` files
- `conflicts/synthetic_conflict_scenarios.json`
- `results/benchmark_validation_report.json` and `.md`
- `results/synthetic_prompt_comparison.json` and `.md`

