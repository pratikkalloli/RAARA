# `cl100k_base` dependency diagnosis and offline recovery

## Diagnosis

- Environment: Python 3.11.9, backend `.venv311`, `tiktoken` **0.14.0**.
- Production tokenization: `app/services/chunker.py` constructs `tiktoken.get_encoding("cl100k_base")`; chunk sizes/overlap are unchanged.
- `tiktoken` does not bundle the mergeable-ranks data file with its Python package. On first use, it reads a cache entry or fetches its configured public data URL.
- Required resource URL: `https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken`.
- Expected SHA-256, pinned by installed `tiktoken_ext/openai_public.py`: `223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7`.
- Cache key used by `tiktoken`: `9b5ad71b2ce5302211f9c61530b329a4922fc6a4` (SHA-1 of the URL; the cache filename has no extension).
- Before recovery, `TIKTOKEN_CACHE_DIR` and `DATA_GYM_CACHE_DIR` were unset, the default `%TEMP%\data-gym-cache` directory had no resource, and `pip cache list tiktoken` had no local package/resource available. Network name resolution to the configured host failed.
- Evaluation tests directly needing `cl100k_base`: `test_benchmark_runner_keeps_experiment_results_separate`, `test_runner_separates_experiments_and_reuses_one_retrieval`, `test_evaluation_indexing_is_repeatable_and_isolated`, and `test_dataset_exact_evidence_span_mapping_audit`. Backend chunker, ingestion, and document-verification tests also use the same encoding.
- No replacement tokenizer was introduced, and chunking parameters were not changed.

## Recovered cache

The exact upstream resource was fetched through the approved reviewer path into the temporary cache directory:

`%TEMP%\raara-phase8d-tiktoken-cache\9b5ad71b2ce5302211f9c61530b329a4922fc6a4`

Its SHA-256 matched the pinned value above. `tiktoken.get_encoding("cl100k_base")` then loaded from that cache offline. This is tokenizer vocabulary data, not an OpenAI inference/API call; no credential was used.

## Reproducible offline recovery

On a machine that already has the verified cache file, set the cache directory before running tests:

```powershell
$env:TIKTOKEN_CACHE_DIR = Join-Path $env:TEMP 'raara-phase8d-tiktoken-cache'
$cacheFile = Join-Path $env:TIKTOKEN_CACHE_DIR '9b5ad71b2ce5302211f9c61530b329a4922fc6a4'
if ((Get-FileHash -LiteralPath $cacheFile -Algorithm SHA256).Hash.ToLowerInvariant() -ne '223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7') { throw 'Tokenizer resource checksum mismatch' }
.\.venv311\Scripts\python.exe -c "import tiktoken; print(tiktoken.get_encoding('cl100k_base').name)"
.\.venv311\Scripts\python.exe -m pytest -v
```

For a fully offline machine without the file, transfer the binary from an approved connected environment using removable media or an approved internal artifact store. Save it under the cache filename above, verify the SHA-256 before use, then set `TIKTOKEN_CACHE_DIR`. Do not rename a different encoding's data to this cache key. If downloading directly is permitted by local policy, use only the URL above and require the exact SHA before testing. Installing/upgrading the `tiktoken` wheel alone does not provide this data file.

## Full-suite environment notes

The complete backend test run also requires local FastAPI test sockets in this Windows sandbox. Run it through the standard approved execution mechanism when local socket access is restricted. The tested SQLite, ChromaDB, and upload paths must point to a unique temporary directory; keep `OPENAI_API_KEY` empty so tests cannot make live model calls.
