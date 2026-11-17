# RAARA Phase 7B Retrieval Benchmark

- Dataset: `0.1.0` (12 questions)
- Embedding used: `deterministic-tfidf-hash-v1` (offline lexical substitute)
- Chunks indexed: 12 (12 added, 0 reused)
- Threshold: 0.35; cosine distance metric

| K | Precision | Recall | MRR | Hit rate | Document hit | Page hit |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.100 | 0.100 | 0.100 | 0.100 | 0.100 | 0.100 |
| 3 | 0.033 | 0.100 | 0.100 | 0.100 | 0.100 | 0.100 |
| 5 | 0.020 | 0.100 | 0.100 | 0.100 | 0.100 | 0.100 |

## Latency by K

| K | Samples | Mean ms | Median ms | P95 ms |
|---:|---:|---:|---:|---:|
| 1 | 36 | 28.969 | 24.192 | 70.3304 |
| 3 | 36 | 29.645 | 25.572 | 61.673 |
| 5 | 36 | 29.686 | 24.672 | 68.0526 |

Average retrieved count and empty retrieval rate are also included in JSON per K and category.

## Limitations
- Synthetic development corpus only; not real academic policy.
- Deterministic lexical hashing substitute was used; scores do not measure OpenAI embedding performance.
- Unanswerable detection here means no results passed the production threshold; it does not measure answer abstention.
- Scores measure retrieval matching only, not semantic answer correctness or faithfulness.
