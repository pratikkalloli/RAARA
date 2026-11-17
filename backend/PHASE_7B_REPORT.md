# RAARA Phase 7B — Retrieval Evaluation and Benchmarking

## Outcome

Phase 7B retrieval benchmarking completed using the existing development evaluation data. The benchmark is a limited baseline, not a measure of university-wide policy retrieval performance.

## Dataset, corpus, and mapping

- Dataset version `0.1.0`: 12 synthetic development questions across six categories.
- Two synthetic PDF fixtures were indexed; every PDF is labelled as a synthetic test document, not official policy.
- All 15 ground-truth evidence spans mapped exactly once to chunks using exact document ID, page number, and section matching. A chunk counts as relevant only when it contains the full normalized evidence span; partial overlap does not count.
- The benchmark indexed 12 chunks.

## Retrieval configuration and isolation

Evaluation indexing and queries used a temporary isolated ChromaDB directory and a dedicated evaluation collection. No production SQLite or ChromaDB writes occurred. Production retrieval behavior and settings were unchanged: cosine distance, threshold 0.35, 700-token chunks, 100-token overlap, and the existing retrieval pipeline. Results were measured for K=1, 3, and 5, with three repetitions for each question/K pair.

The offline embedding substitute was `deterministic-tfidf-hash-v1`. It is not equivalent to the configured production embedding model, `text-embedding-3-small`; production embedding performance remains unverified. No live OpenAI calls were made.

## Results

| K | Precision@K | Recall@K | MRR | Hit rate | Mean latency |
|---:|---:|---:|---:|---:|---:|
| 1 | 0.100 | 0.100 | 0.100 | 0.100 | 28.969 ms |
| 3 | 0.033 | 0.100 | 0.100 | 0.100 | 29.645 ms |
| 5 | 0.020 | 0.100 | 0.100 | 0.100 | 29.687 ms |

Only 1 of the 10 answerable questions retrieved relevant evidence. These weak results are limited by the small synthetic corpus and the offline embedding substitute. They do not establish production embedding or real-policy retrieval performance. The two unanswerable questions had no threshold-passing retrievals; that is a retrieval observation, not an answer-generation abstention score.

The machine-readable per-question, category, metric, and latency details are in [retrieval_benchmark.json](evaluation/results/retrieval_benchmark.json); the summary is in [retrieval_benchmark.md](evaluation/results/retrieval_benchmark.md). Each K had 36 latency samples. Timing includes query embedding and vector retrieval; the JSON also records component timings. PDF extraction, chunking, indexing, and generation are excluded.

## Verification

- Dataset validation: passed, 12 questions.
- Evaluation tests: passed.
- Full backend suite: **135 passed**.
- Evaluation indexing repeatability and temporary-store isolation were tested.
- No live OpenAI calls were made; no production SQLite or ChromaDB writes occurred.

## Limitations

The dataset is synthetic, small, and development-only. The lexical embedding substitute is not semantically equivalent to `text-embedding-3-small`. The benchmark does not assess semantic answer faithfulness, generation quality, or real-policy performance. The held-out set remains unpopulated. Phase 7C has not been started.

## PowerShell verification commands

Run from `C:\prompt_mini_proj\backend`:

```powershell
.\.venv311\Scripts\python.exe -m evaluation.scripts.validate_dataset --dataset evaluation\datasets\development\raara_synthetic_starter_v0.1.0.jsonl --manifest evaluation\datasets\development\manifest.json
.\.venv311\Scripts\python.exe -m pytest -v evaluation\tests
.\.venv311\Scripts\python.exe -m evaluation.scripts.run_retrieval_benchmark --repetitions 3
```

For the full backend suite, configure temporary `DATABASE_URL`, `CHROMA_PERSIST_DIR`, and `UPLOAD_DIR` paths before running `.\.venv311\Scripts\python.exe -m pytest -v`.
