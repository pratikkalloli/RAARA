# Phase 9A Synthetic Benchmark Validation

**Synthetic academic demonstration only — not official PES University policy.**

- Corpus documents: 10 current-model policies.
- Conflict fixtures: 2 superseded synthetic documents.
- Questions: 50 across development (36), synthetic held-out (11), and separate conflict (3) partitions.
- Exact page-level evidence references validated: 86.
- Numeric checks: 2 question calculations and 2 policy examples independently recomputed.
- A/B/C development diagnostics: 36 questions; conditions CONTROLLED_EVIDENCE and END_TO_END_RAG.
- Adapter/model: `deterministic-extractive-mock-v1`; embedding: `deterministic-tfidf-hash-v1`.
- Held-out scoring: NOT RUN. Conflict scenarios: kept out of the primary current-policy index.
- Live OpenAI calls: none. Production retrieval settings and storage: unchanged.

## Interpretation

The deterministic mock ignores natural-language prompt instructions and returns the same extractive output for A, B, and C. Metric equality is an adapter limitation, not evidence that the prompts are equivalent for a real language model.

A/B/C outputs are deterministic mock diagnostics, not real LLM performance. Automated exact-text and lexical metrics do not verify semantic faithfulness.

## Artifacts

- `results/synthetic_prompt_comparison.json` and `.md`: existing prompt experiment runner output over development questions only.
- This report's JSON companion contains metric values and dataset checksums.

## Limitations

- All policies, documents and questions are project-authored synthetic data, not university regulations.
- Only development questions were used for the diagnostic run; synthetic held-out questions were not used for tuning or scoring in this run.
- Conflict scenarios are kept in a separate corpus and were validated, not merged into the primary current-policy index.
- Generation uses a deterministic extractive mock that does not interpret the existing A/B/C prompts.
- Retrieval uses deterministic-tfidf-hash-v1 embeddings; production text-embedding-3-small performance is unverified.
- Automated exact-span and lexical checks do not establish semantic faithfulness or policy correctness.
