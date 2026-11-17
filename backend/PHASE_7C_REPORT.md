# RAARA Phase 7C — Answer Quality, Faithfulness and Citation Evaluation

## Summary and scope

Phase 7C adds an offline answer/citation evaluation framework. The two experiments remain separate: **CONTROLLED_EVIDENCE** evaluates the extractive adapter with gold-aligned evidence supplied directly, while **END_TO_END_RAG** uses the production Retriever against an isolated evaluation Chroma collection. No combined score is calculated.

All 12 questions and two PDFs are synthetic development fixtures, not official university regulations. No live OpenAI calls were made. The generator is `deterministic-extractive-mock-v1`, not the configured production generator; the embedding is `deterministic-tfidf-hash-v1`, not `text-embedding-3-small`. Production embedding and generation performance remain unverified.

## Methodology

### CONTROLLED_EVIDENCE

For each answerable question, the runner maps its exact labelled evidence span(s) to chunk(s) using document ID, page, and section, then supplies only those chunks to the injected generator adapter. Retrieval is intentionally bypassed. For unanswerable questions, it supplies no evidence. This experiment measures answer/evaluator behavior under an evidence-controlled condition; it does not measure retrieval quality.

### END_TO_END_RAG

The runner extracts and chunks the Phase 7A PDFs with the existing production processor and chunker, indexes them into a temporary Chroma directory, and calls the existing production `Retriever` once per question. It passes those actual retrieved passages to the same injected adapter. The existing citation verifier validates the returned `StructuredAnswer` against that retrieval context. The production settings remain unchanged: cosine distance, configured relevance threshold 0.35, top-K 5, 700-token chunk size, and 100-token overlap.

Both experiments use the same deterministic extractive mock adapter implementing the existing `generate_with_usage` interface. It selects sentence(s) from supplied evidence and returns the existing `StructuredAnswer`/`GenerationRecord` schema. No production prompt or generator was changed or invoked; the default Prompt C enum is only an interface marker. The adapter has no API client or credentials.

### Deterministic metrics and interpretation

- Normalized exact answer match uses the existing Unicode/case/punctuation normalization; it is lexical, not semantic.
- Key-fact coverage requires all normalized content terms and values from an expected fact to appear in the generated response. Per-question expected, matched, missing, and incorrect claims are preserved.
- Claim support is checked against retrieved passages using exact normalized containment or content-token containment. Conflicting numeric/date values with overlapping subject terms are marked `CONTRADICTED`; otherwise unmatched claims are `NOT_ENOUGH_EVIDENCE`. Reference-corpus claim classification is stored separately as `SUPPORTED`, `CONTRADICTED`, or `NOT_EVALUATED`.
- These rules are deterministic lexical heuristics, not entailment or semantic faithfulness judgments. Citation structural validity does not prove that a citation semantically supports a claim.
- Citation precision includes only structurally valid citations matching gold passage IDs divided by unique generated citation IDs. Citation recall uses valid cited passage IDs against gold passage IDs and is undefined for unanswerable questions. Citation-to-claim support precision is reported separately.
- Document identification compares the cited document ID set to the gold set. Page accuracy compares document/page pairs. Structural validity is independently checked using the production `CitationVerifier`.
- Question relevance is significant question-content token coverage. Off-topic is a separate flag. Correct abstention is measured on the verifier-final response; false-answer rate measures the raw adapter response on unanswerable questions; fabricated citations are raw citations absent from retrieval context.
- Aggregate values are macro-averages across question-level values. JSON `count` is the number of question-level observations for that metric; claim metrics first average claims within each question. Undefined metrics remain `null` with count zero. There is no arbitrary overall score.

## Results

The tables show answerable and unanswerable questions separately. Each experiment has 10 answerable and 2 unanswerable questions. Claim-level denominator counts are recorded per metric in the JSON artifact.

### Answerable questions

| Metric | CONTROLLED_EVIDENCE (N) | END_TO_END_RAG (N) |
|---|---:|---:|
| Normalized exact match | 0.000 (10) | 0.000 (10) |
| Key-fact coverage | 0.617 (10) | 0.100 (10) |
| Claim support rate | 0.950 (10) | 1.000 (1) |
| Claim contradiction rate | 0.050 (10) | 0.000 (1) |
| Claim not-enough-evidence rate | 0.000 (10) | 0.000 (1) |
| Reference-corpus correct claim rate | 1.000 (8) | 1.000 (1) |
| Answer relevance, question-content coverage | 0.667 (10) | 0.100 (10) |
| Off-topic rate | 0.000 (10) | 0.000 (10) |
| Citation precision | 1.000 (10) | 0.100 (10) |
| Citation-to-claim support precision | 1.000 (10) | 1.000 (1) |
| Citation recall | 1.000 (10) | 0.100 (10) |
| Document identification accuracy | 1.000 (10) | 0.100 (10) |
| Page accuracy | 1.000 (10) | 0.100 (10) |
| Citation structural validity | 1.000 (10) | 1.000 (1) |
| Unsupported-claim rate | 0.050 (10) | 0.000 (1) |

### Unanswerable questions

| Metric | CONTROLLED_EVIDENCE (N=2) | END_TO_END_RAG (N=2) |
|---|---:|---:|
| Correct abstention rate | 1.000 | 1.000 |
| False-answer rate | 0.000 | 0.000 |
| Fabricated-citation rate | 0.000 | 0.000 |
| Citation recall | N/A | N/A |
| Unsupported-claim rate | N/A (no claims to score) | N/A (no claims to score) |

### Per-category key-fact coverage

| Category | Questions | CONTROLLED_EVIDENCE | END_TO_END_RAG |
|---|---:|---:|---:|
| direct_factual | 3 | 1.000 | 0.333 |
| multi_passage | 2 | 0.750 | 0.000 |
| multi_document | 1 | 0.000 | 0.000 |
| conflicting_version | 2 | 0.583 | 0.000 |
| prompt_injection | 2 | 0.250 | 0.000 |
| unanswerable | 2 | N/A | N/A |

The low end-to-end key-fact, citation, document, and page results are consistent with Phase 7B's weak retrieval baseline (only one of ten answerable questions retrieved relevant evidence). The controlled run isolates the adapter/evaluator from retrieval, but its outputs still come from a simple lexical mock. These figures do not show that an OpenAI model would behave similarly.

Per-question raw and verifier-final answers, retrieved passages, claims and classifications, citations, verification issues, category aggregates, denominators, and configuration are in [answer_quality_benchmark.json](evaluation/results/answer_quality_benchmark.json) and [answer_quality_benchmark.md](evaluation/results/answer_quality_benchmark.md).

## Evaluator validation and tests

Tests cover normalization and key facts, correct/wrong-page/missing/fabricated citations, citation validity versus claim support, incorrect numeric claims, unsupported claims, partial multi-part answers, unanswerable abstention/false answers, undefined metrics, and separate controlled/end-to-end result groups. **13 Phase 7C evaluator tests passed.** Combined evaluation tests: **43 passed**. The Phase 7A validator passed with **12 questions validated**. The full backend suite passed: **148 passed, 0 failed**, Python 3.11.9, using isolated temporary SQLite, ChromaDB, and upload paths. No live API calls were used.

## Files created and modified

Created:

- `backend/evaluation/answer_quality/__init__.py`
- `backend/evaluation/answer_quality/adapters.py`
- `backend/evaluation/answer_quality/evaluator.py`
- `backend/evaluation/answer_quality/runner.py`
- `backend/evaluation/scripts/run_answer_quality_benchmark.py`
- `backend/evaluation/tests/test_answer_quality.py`
- `backend/evaluation/results/answer_quality_benchmark.json`
- `backend/evaluation/results/answer_quality_benchmark.md`
- `backend/PHASE_7C_REPORT.md`

Modified: `backend/evaluation/README.md`.

No production application source, frontend, Phase 7A dataset, Phase 7B result, held-out dataset, production SQLite, or production ChromaDB data was modified.

## Limitations and next steps

There was no human assessment or LLM-as-judge. Semantic correctness, semantic faithfulness, production prompt behavior, production generation quality, and real OpenAI embedding performance remain unverified. The mock's lexical extraction and the evaluator's token rules can miss paraphrases, over-credit literal overlap, or mishandle injected text. The corpus is synthetic, small, and development-only; it has no populated held-out split. Results should be treated as evaluator-pipeline diagnostics only. Phase 7D has not been started.

## PowerShell verification

Run from `C:\prompt_mini_proj\backend`:

```powershell
.\.venv311\Scripts\python.exe -m evaluation.scripts.validate_dataset --dataset evaluation\datasets\development\raara_synthetic_starter_v0.1.0.jsonl --manifest evaluation\datasets\development\manifest.json
.\.venv311\Scripts\python.exe -m pytest -v evaluation\tests
.\.venv311\Scripts\python.exe -m evaluation.scripts.run_answer_quality_benchmark
```

For the full backend suite, set `DATABASE_URL`, `CHROMA_PERSIST_DIR`, and `UPLOAD_DIR` to temporary paths, then run `.\.venv311\Scripts\python.exe -m pytest -v`.
