# RAARA Phase 7C Answer Quality and Citation Evaluation

- Dataset: `0.1.0` (12 synthetic development questions)
- Embedding used: `deterministic-tfidf-hash-v1` (offline substitute)
- Generation used: `deterministic-extractive-mock-v1` (deterministic mock/extractive adapter)
- No live OpenAI calls; production SQLite/Chroma untouched.

Controlled evidence and end-to-end RAG are separate experiments. Metrics below are not combined.

## CONTROLLED_EVIDENCE

| Metric | Answerable | Unanswerable | Denominator note |
|---|---:|---:|---|
| normalized_exact_match | 0.000 | N/A | counts in JSON |
| key_fact_coverage | 0.617 | N/A | counts in JSON |
| claim_support_rate | 0.950 | N/A | counts in JSON |
| claim_contradiction_rate | 0.050 | N/A | counts in JSON |
| claim_not_enough_evidence_rate | 0.000 | N/A | counts in JSON |
| reference_correct_claim_rate | 1.000 | N/A | counts in JSON |
| reference_claim_contradiction_rate | 0.000 | N/A | counts in JSON |
| reference_claim_not_evaluated_rate | 0.250 | N/A | counts in JSON |
| answer_relevance | 0.667 | N/A | counts in JSON |
| off_topic_rate | 0.000 | N/A | counts in JSON |
| citation_precision | 1.000 | N/A | counts in JSON |
| citation_claim_support_precision | 1.000 | N/A | counts in JSON |
| citation_recall | 1.000 | N/A | counts in JSON |
| document_accuracy | 1.000 | N/A | counts in JSON |
| page_accuracy | 1.000 | N/A | counts in JSON |
| structural_validity_rate | 1.000 | N/A | counts in JSON |
| correct_abstention_rate | N/A | 1.000 | counts in JSON |
| false_answer_rate | N/A | 0.000 | counts in JSON |
| fabricated_citation_rate | N/A | 0.000 | counts in JSON |
| unsupported_claim_rate | 0.050 | N/A | counts in JSON |

Per-category and per-question details are recorded in JSON. These deterministic heuristics do not establish semantic faithfulness.

## END_TO_END_RAG

| Metric | Answerable | Unanswerable | Denominator note |
|---|---:|---:|---|
| normalized_exact_match | 0.000 | N/A | counts in JSON |
| key_fact_coverage | 0.100 | N/A | counts in JSON |
| claim_support_rate | 1.000 | N/A | counts in JSON |
| claim_contradiction_rate | 0.000 | N/A | counts in JSON |
| claim_not_enough_evidence_rate | 0.000 | N/A | counts in JSON |
| reference_correct_claim_rate | 1.000 | N/A | counts in JSON |
| reference_claim_contradiction_rate | 0.000 | N/A | counts in JSON |
| reference_claim_not_evaluated_rate | 0.000 | N/A | counts in JSON |
| answer_relevance | 0.100 | N/A | counts in JSON |
| off_topic_rate | 0.000 | N/A | counts in JSON |
| citation_precision | 0.100 | N/A | counts in JSON |
| citation_claim_support_precision | 1.000 | N/A | counts in JSON |
| citation_recall | 0.100 | N/A | counts in JSON |
| document_accuracy | 0.100 | N/A | counts in JSON |
| page_accuracy | 0.100 | N/A | counts in JSON |
| structural_validity_rate | 1.000 | N/A | counts in JSON |
| correct_abstention_rate | N/A | 1.000 | counts in JSON |
| false_answer_rate | N/A | 0.000 | counts in JSON |
| fabricated_citation_rate | N/A | 0.000 | counts in JSON |
| unsupported_claim_rate | 0.000 | N/A | counts in JSON |

Per-category and per-question details are recorded in JSON. These deterministic heuristics do not establish semantic faithfulness.

## Limitations
- All 12 items and both PDFs are synthetic development fixtures, not official policy.
- The offline embedding substitute is not text-embedding-3-small; real production embedding performance is unverified.
- The mock generator is not the configured OpenAI generator; production generation quality is untested.
- Claim support and correctness use explicit lexical heuristics and are not semantic entailment judgments.
- No human evaluator or LLM-as-judge was used; semantic correctness and faithfulness remain unverified.
- The dataset is small and has no populated held-out split.
