# RAARA Final Benchmark Consolidation — Phase 7E

**Classification: EVALUATION FRAMEWORK COMPLETE — LIVE EXPERIMENTS PENDING**

This consolidates measured Phase 6E–7D outputs. It does not claim a held-out benchmark, live OpenAI result, semantic faithfulness validation, or statistically significant prompt winner.

## Dataset and environment

- Dataset: 12 question, version 0.1.0 synthetic development set; synthetic PDFs are not official regulations.
- Dataset SHA-256 `db97d1d3d6d723fbdaea7a641dd1f37e988f48abd099145b903af61e5883bf8a`; manifest SHA-256 `f85a5e15f2dc4193c468f34e25bf249cfd50cb6a24d071359427d4c21234ecf7`.
- Held-out dataset: NOT AVAILABLE (0 questions); final held-out benchmark: BLOCKED pending independent permitted data.
- Python 3.11.9; Windows-10-10.0.26300-SP0; AMD64; 16 logical CPUs.
- Project chat model configured: `gpt-4.1-mini`; API key configured: `false`.
- Live OpenAI calls in Phase 7E: 0. Live integration: NOT TESTED. Semantic faithfulness: NOT TESTED.
- No production database, ChromaDB collection or application behavior was modified.

## Phase 7B retrieval benchmark

Offline isolated ChromaDB; `deterministic-tfidf-hash-v1`; cosine distance; threshold 0.35. The production retrieval configuration was unchanged.

| K | Precision@K | Recall@K | MRR | Hit rate | Mean retrieval latency |
|---:|---:|---:|---:|---:|---:|
| 1 | 0.100 (n=10) | 0.100 (n=10) | 0.100 (n=10) | 0.100 (n=10) | 28.969 ms (36 samples) |
| 3 | 0.033 (n=10) | 0.100 (n=10) | 0.100 (n=10) | 0.100 (n=10) | 29.645 ms (36 samples) |
| 5 | 0.020 (n=10) | 0.100 (n=10) | 0.100 (n=10) | 0.100 (n=10) | 29.686 ms (36 samples) |

15 gold evidence spans mapped exactly once by exact document/page/section matching. Only 1 of 10 answerable questions retrieved relevant evidence. Small synthetic corpus and offline embeddings limit these results; production embedding performance is unverified.

## Phase 7C answer and citation benchmark

Deterministic extractive mock; lexical metrics do not prove semantic correctness or faithfulness. Answerable questions:

| Metric | CONTROLLED_EVIDENCE | END_TO_END_RAG |
|---|---:|---:|
| normalized_exact_match | 0.000 (n=10) | 0.000 (n=10) |
| key_fact_coverage | 0.617 (n=10) | 0.100 (n=10) |
| claim_support_rate | 0.950 (n=10) | 1.000 (n=1) |
| claim_contradiction_rate | 0.050 (n=10) | 0.000 (n=1) |
| answer_relevance | 0.667 (n=10) | 0.100 (n=10) |
| citation_precision | 1.000 (n=10) | 0.100 (n=10) |
| citation_recall | 1.000 (n=10) | 0.100 (n=10) |
| document_accuracy | 1.000 (n=10) | 0.100 (n=10) |
| page_accuracy | 1.000 (n=10) | 0.100 (n=10) |

Unanswerable question metrics:
- correct_abstention_rate: controlled 1.000 (n=2); end-to-end 1.000 (n=2).
- false_answer_rate: controlled 0.000 (n=2); end-to-end 0.000 (n=2).
- fabricated_citation_rate: controlled 0.000 (n=2); end-to-end 0.000 (n=2).

CONTROLLED_EVIDENCE bypassed retrieval using gold evidence. END_TO_END_RAG retrieved once per question. These results do not measure OpenAI generation.

## Phase 7D prompt diagnostics

A/B/C tied because `deterministic-extractive-mock-v1` ignores prompt text. This does not measure prompt effects or show Prompt C improves grounding.

| Experiment | Prompt | Key-fact coverage | Citation precision | Citation recall | Correct abstention | Mean local mock ms | Tokens / cost |
|---|---|---:|---:|---:|---:|---:|---|
| CONTROLLED_EVIDENCE | A | 0.617 (n=10) | 1.000 (n=10) | 1.000 (n=10) | 1.000 (n=2) | 17.629 | null / null |
| CONTROLLED_EVIDENCE | B | 0.617 (n=10) | 1.000 (n=10) | 1.000 (n=10) | 1.000 (n=2) | 14.491 | null / null |
| CONTROLLED_EVIDENCE | C | 0.617 (n=10) | 1.000 (n=10) | 1.000 (n=10) | 1.000 (n=2) | 17.152 | null / null |
| END_TO_END_RAG | A | 0.100 (n=10) | 0.100 (n=10) | 0.100 (n=10) | 1.000 (n=2) | 14.060 | null / null |
| END_TO_END_RAG | B | 0.100 (n=10) | 0.100 (n=10) | 0.100 (n=10) | 1.000 (n=2) | 19.399 | null / null |
| END_TO_END_RAG | C | 0.100 (n=10) | 0.100 (n=10) | 0.100 (n=10) | 1.000 (n=2) | 18.708 | null / null |

Input/output/total token counts and estimated API cost are null, not zero. Local mock latency is not model latency. No significance claim is made.

### Existing prompt definition hashes

| Prompt | Name | System SHA-256 |
|---|---|---|
| A | Basic Prompt | `12a4ed981ffb88980998c9fd63a9c53bf6c0e17f1b51420ae1ed936dbb10c087` |
| B | Role-Based Contextual Prompt | `fa613a6859977d302ecad0c96d0ff5d66729de2f2ce2c3a9d3dcc8420c936fc6` |
| C | Structured Evidence-Constrained Prompt | `471b6bee34cf8d5fed841afd9d57dac9ab100bff0d8dd2924a854734448e2ed6` |

Shared user-template hash: `f058d8040c64dc0bbf44b0d9f4de7632c8902dfbaf181e66b41712e350547108`. Shared schema hash: `5f82414dae04f460f8c0f4f7e430b631565c66045529e00ef87c17167fb0ac97`.

## Visual summaries

Static figures below use only metrics measured in preserved phase artifacts.

![Phase 7B retrieval metrics](evaluation/results/figures/retrieval_metrics.svg)

![Phase 7C answer and citation metrics](evaluation/results/figures/answer_quality_metrics.svg)

![Phase 7D prompt mock diagnostics](evaluation/results/figures/prompt_diagnostics.svg)

## Live OpenAI gate

The live evaluation gate is fail-closed. At finalization, no API key was configured and the explicit opt-in/model/call/budget variables were not all configured. No client was created and no network request was made. Set `RAARA_ENABLE_LIVE_EVAL=true`, `RAARA_EVAL_MODEL`, `RAARA_EVAL_MAX_CALLS`, `RAARA_EVAL_MAX_BUDGET_USD`, and `OPENAI_API_KEY` only after explicit approval. Run `python -m evaluation.scripts.check_live_eval_readiness` to check readiness; it never calls OpenAI.

Future checklist: authorize model and maximum budget; independently review permitted held-out sources and annotations; pin dataset and prompt hashes; record generation parameters/repetitions; use dated pricing for cost; enforce per-request spend/call ceilings; preserve source metadata; and obtain human semantic-faithfulness review.

## Historical test outcomes

| Phase | Test outcome |
|---|---|
| 6E backend regression | 105 passed, 0 failed |
| 6E frontend tests/build | 7 passed; production build passed |
| 6E isolated API acceptance | 48 checks passed |
| 7A full backend | 129 passed, 0 failed |
| 7B full backend | 135 passed, 0 failed |
| 7C full backend | 148 passed, 0 failed |
| 7D full backend | 152 passed, 0 failed |

Phase 7E dataset validation passed (12 questions); evaluation tests: 52 passed, 0 failed; full backend suite: 157 passed, 0 failed (Python 3.11.9, isolated temporary SQLite/Chroma/upload paths). Browser acceptance, live OpenAI and semantic faithfulness remain NOT TESTED.

## Held-out annotation workflow

`evaluation/datasets/held_out/README.md` and `annotation_template.json` describe source review, annotation and split separation. The template is not a held-out sample. Do not move development questions into the held-out split.

## Preserved source artifact hashes

- `PHASE_6E_ACCEPTANCE_REPORT.md` — SHA-256 `c4ab542bb11788b86a609d7a0a045ab3202fdd374870e4e9369c840fd5eb610b`
- `PHASE_7A_REPORT.md` — SHA-256 `a540f447a10d23e638251d3ab2a81d978bd0854c7c24d9762578ad44c3d68d90`
- `PHASE_7B_REPORT.md` — SHA-256 `41cfee1e9a89e56b9e19a48484b08a471e3adb2b1eefcf93466efa4e44c8533e`
- `PHASE_7C_REPORT.md` — SHA-256 `7d215e9215c93ad38a6cfa6eb1762a441918fd85887722e470d6a92daf8cefda`
- `PHASE_7D_REPORT.md` — SHA-256 `d2649c52998fddd77f109f9a831231272c702fdd77fc9db16a11da3dee468379`
- `evaluation/results/retrieval_benchmark.json` — SHA-256 `6fcb2418f36e4efe30643f4464d57be2f145f0cd3cc32f298e84d196f74e5425`
- `evaluation/results/answer_quality_benchmark.json` — SHA-256 `460cc40c416d3b298bf642e054cb401285d761fee9b154071a77fc9287da3a5b`
- `evaluation/results/prompt_comparison.json` — SHA-256 `bff414f7a66568a5f1b2984549450f0407d69ddc6fd0c7820ad016867000f004`
- `evaluation/final_benchmark_config.json` — SHA-256 `fa271a57f3cdd60c5b54e96b06aaafc211bc8c540b1f340da742f4480084dfe4`
