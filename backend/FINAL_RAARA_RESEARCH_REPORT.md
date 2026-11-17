# RAARA Final Research Report

## Result

**Classification: EVALUATION FRAMEWORK COMPLETE — LIVE EXPERIMENTS PENDING.**

Phase 7E consolidates the existing Phase 6E and 7A–7D results, records configuration and provenance, adds a fail-closed live-evaluation readiness check, and documents a held-out annotation workflow. No application, production retrieval, prompt, citation-verification, database, or Chroma behavior was changed. No OpenAI client was created and no live API request was made.

The 12-question development corpus and its two PDFs are synthetic and not official academic regulations. No held-out set exists; held-out scoring is **BLOCKED**. The historical reports and benchmark artifacts were preserved. Consolidated results are in `evaluation/results/final_benchmark.json` and `.md`; exact future run settings are in `evaluation/final_benchmark_config.json`.

## Environment and provenance

- Python: 3.11.9; Windows 10, AMD64; 16 logical CPUs; processor reported by Python as Intel64 Family 6 Model 186 Stepping 2.
- Configured project chat model: `gpt-4.1-mini`; configured embedding model: `text-embedding-3-small`.
- OpenAI key configured at finalization: **no**. Live model availability was not checked because no live request was authorized.
- Development dataset version: `0.1.0`, 12 synthetic questions.
- Dataset SHA-256: `db97d1d3d6d723fbdaea7a641dd1f37e988f48abd099145b903af61e5883bf8a`.
- Manifest SHA-256: `f85a5e15f2dc4193c468f34e25bf249cfd50cb6a24d071359427d4c21234ecf7`.
- Held-out data: 0 records; **NOT AVAILABLE**. Its benchmark is **BLOCKED**, not passed.
- Finalization made no production SQLite or ChromaDB writes. No frontend files were changed.

## Consolidated measured results

### Phase 7B — Retrieval

The benchmark used an isolated temporary ChromaDB, 12 chunks, cosine distance, threshold 0.35, and the unchanged 700-token/100-token-overlap settings. Query/index vectors used the offline substitute `deterministic-tfidf-hash-v1`, not the configured production embedding model. There were 12 synthetic questions, three repetitions, and 15 gold evidence spans mapped exactly once using exact document, page, and section matching.

| K | Precision@K | Recall@K | MRR | Hit rate | Mean retrieval latency |
|---:|---:|---:|---:|---:|---:|
| 1 | 0.100 (n=10) | 0.100 (n=10) | 0.100 (n=10) | 0.100 (n=10) | 28.969 ms (36 samples) |
| 3 | 0.033 (n=10) | 0.100 (n=10) | 0.100 (n=10) | 0.100 (n=10) | 29.645 ms (36 samples) |
| 5 | 0.020 (n=10) | 0.100 (n=10) | 0.100 (n=10) | 0.100 (n=10) | 29.687 ms (36 samples) |

Only **1 of 10 answerable questions** retrieved relevant evidence. This is a weak baseline on the synthetic corpus with an offline lexical embedding substitute. Production embedding performance is unverified. Latency is local retrieval timing, not hosted model or production-service latency.

### Phase 7C — Answer quality and citations

The `CONTROLLED_EVIDENCE` condition bypassed retrieval and supplied gold-aligned evidence. `END_TO_END_RAG` used isolated retrieval. Both used `deterministic-extractive-mock-v1`. The metrics are deterministic lexical/evaluator measures and do not establish semantic entailment or faithfulness. Denominators appear beside each value.

| Answerable metric | CONTROLLED_EVIDENCE | END_TO_END_RAG |
|---|---:|---:|
| Normalized exact match | 0.000 (n=10) | 0.000 (n=10) |
| Key-fact coverage | 0.617 (n=10) | 0.100 (n=10) |
| Claim support rate | 0.950 (n=10) | 1.000 (n=1) |
| Claim contradiction rate | 0.050 (n=10) | 0.000 (n=1) |
| Answer relevance | 0.667 (n=10) | 0.100 (n=10) |
| Citation precision / recall | 1.000 / 1.000 (n=10) | 0.100 / 0.100 (n=10) |
| Document / page accuracy | 1.000 / 1.000 (n=10) | 0.100 / 0.100 (n=10) |

On the two unanswerable questions, correct abstention was 1.000 (n=2), false-answer rate 0.000 (n=2), and fabricated-citation rate 0.000 (n=2) for each condition. The end-to-end claim-support denominator is one; it must not be read as support for the other nine answerable questions.

### Phase 7D — A/B/C prompt diagnostics

The existing prompt configurations and content hashes were retained. Each prompt received identical questions, evidence, retrieval result, metadata, adapter and response schema within a condition. Retrieval ran once per question in end-to-end evaluation. The mock does not interpret prompt text; A, B and C returned identical outputs. These are simulated diagnostics and cannot show whether a real model responds differently or whether Prompt C improves evidence discipline.

| Condition | Prompt | Key-fact coverage | Claim support | Answer relevance | Citation precision / recall | Correct abstention (n=2) | Mean local mock latency |
|---|---|---:|---:|---:|---:|---:|---:|
| Controlled | A / B / C | 0.617 (n=10) | 0.950 (n=10) | 0.667 (n=10) | 1.000 / 1.000 (n=10) | 1.000 | A 17.629, B 14.491, C 17.152 ms |
| End-to-end | A / B / C | 0.100 (n=10) | 1.000 (n=1) | 0.100 (n=10) | 0.100 / 0.100 (n=10) | 1.000 | A 14.060, B 19.399, C 18.708 ms |

The prompt hashes, shared user-template hash and shared response-schema hash are in the final JSON/Markdown and preserved Phase 7D output. Local adapter latency is not generation-model latency. Input, output and total tokens are unavailable (`null`); estimated API cost is also `null` because neither token usage nor a dated pricing snapshot is available. No statistically significant winner is claimed.

Existing system-prompt versions are identified by their content hashes:

| Prompt | Existing definition | System prompt SHA-256 |
|---|---|---|
| A | Basic Prompt | `12a4ed981ffb88980998c9fd63a9c53bf6c0e17f1b51420ae1ed936dbb10c087` |
| B | Role-Based Contextual Prompt | `fa613a6859977d302ecad0c96d0ff5d66729de2f2ce2c3a9d3dcc8420c936fc6` |
| C | Structured Evidence-Constrained Prompt | `471b6bee34cf8d5fed841afd9d57dac9ab100bff0d8dd2924a854734448e2ed6` |

Shared user-template SHA-256: `f058d8040c64dc0bbf44b0d9f4de7632c8902dfbaf181e66b41712e350547108`. Shared `StructuredAnswer` schema SHA-256: `5f82414dae04f460f8c0f4f7e430b631565c66045529e00ef87c17167fb0ac97`.

### Category comparison

Phase 7C key-fact coverage by category was identical across A/B/C in Phase 7D because the mock ignored prompt text. `n` is the number of questions in the category; unanswerable examples are not scored for key-fact coverage.

| Category | n | Controlled evidence | End-to-end RAG |
|---|---:|---:|---:|
| direct_factual | 3 | 1.000 | 0.333 |
| multi_passage | 2 | 0.750 | 0.000 |
| multi_document | 1 | 0.000 | 0.000 |
| conflicting_version | 2 | 0.583 | 0.000 |
| prompt_injection | 2 | 0.250 | 0.000 |
| unanswerable | 2 | N/A | N/A |

The broader by-category metric groups and their metric-specific denominators are preserved in `evaluation/results/answer_quality_benchmark.json` and `prompt_comparison.json`; one-question categories and small subgroups are descriptive only.

## OpenAI authorization and cost gate

At finalization, the project-configured model string was `gpt-4.1-mini`, but no API key was configured. Live model availability was not tested. The live-evaluation readiness check reported `ready: false` with all five expected blockers: missing explicit opt-in, API key, evaluation model, positive call limit, and positive budget limit. Its exit code was 2. The check does not initialize an OpenAI client, print credentials, or make network requests.

The gate requires explicit `RAARA_ENABLE_LIVE_EVAL=true`, `OPENAI_API_KEY`, `RAARA_EVAL_MODEL`, positive `RAARA_EVAL_MAX_CALLS`, and positive finite `RAARA_EVAL_MAX_BUDGET_USD`. Readiness is not authorization. Any future run requires explicit approval, an independently reviewed held-out set, pinned prompts and generation parameters, a dated pricing snapshot, per-request call/spend limits, and human review of semantic faithfulness. Phase 7E made **zero** live calls.

## Held-out preparation

`evaluation/datasets/held_out/README.md` documents source permissions, source hashing, independent review, annotation, schema validation, frozen labels, and split discipline. `evaluation/datasets/held_out/annotation_template.json` is explicitly a **template only**, not an example question or benchmark item. No development item was copied or relabeled as held-out. Do not claim held-out performance until a valid, permitted and independently reviewed dataset has been supplied and frozen.

## Static visualizations

Three dependency-free SVG figures are generated from measured artifacts by `python -m evaluation.scripts.build_final_benchmark`:

- `evaluation/results/figures/retrieval_metrics.svg`
- `evaluation/results/figures/answer_quality_metrics.svg`
- `evaluation/results/figures/prompt_diagnostics.svg`

The prompt figure explicitly identifies the A/B/C tie as a mock diagnostic, not a prompt-quality result. No chart is produced for unavailable token or cost data.

## Verification results

- Phase 7A dataset validator: **passed**, 12 questions validated.
- Phase 7A–7D plus Phase 7E evaluation tests: **52 passed, 0 failed**.
- Full backend suite: **157 passed, 0 failed**. Pytest ran under Python 3.11.9 with temporary SQLite, ChromaDB and upload paths. The initial restricted run stalled during `TestClient` startup at Windows `socket.socketpair()`; the verified rerun with local socket access completed in 39.01 seconds.
- The first evaluation-suite attempt without a tiktoken cache had 4 failures from attempted network fetches of the tokenizer data. Setting `TIKTOKEN_CACHE_DIR` to the already-present local cache and rerunning the same suite produced the 52-pass result above. No OpenAI API was involved.
- Phase 6E historical outcomes: backend 105 passed; frontend tests 7 passed; production build passed; isolated API acceptance 48 checks passed. Browser acceptance, live OpenAI, and semantic faithfulness were **NOT TESTED**.
- Historical full-backend outcomes: Phase 7A 129 passed; 7B 135 passed; 7C 148 passed; 7D 152 passed. Phase 7E's current 157-test run includes all existing backend and evaluation tests.

## Files created or modified

Created:

- `backend/PHASE_7E_REPORT.md`
- `backend/FINAL_RAARA_RESEARCH_REPORT.md`
- `backend/evaluation/final_benchmark.py`
- `backend/evaluation/final_benchmark_config.json`
- `backend/evaluation/live_eval_gate.py`
- `backend/evaluation/scripts/build_final_benchmark.py`
- `backend/evaluation/scripts/check_live_eval_readiness.py`
- `backend/evaluation/datasets/held_out/annotation_template.json`
- `backend/evaluation/results/final_benchmark.json`
- `backend/evaluation/results/final_benchmark.md`
- `backend/evaluation/results/figures/retrieval_metrics.svg`
- `backend/evaluation/results/figures/answer_quality_metrics.svg`
- `backend/evaluation/results/figures/prompt_diagnostics.svg`
- `backend/evaluation/tests/test_final_benchmark.py`

Modified:

- `backend/evaluation/README.md`
- `backend/evaluation/datasets/held_out/README.md`

No production code, database or Chroma data was changed. Historical result files and prior phase reports were preserved.

## Remaining limitations and recommendation

The main blockers for research-grade evaluation are the missing permitted real-policy dataset, empty held-out split, weak offline retrieval, lack of production embedding performance data, simulated prompt diagnostics, no live OpenAI validation, and no human semantic-faithfulness assessment. The existing evaluator's claim/support metrics are deterministic heuristics.

Next, obtain and independently review a permitted corpus and held-out annotations; then explicitly authorize one fixed model, bounded call count and budget. Run the already-defined controlled-evidence and end-to-end conditions without tuning against held-out labels. Review citation faithfulness and semantic correctness with qualified human annotators before drawing conclusions.

## PowerShell verification commands

Run from `C:\prompt_mini_proj\backend`:

```powershell
$env:TIKTOKEN_CACHE_DIR = 'C:\Users\Pratik Kalloli\AppData\Local\Temp\data-gym-cache'
.\.venv311\Scripts\python.exe -m evaluation.scripts.validate_dataset --dataset evaluation\datasets\development\raara_synthetic_starter_v0.1.0.jsonl --manifest evaluation\datasets\development\manifest.json
.\.venv311\Scripts\python.exe -m pytest -v evaluation\tests
.\.venv311\Scripts\python.exe -m evaluation.scripts.build_final_benchmark
.\.venv311\Scripts\python.exe -m evaluation.scripts.check_live_eval_readiness
```

The readiness command exits 2 while the live-evaluation requirements are not configured; it does not run OpenAI. To run the full backend suite in an environment where the Windows `socket.socketpair()` used by the TestClient is available, use isolated paths:

```powershell
$testRoot = Join-Path $env:TEMP ('raara-phase7e-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $testRoot | Out-Null
$dbPath = (Join-Path $testRoot 'raara-test.sqlite').Replace('\', '/')
$env:DATABASE_URL = "sqlite:///$dbPath"
$env:CHROMA_PERSIST_DIR = Join-Path $testRoot 'chroma'
$env:UPLOAD_DIR = Join-Path $testRoot 'uploads'
$env:TIKTOKEN_CACHE_DIR = 'C:\Users\Pratik Kalloli\AppData\Local\Temp\data-gym-cache'
.\.venv311\Scripts\python.exe -m pytest -v
```

No Phase 8 work was started.


