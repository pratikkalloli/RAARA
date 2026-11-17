# RAARA offline evaluation foundation (Phase 7A)

This package holds offline benchmark data, validation, and metric functions. It is deliberately separate from `app/services`, production SQLite, and the configured ChromaDB collection. Importing `evaluation` does not initialize the FastAPI app or connect to production storage.

## Layout

```text
backend/evaluation/
  README.md
  evaluation_config.json
  datasets/
    development/
      manifest.json
      raara_synthetic_starter_v0.1.0.jsonl
      sources/                         # labelled PDFs, not production uploads
    held_out/README.md                 # no held-out labels yet
  schemas/dataset.py                   # Pydantic schema and validator
  metrics/
    retrieval.py
    citations.py
    answer.py
    performance.py
  answer_quality/                    # Phase 7C deterministic evaluator and offline adapter
  prompt_experiments/                # Phase 7D simulated A/B/C comparison harness
  results/README.md                    # no scores generated in Phase 7A
  scripts/
    build_synthetic_sources.py
    validate_dataset.py
    run_retrieval_benchmark.py
    run_answer_quality_benchmark.py
    run_prompt_comparison.py
  tests/
```

The existing A/B/C prompt experiment runner remains under `app/evaluation/experiments.py`. The new `evaluation/` directory does not change its behavior or run it automatically.

## Dataset status and source material

At project inspection, `documents/` and `documentation/` contained no permitted academic policy sources, and the existing `evaluation_dataset/` folder had no files. The Phase 7A set is therefore a small **synthetic development starter**, not a real-policy benchmark and not the suggested 50-question target.

Dataset version `0.1.0` contains 12 questions:

| Category | Count |
|---|---:|
| `direct_factual` | 3 |
| `multi_passage` | 2 |
| `multi_document` | 1 |
| `unanswerable` | 2 |
| `conflicting_version` | 2 |
| `prompt_injection` | 2 |

The two generated PDF sources are labelled on every page **SYNTHETIC TEST DOCUMENT — NOT OFFICIAL UNIVERSITY POLICY**. They contain fictional dates, percentages, sample tokens, version differences, and explicit untrusted injection strings. The dataset uses stable corpus IDs such as `SYNTH-ACADEMIC-GUIDE-V1`; they are not production SQLite document IDs. Production Chroma IDs currently use `doc-<database-document-id>-chunk-<chunk-index>`, while evaluation evidence IDs are stable labels such as `V1-P1-DEADLINE`. This separation avoids assuming that evaluation fixtures have production database IDs.

`manifest.json` records each source ID, filename, version, effective date, page count, source type, synthetic/official flags, and SHA-256. Each JSONL question uses these fields:

- `question_id`, `question`, `category`, `expected_status`
- `reference_answer` (required for answerable examples; null for `NOT_FOUND`)
- `relevant_document_ids`, `relevant_pages`, `relevant_evidence`
- `expected_claims`, `evaluation_notes`
- `dataset_version`, `source_type`, and `attack_surface`

Page and evidence references identify a stable source ID, one-based page, section, and (for evidence) stable evidence label and exact text. One or multiple documents/passages are supported. Unanswerable examples intentionally have no gold documents, pages, passages, claims, or reference answer.

`schemas/dataset.py` is the authoritative typed schema. It rejects unknown fields, invalid category/status values, blank questions, duplicate IDs, version mismatches, missing answers for answerable items, invented answers/evidence on unanswerable items, bad document/page references, and evidence text absent from the referenced synthetic PDF page. The manifest checksum is checked before page validation.

## Build and validate

Run from `backend` in `.venv311`:

```powershell
.\.venv311\Scripts\python.exe -m evaluation.scripts.build_synthetic_sources
.\.venv311\Scripts\python.exe -m evaluation.scripts.validate_dataset --dataset evaluation\datasets\development\raara_synthetic_starter_v0.1.0.jsonl --manifest evaluation\datasets\development\manifest.json
```

The source builder writes only beneath `evaluation/datasets/development/`. The validator is read-only. It prints question count and category distribution and exits nonzero with line- or record-specific validation errors.

Run evaluation metric/schema tests:

```powershell
.\.venv311\Scripts\python.exe -m pytest -v evaluation\tests
```

Dataset/schema and metric tests make no API calls. Phase 7B retrieval tests use deterministic local embeddings and temporary Chroma storage; they do not use production databases, production Chroma data, credentials, or generation.

## Metric definitions

All retrieval metric inputs must use the same identifier level: either stable evidence/passage IDs or document IDs. Do not mix the two. Retrieved IDs are deduplicated by exact identifier while preserving the first rank, so duplicate chunks do not improve rank or count twice.

The starter labels use stable corpus evidence IDs, while runtime Chroma IDs are generated from document/chunk identifiers. Phase 7B implements exact evidence-to-chunk alignment in `retrieval/ground_truth.py`: normalized full evidence text must occur in a chunk with the exact labelled document ID, one-based page number, and section. Partial text overlap does not count. If a complete span appears in more than one chunk, each matching chunk counts; the current 15 spans each map exactly once. Unanswerable questions map to an empty passage set. The mapping fails if an answerable span cannot be mapped.

- **Precision@K:** unique relevant IDs among the first K unique results divided by K. K remains the denominator even when fewer than K results are returned. Empty retrieval has value 0.
- **Recall@K:** unique relevant IDs among the first K unique results divided by the number of gold relevant IDs. It is 0 for a nonempty gold set with no retrieved match. It is `null`/`None` when the gold set is empty, as with an unanswerable question.
- **Reciprocal rank:** inverse rank of the first unique relevant result; 0 when a nonempty gold set has no hit. It is `None` for an empty gold set.
- **MRR:** arithmetic mean of reciprocal ranks across queries with at least one gold relevant ID. Unanswerable/empty-gold queries are excluded rather than counted as zero. MRR is unavailable (`None`) when no query has gold evidence.
- **Citation precision/recall:** same set definitions as evidence-level retrieval metrics, applied to unique cited evidence IDs. Citation recall is unavailable for no-gold-evidence questions.
- **Document identification accuracy:** exact set match between predicted and gold document IDs; empty/empty is correct for abstention.
- **Page accuracy:** fraction of unique predicted `(document_id, one_based_page_number)` pairs that match a gold pair. Empty/empty is correct abstention; empty prediction against nonempty gold is 0.
- **Normalized exact answer match:** binary equality after Unicode normalization, case folding, punctuation-to-space conversion, and whitespace collapse. This is lexical only; it does not credit paraphrase or prove correctness.

These citation measures evaluate structural reference matching only. A citation can point to a real retrieved passage and still fail to support a claim. `SemanticAssessment` is a storage interface for explicitly attributed human or future LLM-judge scores for claim correctness, faithfulness, and answer relevance. Phase 7A implements no judge and assigns no semantic scores. No hidden chain-of-thought is requested or stored.

Performance helpers preserve missing values as unavailable:

- Record retrieval, generation, and total latency in milliseconds. Total is `None` unless both phase times exist.
- Preserve input/output token counts as `None` if unavailable.
- Estimated API cost is `None` unless both token counts and an explicit input/output USD-per-million rate snapshot are supplied. The helper does not fetch changing prices and the development config intentionally contains no rate snapshot.

## Phase 7B retrieval benchmark

Run `python -m evaluation.scripts.run_retrieval_benchmark` from `backend`. The runner validates the JSONL dataset and manifest, extracts the two synthetic PDFs with the production PDF processor, chunks them with the production token chunker and metadata rules, and indexes stable `doc-<document_id>-chunk-<chunk_index>` IDs into a temporary Chroma directory and dedicated evaluation collection. The CLI does not use the configured production Chroma path. Repeated indexing reuses matching chunk IDs and fails if fixture text or metadata differs.

The benchmark uses the production `Retriever`, cosine distance, configured threshold, and existing preprocessing. It measures independent K=1, 3, and 5 retrievals with three repetitions, using an out-of-sample warm-up. The production settings remain unchanged: threshold 0.35, chunk size 700, overlap 100, and `1 - cosine_distance` similarity. Retrieval latency includes query embedding and vector lookup; each component is timed separately. Parsing, chunking, indexing, and answer generation are excluded. P95 is reported when the sample count supports it.

No OpenAI embedding call is made. The evaluation-only `deterministic-tfidf-hash-v1` lexical substitute is used for index and query vectors; it is not equivalent to production `text-embedding-3-small`. The configured production model is recorded separately. Generation is not run. Fixture documents remain unverified synthetic test documents.

Phase 7B results are in `results/retrieval_benchmark.json` and `results/retrieval_benchmark.md`; the acceptance summary is in `../PHASE_7B_REPORT.md`. The baseline is weak: only one of ten answerable questions retrieved relevant evidence. The small synthetic corpus and offline embedding substitute limit interpretation; production embedding performance remains unverified.

## Phase 7C answer and citation evaluation

Run `python -m evaluation.scripts.run_answer_quality_benchmark` from `backend` to generate separate `CONTROLLED_EVIDENCE` and `END_TO_END_RAG` results in `results/answer_quality_benchmark.json` and `.md`. The controlled experiment intentionally bypasses retrieval and supplies exact gold-aligned passages for answerable questions; unanswerable questions receive no context. The end-to-end experiment uses the production Retriever with the Phase 7B corpus in temporary Chroma storage. Both use an offline deterministic extractive adapter conforming to the existing generator interface. No live OpenAI generator call is made, and production prompts are not run or modified.

The evaluator reuses the application's `StructuredAnswer`, `CitationVerifier`, Phase 7A normalized-match/citation metrics, and Phase 7B ground-truth passage mapping. It distinguishes retrieved-context support from reference-corpus claim matching, structural citation validity from citation-to-claim lexical support, and relevance from faithfulness. Claim splitting and matching are deterministic lexical heuristics. No semantic correctness or faithfulness judgment is made; those fields remain unavailable. Outputs retain per-question claims, missing expected facts, citations, evidence IDs, verifier issues, metric counts, and experiment configuration. Controlled and end-to-end results are never combined into a single score.

See `../PHASE_7C_REPORT.md` for aggregate values, denominators, limitations, tests, and verification commands. Results apply only to the small synthetic development corpus; the local embedding substitute and mock generator do not establish production OpenAI performance.

## Phase 7D A/B/C prompt comparison

Run `python -m evaluation.scripts.run_prompt_comparison` from `backend`. It reads the unchanged A/B/C definitions from `app/prompting/system_prompt.py`, uses the same existing `build_user_prompt` context rendering and `StructuredAnswer` schema, and reports content-addressed hashes for system instructions, user template, output schema, and each combined prompt/context payload.

This run uses the Phase 7C deterministic extractive mock because no live generation was authorized. The mock accepts and records the prompt selector but does not interpret prompt text; therefore matching A/B/C outputs are expected simulated diagnostics, not evidence that the real prompts are equivalent or have equal performance. In CONTROLLED_EVIDENCE it supplies the same gold-aligned evidence to all three prompts. In END_TO_END_RAG it retrieves once per question from a temporary Chroma index and reuses that retrieval result for A/B/C. Retrieval configuration is unchanged. Token usage and estimated cost are null because mock usage and a pricing snapshot are unavailable; local adapter latency is not model latency.

The machine-readable and summary reports are `results/prompt_comparison.json` and `results/prompt_comparison.md`; the Phase 7D report is `../PHASE_7D_REPORT.md`. No overall winner or statistical significance claim is made from this synthetic 12-question mock experiment.

## Reproducibility and split discipline

`evaluation_config.json` records the baseline retrieval K (5), relevance threshold (0.35), cosine distance, embedding model (`text-embedding-3-small`), configurable generation model setting (`OPENAI_CHAT_MODEL`, project default `gpt-4.1-mini`), prompt identifiers A/B/C, duplicate policy, seed status, and cost-rate status. These are evaluation metadata, not changes to production config. A future run must additionally record the resolved model, dataset/manifest checksums, prompt ID, runtime configuration, token usage, and score-output version.

The starter dataset is development data only. `datasets/held_out/` is deliberately empty and has its own README. Do not copy development questions into held-out and then use the result for unbiased evaluation. Acquire and review permitted sources and hold-out labels independently before tuning or reporting final model comparisons.

## Limitations

- No real permitted university source documents were available, so all 12 examples and both PDFs are synthetic. They must never be presented as policy.
- The Phase 7B benchmark is a synthetic development baseline, not a real-policy or production embedding benchmark.
- It does not measure semantic faithfulness, claim correctness, answer relevance, or live model cost. Phase 7B measures local retrieval latency only; it is not production-service latency.
- Evaluation indexing uses an isolated temporary ChromaDB directory and does not write to production SQLite or ChromaDB.
- A small starter set is not a statistically representative benchmark; no held-out set exists yet.
- Phase 6E reported that live OpenAI integration was not tested. Phase 7A makes no live calls and does not change that status.

## Phase 7E final consolidation and live-evaluation gate

Phase 7E consolidates the preserved Phase 6E–7D reports and measured JSON artifacts into `results/final_benchmark.json`, `results/final_benchmark.md`, the Phase 7E report at `../PHASE_7E_REPORT.md`, and the consolidated `../FINAL_RAARA_RESEARCH_REPORT.md`. The pinned run plan is `final_benchmark_config.json`; static SVG figures are in `results/figures/`. The build command is:

```powershell
.\.venv311\Scripts\python.exe -m evaluation.scripts.build_final_benchmark
```

The final report keeps the Phase 7B retrieval baseline, Phase 7C controlled/e2e answer and citation metrics, and Phase 7D A/B/C simulated diagnostics separate. The 12-question development corpus is synthetic and no held-out split exists; the held-out benchmark therefore remains blocked. Phase 7D's mock ignores prompt content, so tied A/B/C results are simulated diagnostics, not prompt performance. Live OpenAI, browser acceptance, and semantic faithfulness are not claimed as tested.

No OpenAI call is made by the final benchmark builder or readiness checker. Before any future live run, require explicit authorization and configure all of the following: `RAARA_ENABLE_LIVE_EVAL=true`, `OPENAI_API_KEY`, `RAARA_EVAL_MODEL`, positive `RAARA_EVAL_MAX_CALLS`, and positive finite `RAARA_EVAL_MAX_BUDGET_USD`. Check readiness without a network call:

```powershell
.\.venv311\Scripts\python.exe -m evaluation.scripts.check_live_eval_readiness
```

The checker reports only readiness and blockers; it never reveals a credential, initializes an OpenAI client, or sends a request. Readiness alone is not authorization to run the experiment. See `datasets/held_out/README.md` and `datasets/held_out/annotation_template.json` for the future independent annotation workflow. These are workflow materials, not held-out data.

## Phase 8A held-out document and annotation preparation

Phase 8A adds a separate real-world held-out schema in `schemas/held_out.py` and validation/import workflow in `heldout.py`; it does not change the Phase 7 development schema or production application. The held-out split currently contains an empty `questions.jsonl` and `documents.json` registry. The existing 12-question synthetic development corpus remains separate.

Use the held-out tooling from `backend`:

```powershell
.\.venv311\Scripts\python.exe -m evaluation.scripts.import_heldout_document --help
.\.venv311\Scripts\python.exe -m evaluation.scripts.annotate_heldout
.\.venv311\Scripts\python.exe -m evaluation.scripts.review_heldout_annotation --help
.\.venv311\Scripts\python.exe -m evaluation.scripts.validate_heldout_dataset
```

The PDF importer records required provenance/permission details, copies original PDF bytes without transformation, hashes content, rejects duplicates and refuses overwrite. Claimed official authority remains pending until independently reviewed. The interactive annotation workflow creates `PENDING_REVIEW` labels, checks exact evidence on the stated page and version, and prevents exact question/ID overlap with development data. An independent reviewer can record `APPROVED`, `REJECTED`, or `NEEDS_CORRECTION`; legacy `reviewed`/`approved` values remain accepted. Approval requires a distinct reviewer and verified official sources. Unofficial references remain labeled and cannot be authoritative support for approved regulatory annotations. `DRAFT` is planning-only.

`datasets/held_out/readiness_report.json` and `.md` report real current counts. A valid empty split returns successfully while showing `EMPTY`, Phase 8B not ready, and Phase 8C not ready; no question is synthesized. The target is 40–60 independently annotated questions, but the importer and authoring workflow do not generate content. Run isolated fixture tests with:

```powershell
.\.venv311\Scripts\python.exe -m pytest -v evaluation\tests\test_heldout_workflow.py
```

## Phase 8B source acquisition and inspection

PES University source discovery is tracked at `evaluation/held_out/SOURCE_INVENTORY.md` with a JSON companion. Original candidate PDFs are in `evaluation/held_out/documents/`; `PDF_INSPECTION_REPORT.md` records hashes, page/text extraction counts, and warnings. The candidate files do not enter the authoritative Phase 8A registry automatically. They remain outside `evaluation/datasets/held_out/documents.json` until a separate human completes source and applicability review. No real questions or answers were created in this phase.

The source inventory contains 24 tracked sources: 11 official-verified source records, 9 official-unverified records, and 4 wrong-institution/scope exclusions. Three PDFs were downloaded; two are verified as official-source documents and one remains exact-file unverified. The Act is a scanned image PDF with no extractable text. The UGC Proforma is an archival 2014 submission, not a current B.Tech rulebook. The AI/ML curriculum is batch-specific and its campus applicability is unknown. Accordingly, the held-out registry and question set remain empty and readiness is `EMPTY`.

The readiness validator accepts the source inventory and includes acquisition counts separately from imported-document and annotation counts. At the Phase 8B checkpoint there were 24 tracked records; Phase 8C extends the inventory to 38 discovery records: 13 official-verified, 10 official-unverified, 7 wrong-institution, and 8 third-party references. The three candidate PDFs remain outside the Phase 8A registry pending review.

```powershell
.\.venv311\Scripts\python.exe -m evaluation.scripts.validate_heldout_dataset
```

## Phase 8C authority review and page-level evidence

Phase 8C adds `evaluation/schemas/policy_evidence.py` and `evaluation/policy_evidence.py` for provenance-bound evidence candidates. Candidate records are in `evaluation/held_out/evidence_candidates.jsonl`; validation checks inventory identity, URL/path, root containment, original PDF hash, page range, verbatim page text, and duplicates. OCR evidence is rejected unless a separate reviewed artifact exists. The authoritative selector requires all three: `VERIFIED_AUTHORITATIVE`, `HUMAN_APPROVED`, and `CURRENT`.

The three inspected PDFs remain classified as `EXTRACTION_BLOCKED` (Act), `VERIFIED_OFFICIAL_CONTEXT_ONLY` (2014 UGC Proforma), and `PENDING_HUMAN_AUTHORITY_REVIEW` (2025-26 AIML curriculum). The four extracted snippets are candidates only; they are all `NOT_REVIEWED`, none is authoritative, and no source was imported into the Phase 8A registry. The matrix marks missing current rules as `NO VERIFIED EVIDENCE FOUND`. See `evaluation/held_out/POLICY_EVIDENCE_MATRIX.md`, `HUMAN_AUTHORITY_REVIEW.md`, `OCR_REPORT.md`, `CONFLICT_AND_VERSION_ANALYSIS.md`, and `../PHASE_8C_REPORT.md`.

Local OCR software and libraries were unavailable, so the Act remains blocked. The original file was preserved and no external OCR service was used. No production RAG code or production storage was modified. Re-run Phase 8C checks with:

```powershell
.\.venv311\Scripts\python.exe -m pytest -v evaluation\tests\test_policy_evidence.py evaluation\tests\test_heldout_workflow.py
.\.venv311\Scripts\python.exe -m evaluation.scripts.validate_heldout_dataset
```

Phase 8D prepared `evaluation/held_out/HUMAN_REVIEW_PACKAGE.md` without changing any `NOT_REVIEWED` state. `evaluation/TOKENIZER_OFFLINE_RECOVERY.md` documents the required `cl100k_base` data file and its pinned SHA-256. With that verified cache, the Phase 8D regression run passed: 32 evidence/held-out tests, 84 evaluation tests, and 189 tests in the complete backend suite. Tests used isolated temporary storage; no live OpenAI call or production database/vector-store write was made. Current readiness remains `EMPTY` pending human authority review.

## Phase 8E official regulation acquisition status

Phase 8E checked the official PES academic, B.Tech, AIML syllabus, FAQ, calendar, Important Information, and Public Self Disclosure sources. The Public Self Disclosure index lists item 3.3, “Statutes/Ordinances Pertaining to Academics/Examinations,” but its public target could not be retrieved; no B.Tech AIML regulation file was acquired. The current official FAQ's broad attendance/grading statements lack sufficient programme, campus, batch, effective-date, and controlling-rule details for authoritative use.

The registry remains empty and the four evidence candidates remain `NOT_REVIEWED`. No production database, ChromaDB, RAG logic, prompts, or retrieval settings were changed. See `evaluation/held_out/DOCUMENT_APPROVAL_STATUS.md`, `MISSING_REGULATIONS_REPORT.md`, updated `POLICY_EVIDENCE_MATRIX.md`, and `SOURCE_INVENTORY.md`. Dataset readiness remains `EMPTY`; the readiness validator's JSON/Markdown reports are generated from the empty registry and updated 40-source discovery inventory.

## Phase 9A synthetic project corpus

`synthetic_project_data/` is an isolated academic demonstration corpus, explicitly **not official PES University policy**. It contains 10 current-model synthetic policy documents in Markdown and generated PDFs, 2 separate superseded conflict fixtures, and 50 questions partitioned into synthetic development (36), synthetic held-out (11), and a separate conflict set (3). Every item is marked `SYNTHETIC_PROJECT_DATA`, `PROJECT_AUTHORED`, and `is_official_university_policy: false`. The synthetic held-out partition is not the real-source held-out registry under `datasets/held_out/`.

Build and validate the Phase 9A material, then run its offline A/B/C diagnostics:

```powershell
$env:TIKTOKEN_CACHE_DIR = 'C:\Users\Pratik Kalloli\AppData\Local\Temp\data-gym-cache'
.\.venv311\Scripts\python.exe -m evaluation.synthetic_project_data.build_dataset
.\.venv311\Scripts\python.exe -m evaluation.synthetic_project_data.validate
.\.venv311\Scripts\python.exe -m evaluation.synthetic_project_data.run_benchmark
```

The validator reuses the existing dataset schema and PDF/page/evidence validator, verifies checksums and classifications, checks exact evidence spans and development/held-out separation, and independently recomputes weighted score, SGPA and CGPA examples. The benchmark runner uses the existing Phase 7D A/B/C prompt experiment, retriever, chunker, evaluation indexer, citation verifier and metrics. It evaluates development questions only, uses deterministic local TF/hash embeddings plus a deterministic mock generator, and indexes the ten current-model documents into temporary Chroma storage. Held-out questions are not scored; historical conflict documents are not mixed into the primary current-policy index. No live OpenAI call or production storage write is made. Mock equality does not establish real prompt performance, and lexical/exact-span metrics do not establish semantic faithfulness. See `synthetic_project_data/SYNTHETIC_DATASET_DOCUMENTATION.md`, `SYNTHETIC_POLICY_REGISTER.md`, `SYNTHETIC_CONFLICT_SCENARIOS.md`, and `results/benchmark_validation_report.md`.

## Phase 8C resumption (2026-11-13)

The official-source resumption rechecked current PES public discovery pages but acquired no current B.Tech AIML regulations. The AIML syllabus page lists batch curriculum content; its live download points to Google Drive, leaving the local curriculum PDF’s exact file linkage for human review. The disclosed item 3.3 route remains inaccessible. No evidence was inferred from these pages, all four existing candidates remain `NOT_REVIEWED`, the Phase 8A official registry remains empty, and readiness remains `EMPTY`. See `PHASE_8C_REPORT.md` and the resumption sections in the held-out source, matrix, OCR, conflict and review documents.

## Phase 8C resumption validation results

The 2026-11-13 resumption ran the held-out dataset validator (`EMPTY`, no imported documents or questions), Phase 9A synthetic validator (`PASS`, 50 synthetic questions and 86 exact evidence references), and full backend suite (**198 passed, 0 failed**). The 3 candidate PDF checksums match the inventory and all 4 evidence candidates remain `NOT_REVIEWED`. The readiness artifacts are regenerated from the unchanged empty official registry and the 40-source inventory. No official document was imported and no current regulation was verified.

## Phase 8C Stage 2 — public-source discovery and human review

Stage 2 expanded `evaluation/held_out/source_inventory.json` to 44 source records and updated `SOURCE_INVENTORY.md`, `POLICY_EVIDENCE_MATRIX.md`, `MISSING_REGULATIONS_REPORT.md`, `HUMAN_AUTHORITY_REVIEW.md`, `OCR_REPORT.md`, and `CONFLICT_AND_VERSION_ANALYSIS.md`. Discovery sources and context PDFs are not regulatory approval. The current AIML regulations, batch versions, and item 3.3 target remain unavailable for applicability review; the official registry and held-out questions remain empty.

An optional interactive review utility exists at `evaluation/scripts/review_policy_evidence.py`. Review is deliberately not performed by validators or tests. To inspect usage:

```powershell
.\.venv311\Scripts\python.exe -m evaluation.scripts.review_policy_evidence --help
```

The decision workflow requires a human reviewer ID, explicit approve/reject decision, rationale, and confirmation. Approval requires `VERIFIED_AUTHORITATIVE` and `CURRENT`, and is stored in a separate hash-chained ledger; source evidence files are not modified. Do not treat running tests or validators as human review.

Stage 2 verification from `backend` (Python 3.11.9, `.venv311`):

```powershell
.\.venv311\Scripts\python.exe -m evaluation.scripts.validate_heldout_dataset
.\.venv311\Scripts\python.exe -m evaluation.scripts.validate_dataset --dataset evaluation\datasets\development\raara_synthetic_starter_v0.1.0.jsonl --manifest evaluation\datasets\development\manifest.json
.\.venv311\Scripts\python.exe -m pytest -v
```

The observed results were held-out readiness `EMPTY` (0 imported documents, 0 questions, 0 approved annotations), development validation passed for 12 synthetic questions, and the complete backend suite passed **208 tests**. Tests used isolated storage and mocked/local substitutes; no live OpenAI call was made. See `../PHASE_8C_STAGE2_REPORT.md` for full counts, limitations, and dispositions. Phase 8C Stage 2 did not begin subsequent phases.

## Phase 8C Stage 3 — generic academic policy demo corpus

`datasets/project_authored_academic_policy/` is a standalone corpus with 28 policies and 30 clearly labeled project demonstration questions. Every policy is `PROJECT_AUTHORED`, `GENERIC_PROJECT_POLICY`, `NOT_OFFICIAL`, and has `is_official_university_policy: false`. The project-only `PROJECT_APPROVED` marker is not authority approval. This corpus is separate from Phase 9A, the official held-out registry, and production storage. It does not replace or alter the PES FAQ's separate 80% attendance discovery record.

Validate the content and recompute formulas from `backend`:

```powershell
.\.venv311\Scripts\python.exe -m evaluation.scripts.validate_project_authored_policies
.\.venv311\Scripts\python.exe -m pytest -v evaluation\tests\test_project_authored_policies.py
```

The offline helper `evaluation/project_authored_policies.py` prefixes generic policy context with a project-authored/nonofficial disclaimer and returns an abstention for recognized official-institution questions. It is not wired into the production chat/retrieval pipeline. No generic records were indexed or imported. Future demo retrieval must use its own evaluation-only collection and still label evidence as a project assumption; it must not share production ChromaDB or pass through the official evidence gate.

See `datasets/project_authored_academic_policy/README.md` and `GENERIC_POLICY_ASSUMPTIONS.md` for assumptions, scope, restrictions, and a future replacement process. Stage 3 results and limitations are recorded in `../PHASE_8C_STAGE3_REPORT.md`.

## Phase 8C Stage 4 — isolated generic-policy RAG demo

`evaluation/generic_policy_demo/` provides an offline, process-local demo over only the separate 28-record project-authored dataset. It reuses the deterministic TF/hash evaluation embedder from `evaluation/retrieval/embeddings.py` with cosine similarity, not the production vector store. The embedder is in a pure module so importing the demo does not load `app.config` or `.env` settings. The demo default threshold is 0.12 and top-K is 5; both are local CLI options. `cli.py` supports interactive questions and `--question` one-shot use. The answerer uses deterministic templates and calculations, not an LLM; no API/network calls are made.

Every retrieved record is revalidated as `PROJECT_AUTHORED` / `GENERIC_PROJECT_POLICY` / `NOT_OFFICIAL` / nonofficial. Answer citations are checked against retrieved policy/evidence IDs and carry title, category, version, provenance, and `PROJECT_AUTHORED_GENERIC_POLICY`; no pages or URLs are fabricated. Recognized official university/PES and admission-batch questions abstain. Missing values, unrelated questions, ambiguity, calculation input errors, and project-only version conflicts have explicit outcomes. Retrieval scores indicate lexical similarity only.

Run the demo from `backend`:

```powershell
.\.venv311\Scripts\python.exe -m evaluation.generic_policy_demo.cli
.\.venv311\Scripts\python.exe -m evaluation.generic_policy_demo.cli --question "What is the illustrative minimum attendance?"
```

No persistent index is created. The module does not import production chat routes or write to SQLite/Chroma. The Stage 4 report at `../PHASE_8C_STAGE4_REPORT.md` records test results, sample CLI outputs, threshold observations, limitations, and the one dataset text-encoding normalization made for stable terminal display.

Stage 4 final verification: the focused demo tests passed (27), the generic-policy plus Stage 3 retrieval focused set passed (45), and the complete backend suite passed (247). Regression tests use isolated SQLite, ChromaDB, and upload paths; see the Stage 4 report for exact commands and the tokenizer-cache note.
