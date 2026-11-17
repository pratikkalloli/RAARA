# RAARA Phase 7D A/B/C Prompt Comparison

**SIMULATED_PROMPT_DIAGNOSTICS** — the deterministic mock does not interpret prompt text. These results are not real LLM prompt-performance measurements.

- Dataset: `0.1.0` (12 synthetic questions)
- Model used: `deterministic-extractive-mock-v1`; production chat model configured: `gpt-4.1-mini` (not called)
- Embedding: `deterministic-tfidf-hash-v1`; no live OpenAI calls.
- Prompt hashes and per-question details are in the JSON artifact.

A/B/C receive the same retrieval object, evidence metadata, model adapter, generation settings, and StructuredAnswer schema for each question. End-to-end retrieval is run once per question and reused across the three prompts.

## CONTROLLED_EVIDENCE

| Metric | A | B | C |
|---|---:|---:|---:|
| normalized_exact_match | 0.000 (n=10) | 0.000 (n=10) | 0.000 (n=10) |
| key_fact_coverage | 0.617 (n=10) | 0.617 (n=10) | 0.617 (n=10) |
| claim_support_rate | 0.950 (n=10) | 0.950 (n=10) | 0.950 (n=10) |
| claim_contradiction_rate | 0.050 (n=10) | 0.050 (n=10) | 0.050 (n=10) |
| answer_relevance | 0.667 (n=10) | 0.667 (n=10) | 0.667 (n=10) |
| citation_precision | 1.000 (n=10) | 1.000 (n=10) | 1.000 (n=10) |
| citation_recall | 1.000 (n=10) | 1.000 (n=10) | 1.000 (n=10) |
| document_accuracy | 1.000 (n=10) | 1.000 (n=10) | 1.000 (n=10) |
| page_accuracy | 1.000 (n=10) | 1.000 (n=10) | 1.000 (n=10) |
| correct_abstention_rate | N/A | N/A | N/A |
| false_answer_rate | N/A | N/A | N/A |
| fabricated_citation_rate | N/A | N/A | N/A |

### Unanswerable questions

| Metric | A | B | C |
|---|---:|---:|---:|
| correct_abstention_rate | 1.000 (n=2) | 1.000 (n=2) | 1.000 (n=2) |
| false_answer_rate | 0.000 (n=2) | 0.000 (n=2) | 0.000 (n=2) |
| fabricated_citation_rate | 0.000 (n=2) | 0.000 (n=2) | 0.000 (n=2) |

### Key-fact coverage by category

| Category | A | B | C |
|---|---:|---:|---:|
| conflicting_version | 0.583 (n=2) | 0.583 (n=2) | 0.583 (n=2) |
| direct_factual | 1.000 (n=3) | 1.000 (n=3) | 1.000 (n=3) |
| multi_document | 0.000 (n=1) | 0.000 (n=1) | 0.000 (n=1) |
| multi_passage | 0.750 (n=2) | 0.750 (n=2) | 0.750 (n=2) |
| prompt_injection | 0.250 (n=2) | 0.250 (n=2) | 0.250 (n=2) |
| unanswerable | N/A | N/A | N/A |

| Prompt | Input tokens | Output tokens | Total tokens | Mean adapter latency ms | Estimated cost USD |
|---|---:|---:|---:|---:|---:|
| A | N/A | N/A | N/A | 17.629267 | N/A |
| B | N/A | N/A | N/A | 14.490917 | N/A |
| C | N/A | N/A | N/A | 17.151933 | N/A |

## END_TO_END_RAG

| Metric | A | B | C |
|---|---:|---:|---:|
| normalized_exact_match | 0.000 (n=10) | 0.000 (n=10) | 0.000 (n=10) |
| key_fact_coverage | 0.100 (n=10) | 0.100 (n=10) | 0.100 (n=10) |
| claim_support_rate | 1.000 (n=1) | 1.000 (n=1) | 1.000 (n=1) |
| claim_contradiction_rate | 0.000 (n=1) | 0.000 (n=1) | 0.000 (n=1) |
| answer_relevance | 0.100 (n=10) | 0.100 (n=10) | 0.100 (n=10) |
| citation_precision | 0.100 (n=10) | 0.100 (n=10) | 0.100 (n=10) |
| citation_recall | 0.100 (n=10) | 0.100 (n=10) | 0.100 (n=10) |
| document_accuracy | 0.100 (n=10) | 0.100 (n=10) | 0.100 (n=10) |
| page_accuracy | 0.100 (n=10) | 0.100 (n=10) | 0.100 (n=10) |
| correct_abstention_rate | N/A | N/A | N/A |
| false_answer_rate | N/A | N/A | N/A |
| fabricated_citation_rate | N/A | N/A | N/A |

### Unanswerable questions

| Metric | A | B | C |
|---|---:|---:|---:|
| correct_abstention_rate | 1.000 (n=2) | 1.000 (n=2) | 1.000 (n=2) |
| false_answer_rate | 0.000 (n=2) | 0.000 (n=2) | 0.000 (n=2) |
| fabricated_citation_rate | 0.000 (n=2) | 0.000 (n=2) | 0.000 (n=2) |

### Key-fact coverage by category

| Category | A | B | C |
|---|---:|---:|---:|
| conflicting_version | 0.000 (n=2) | 0.000 (n=2) | 0.000 (n=2) |
| direct_factual | 0.333 (n=3) | 0.333 (n=3) | 0.333 (n=3) |
| multi_document | 0.000 (n=1) | 0.000 (n=1) | 0.000 (n=1) |
| multi_passage | 0.000 (n=2) | 0.000 (n=2) | 0.000 (n=2) |
| prompt_injection | 0.000 (n=2) | 0.000 (n=2) | 0.000 (n=2) |
| unanswerable | N/A | N/A | N/A |

| Prompt | Input tokens | Output tokens | Total tokens | Mean adapter latency ms | Estimated cost USD |
|---|---:|---:|---:|---:|---:|
| A | N/A | N/A | N/A | 14.059758 | N/A |
| B | N/A | N/A | N/A | 19.398817 | N/A |
| C | N/A | N/A | N/A | 18.708267 | N/A |

## Interpretation

The deterministic mock ignores natural-language prompt instructions and returns the same extractive output for A, B, and C. Metric equality is an adapter limitation, not evidence that the prompts are equivalent for a real language model.

The prompts tie on the deterministic mock. This cannot show whether structured prompting improves evidence discipline with a real model. There is no statistically supported winner.

## Limitations
- The 12-question corpus and PDFs are synthetic development data, not official regulations.
- No live OpenAI generation was run; credentials and live service behavior were not exercised.
- The deterministic mock does not process prompt text, so A/B/C output equality is expected and cannot establish model prompt effects.
- The local embedding substitute is not text-embedding-3-small; production embedding performance is unverified.
- Token usage is unavailable for the mock and remains null; no pricing snapshot is configured, so estimated API cost remains null.
- Measured generation latency is local adapter execution time and is not representative of model latency.
- No held-out dataset or statistical significance analysis is available.
