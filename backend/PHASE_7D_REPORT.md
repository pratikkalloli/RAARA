# RAARA Phase 7D — A/B/C Prompt Engineering Experiment

## Outcome and interpretation

Phase 7D ran as **SIMULATED_PROMPT_DIAGNOSTICS**. No live OpenAI generation was authorized or performed. The existing prompt configurations were selected and hashed, but the deterministic Phase 7C mock does not interpret natural-language prompt text. Therefore A/B/C produced identical output and metric values. This is a limitation of the selected mock, not evidence that the prompts perform equivalently with a real language model. No prompt is declared a real-world winner, and no statistical significance is claimed.

The corpus contains 12 synthetic development questions, not official university policy. The embedding substitute was `deterministic-tfidf-hash-v1`; production embedding performance is unverified. The production chat model setting is `gpt-4.1-mini`, recorded but not called.

## Experiment methodology

### CONTROLLED_EVIDENCE

For each question, the existing Phase 7B exact ground-truth-to-chunk mapping supplied the same passage IDs, text, and source metadata to A, B, and C. Retrieval was bypassed. The same deterministic extractive mock adapter, structured response schema, and generation settings were used for all three selections. Twelve contexts were evaluated per prompt. The two unanswerable questions were supplied no evidence.

### END_TO_END_RAG

For each question, the existing production `Retriever` was invoked once against a temporary isolated ChromaDB collection. Its `RetrievalResult` object was passed unchanged to A, B, and C. Retrieval settings remained unchanged: cosine distance, top-K 5, configured relevance threshold 0.35, 700-token chunks, and 100-token overlap. Twelve retrieval operations fed 36 prompt-selected mock generations.

### Prompt selection and content hashes

Prompt definitions are read directly from `app/prompting/system_prompt.py`; the common user context is rendered with the existing `build_user_prompt`. Output metadata uses the existing `StructuredAnswer` schema. Content-addressed versions are SHA-256 hashes of system instruction content. The user template and output schema hashes are shared across the prompts.

| ID | Existing prompt definition | System instruction SHA-256 |
|---|---|---|
| A | Basic Prompt | `12a4ed981ffb88980998c9fd63a9c53bf6c0e17f1b51420ae1ed936dbb10c087` |
| B | Role-Based Contextual Prompt | `fa613a6859977d302ecad0c96d0ff5d66729de2f2ce2c3a9d3dcc8420c936fc6` |
| C | Structured Evidence-Constrained Prompt | `471b6bee34cf8d5fed841afd9d57dac9ab100bff0d8dd2924a854734448e2ed6` |

- Shared user-template SHA-256: `f058d8040c64dc0bbf44b0d9f4de7632c8902dfbaf181e66b41712e350547108`
- Shared `StructuredAnswer` schema SHA-256: `5f82414dae04f460f8c0f4f7e430b631565c66045529e00ef87c17167fb0ac97`
- Every prompt/context/schema combination also has a per-question combined SHA-256 in the JSON artifact.

For each comparison, the evidence fingerprint, passage IDs, user payload hash, schema hash, model adapter, and generation settings were identical across A/B/C. Only the selected prompt configuration and its system instruction hash differed. The mock records the selected prompt type but does not consume the instructions. Its deterministic response was repeat-checked in tests.

## Results

Every prompt has identical answer and citation metrics within each experiment. Values below are for each of A, B, and C. `n` is the metric denominator shown in the generated JSON/Markdown. For claim metrics, the aggregate is a macro-average over questions with claim observations; claim counts are available per question.

### CONTROLLED_EVIDENCE

| Metric | A | B | C |
|---|---:|---:|---:|
| Normalized exact match | 0.000 (n=10) | 0.000 (n=10) | 0.000 (n=10) |
| Key-fact coverage | 0.617 (n=10) | 0.617 (n=10) | 0.617 (n=10) |
| Claim support rate | 0.950 (n=10) | 0.950 (n=10) | 0.950 (n=10) |
| Claim contradiction rate | 0.050 (n=10) | 0.050 (n=10) | 0.050 (n=10) |
| Answer relevance | 0.667 (n=10) | 0.667 (n=10) | 0.667 (n=10) |
| Citation precision / recall | 1.000 / 1.000 (n=10) | 1.000 / 1.000 (n=10) | 1.000 / 1.000 (n=10) |
| Document / page accuracy | 1.000 / 1.000 (n=10) | 1.000 / 1.000 (n=10) | 1.000 / 1.000 (n=10) |
| Correct abstention rate | 1.000 (n=2) | 1.000 (n=2) | 1.000 (n=2) |
| False-answer rate | 0.000 (n=2) | 0.000 (n=2) | 0.000 (n=2) |
| Fabricated-citation rate | 0.000 (n=2) | 0.000 (n=2) | 0.000 (n=2) |

### END_TO_END_RAG

| Metric | A | B | C |
|---|---:|---:|---:|
| Normalized exact match | 0.000 (n=10) | 0.000 (n=10) | 0.000 (n=10) |
| Key-fact coverage | 0.100 (n=10) | 0.100 (n=10) | 0.100 (n=10) |
| Claim support rate | 1.000 (n=1) | 1.000 (n=1) | 1.000 (n=1) |
| Claim contradiction rate | 0.000 (n=1) | 0.000 (n=1) | 0.000 (n=1) |
| Answer relevance | 0.100 (n=10) | 0.100 (n=10) | 0.100 (n=10) |
| Citation precision / recall | 0.100 / 0.100 (n=10) | 0.100 / 0.100 (n=10) | 0.100 / 0.100 (n=10) |
| Document / page accuracy | 0.100 / 0.100 (n=10) | 0.100 / 0.100 (n=10) | 0.100 / 0.100 (n=10) |
| Correct abstention rate | 1.000 (n=2) | 1.000 (n=2) | 1.000 (n=2) |
| False-answer rate | 0.000 (n=2) | 0.000 (n=2) | 0.000 (n=2) |
| Fabricated-citation rate | 0.000 (n=2) | 0.000 (n=2) | 0.000 (n=2) |

The end-to-end run generated a claim for only one of ten answerable questions; claim support and contradiction metrics therefore have `n=1`. Nine answerable questions had no retrieved evidence and abstained. This is consistent with the weak Phase 7B retrieval baseline and does not establish prompt behavior.

### Per-category key-fact coverage (identical for A, B, and C)

| Category | Questions | CONTROLLED_EVIDENCE | END_TO_END_RAG |
|---|---:|---:|---:|
| direct_factual | 3 | 1.000 | 0.333 |
| multi_passage | 2 | 0.750 | 0.000 |
| multi_document | 1 | 0.000 | 0.000 |
| conflicting_version | 2 | 0.583 | 0.000 |
| prompt_injection | 2 | 0.250 | 0.000 |
| unanswerable | 2 | N/A | N/A |

The JSON artifact includes per-category values for all evaluator metrics and per-question prompt, hash, retrieval, response, and citation details. No score is synthesized into an overall prompt ranking.

## Latency, tokens, and cost

| Experiment | Prompt | Mean local adapter latency (ms) | Input tokens | Output tokens | Total tokens | Estimated API cost |
|---|---|---:|---:|---:|---:|---:|
| CONTROLLED_EVIDENCE | A | 17.629267 | null | null | null | null |
| CONTROLLED_EVIDENCE | B | 14.490917 | null | null | null | null |
| CONTROLLED_EVIDENCE | C | 17.151933 | null | null | null | null |
| END_TO_END_RAG | A | 14.059758 | null | null | null | null |
| END_TO_END_RAG | B | 19.398817 | null | null | null | null |
| END_TO_END_RAG | C | 18.708267 | null | null | null | null |

These latency measurements are local Python mock execution time and are not model latency. The deterministic adapter reports no token usage. No pricing snapshot is configured, so estimated API costs are null rather than zero.

## Analysis

- **Best-performing prompt:** A, B, and C tie for every reported metric because the same deterministic output is returned for each selection. This is not a real prompt winner.
- **Evidence discipline:** whether C improves evidence discipline is not measurable with this adapter. Citation verifier outcomes are the same across prompt types because generated output is the same.
- **Prompt differences:** definition hashes prove the existing system instructions differ. Output metrics cannot measure those instruction differences because the mock does not read them.
- **Nondeterminism:** the mock output is deterministic and repeat-tested. Timing varies due to local execution and should not be compared as language-model latency.
- **Significance:** no significance analysis was conducted; 12 synthetic questions and a non-prompt-aware adapter are inadequate for inference.

## Verification and files

- Phase 7A dataset validator: **12 questions validated**.
- Phase 7A–7D evaluation suite: **47 passed**.
- Full backend suite: **152 passed, 0 failed**, Python 3.11.9, with temporary SQLite, ChromaDB, and upload paths.
- Phase 7B and 7C result artifacts were preserved. No production prompt, retrieval, citation, database, or Chroma behavior was changed. No live OpenAI API call was made.

Created:

- `backend/evaluation/prompt_experiments/__init__.py`
- `backend/evaluation/prompt_experiments/runner.py`
- `backend/evaluation/scripts/run_prompt_comparison.py`
- `backend/evaluation/tests/test_prompt_experiments.py`
- `backend/evaluation/results/prompt_comparison.json`
- `backend/evaluation/results/prompt_comparison.md`
- `backend/PHASE_7D_REPORT.md`

Modified: `backend/evaluation/README.md`.

## Limitations and recommendation for Phase 7E

No actual LLM received prompts A/B/C. The current comparison validates experiment plumbing, prompt/context/schema hash tracking, same-evidence fairness, and metric reuse only. It does not verify that C improves grounding, abstention, citation quality, or answer correctness. Synthetic corpus limitations and the very low end-to-end retrieval hit rate remain. The held-out dataset remains unpopulated.

For Phase 7E, first obtain explicit authorization and access for a fixed production-capable model, then run a preregistered A/B/C comparison with identical retrieval contexts and generation parameters, repeated model samples, and an independently reviewed held-out set. Keep controlled-evidence and end-to-end results separate, record provider token usage and a dated pricing snapshot, and use human review for semantic faithfulness. Do not tune using held-out labels.

## PowerShell verification commands

Run from `C:\prompt_mini_proj\backend`:

```powershell
.\.venv311\Scripts\python.exe -m evaluation.scripts.validate_dataset --dataset evaluation\datasets\development\raara_synthetic_starter_v0.1.0.jsonl --manifest evaluation\datasets\development\manifest.json
.\.venv311\Scripts\python.exe -m pytest -v evaluation\tests
.\.venv311\Scripts\python.exe -m evaluation.scripts.run_prompt_comparison
```

For the full backend suite, set `DATABASE_URL`, `CHROMA_PERSIST_DIR`, and `UPLOAD_DIR` to unique temporary paths, then run `.\.venv311\Scripts\python.exe -m pytest -v`.
