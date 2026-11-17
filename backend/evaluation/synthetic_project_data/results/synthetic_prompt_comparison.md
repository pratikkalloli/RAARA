# RAARA Phase 7D A/B/C Prompt Comparison

**SIMULATED_PROMPT_DIAGNOSTICS** — the deterministic mock does not interpret prompt text. These results are not real LLM prompt-performance measurements.

- Dataset: `9A.1.0` (36 synthetic questions)
- Model used: `deterministic-extractive-mock-v1`; production chat model configured: `gpt-4.1-mini` (not called)
- Embedding: `deterministic-tfidf-hash-v1`; no live OpenAI calls.
- Prompt hashes and per-question details are in the JSON artifact.

A/B/C receive the same retrieval object, evidence metadata, model adapter, generation settings, and StructuredAnswer schema for each question. End-to-end retrieval is run once per question and reused across the three prompts.

## CONTROLLED_EVIDENCE

| Metric | A | B | C |
|---|---:|---:|---:|
| normalized_exact_match | 0.000 (n=35) | 0.000 (n=35) | 0.000 (n=35) |
| key_fact_coverage | 0.257 (n=35) | 0.257 (n=35) | 0.257 (n=35) |
| claim_support_rate | 0.138 (n=35) | 0.138 (n=35) | 0.138 (n=35) |
| claim_contradiction_rate | 0.057 (n=35) | 0.057 (n=35) | 0.057 (n=35) |
| answer_relevance | 0.699 (n=35) | 0.699 (n=35) | 0.699 (n=35) |
| citation_precision | 1.000 (n=35) | 1.000 (n=35) | 1.000 (n=35) |
| citation_recall | 1.000 (n=35) | 1.000 (n=35) | 1.000 (n=35) |
| document_accuracy | 1.000 (n=35) | 1.000 (n=35) | 1.000 (n=35) |
| page_accuracy | 1.000 (n=35) | 1.000 (n=35) | 1.000 (n=35) |
| correct_abstention_rate | N/A | N/A | N/A |
| false_answer_rate | N/A | N/A | N/A |
| fabricated_citation_rate | N/A | N/A | N/A |

### Unanswerable questions

| Metric | A | B | C |
|---|---:|---:|---:|
| correct_abstention_rate | 1.000 (n=1) | 1.000 (n=1) | 1.000 (n=1) |
| false_answer_rate | 0.000 (n=1) | 0.000 (n=1) | 0.000 (n=1) |
| fabricated_citation_rate | 0.000 (n=1) | 0.000 (n=1) | 0.000 (n=1) |

### Key-fact coverage by category

| Category | A | B | C |
|---|---:|---:|---:|
| assessment_calculation | 0.600 (n=5) | 0.600 (n=5) | 0.600 (n=5) |
| attendance_eligibility | 0.400 (n=5) | 0.400 (n=5) | 0.400 (n=5) |
| backlogs_supplementary | 0.500 (n=4) | 0.500 (n=4) | 0.500 (n=4) |
| direct_factual | 0.143 (n=7) | 0.143 (n=7) | 0.143 (n=7) |
| grading_sgpa_cgpa | 0.000 (n=4) | 0.000 (n=4) | 0.000 (n=4) |
| lateral_entry_progression | 0.250 (n=4) | 0.250 (n=4) | 0.250 (n=4) |
| multi_document | 0.000 (n=2) | 0.000 (n=2) | 0.000 (n=2) |
| multi_passage | 0.000 (n=3) | 0.000 (n=3) | 0.000 (n=3) |
| prompt_injection | 0.000 (n=1) | 0.000 (n=1) | 0.000 (n=1) |
| unanswerable | N/A | N/A | N/A |

| Prompt | Input tokens | Output tokens | Total tokens | Mean adapter latency ms | Estimated cost USD |
|---|---:|---:|---:|---:|---:|
| A | N/A | N/A | N/A | 9.727189 | N/A |
| B | N/A | N/A | N/A | 9.919389 | N/A |
| C | N/A | N/A | N/A | 10.020686 | N/A |

## END_TO_END_RAG

| Metric | A | B | C |
|---|---:|---:|---:|
| normalized_exact_match | 0.000 (n=35) | 0.000 (n=35) | 0.000 (n=35) |
| key_fact_coverage | 0.057 (n=35) | 0.057 (n=35) | 0.057 (n=35) |
| claim_support_rate | 0.100 (n=5) | 0.100 (n=5) | 0.100 (n=5) |
| claim_contradiction_rate | 0.000 (n=5) | 0.000 (n=5) | 0.000 (n=5) |
| answer_relevance | 0.133 (n=35) | 0.133 (n=35) | 0.133 (n=35) |
| citation_precision | 0.143 (n=35) | 0.143 (n=35) | 0.143 (n=35) |
| citation_recall | 0.129 (n=35) | 0.129 (n=35) | 0.129 (n=35) |
| document_accuracy | 0.143 (n=35) | 0.143 (n=35) | 0.143 (n=35) |
| page_accuracy | 0.143 (n=35) | 0.143 (n=35) | 0.143 (n=35) |
| correct_abstention_rate | N/A | N/A | N/A |
| false_answer_rate | N/A | N/A | N/A |
| fabricated_citation_rate | N/A | N/A | N/A |

### Unanswerable questions

| Metric | A | B | C |
|---|---:|---:|---:|
| correct_abstention_rate | 1.000 (n=1) | 1.000 (n=1) | 1.000 (n=1) |
| false_answer_rate | 0.000 (n=1) | 0.000 (n=1) | 0.000 (n=1) |
| fabricated_citation_rate | 0.000 (n=1) | 0.000 (n=1) | 0.000 (n=1) |

### Key-fact coverage by category

| Category | A | B | C |
|---|---:|---:|---:|
| assessment_calculation | 0.200 (n=5) | 0.200 (n=5) | 0.200 (n=5) |
| attendance_eligibility | 0.000 (n=5) | 0.000 (n=5) | 0.000 (n=5) |
| backlogs_supplementary | 0.000 (n=4) | 0.000 (n=4) | 0.000 (n=4) |
| direct_factual | 0.000 (n=7) | 0.000 (n=7) | 0.000 (n=7) |
| grading_sgpa_cgpa | 0.000 (n=4) | 0.000 (n=4) | 0.000 (n=4) |
| lateral_entry_progression | 0.250 (n=4) | 0.250 (n=4) | 0.250 (n=4) |
| multi_document | 0.000 (n=2) | 0.000 (n=2) | 0.000 (n=2) |
| multi_passage | 0.000 (n=3) | 0.000 (n=3) | 0.000 (n=3) |
| prompt_injection | 0.000 (n=1) | 0.000 (n=1) | 0.000 (n=1) |
| unanswerable | N/A | N/A | N/A |

| Prompt | Input tokens | Output tokens | Total tokens | Mean adapter latency ms | Estimated cost USD |
|---|---:|---:|---:|---:|---:|
| A | N/A | N/A | N/A | 9.529406 | N/A |
| B | N/A | N/A | N/A | 9.509964 | N/A |
| C | N/A | N/A | N/A | 9.282339 | N/A |

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
