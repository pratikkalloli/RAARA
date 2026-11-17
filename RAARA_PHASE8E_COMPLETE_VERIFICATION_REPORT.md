# RAARA Phase 8E — Complete Post-Repair Audit and Verification

**Audit date:** 2026-11-15  
**Overall classification:** **BLOCKED — supplied backend run has one protected fingerprint failure; latest targeted edits are untested**  
**Protected Phase 9A integrity check:** **FAIL** (aggregate mismatch; historical cause cannot be isolated from the available baseline)

## Executive summary

The Phase 8E repair files were reviewed directly. They contain targeted changes to numerical claim checking, hierarchical summary coverage tracking, Gemini interpretation diagnostics, and evidence-aware abstention. No source files were changed during this audit.

The reported Phase 9A aggregate fingerprint mismatch is reproducible: the current tree hashes to `2f85936bb776a0fea3fdaed1fffe013cd138022d4e8a37ab954ca2d418cc0013`, while the protected test expects `e60703d320a2339b2fc1181a0ca1ce55e980744ce6fe87358eac9c6cecaab4fd`. The aggregate algorithm includes 45 files, including scripts and generated result reports. All 12 PDFs match the SHA-256 values in their manifests, and the master question set and primary manifest match their recorded checksums. With no Git metadata and no earlier per-file hash list, it is not possible to name individual files that differ from the expected aggregate. Timestamps indicate the included Phase 9A tree predates the Phase 8E edits, but this does not establish when or why the aggregate drift occurred.

The user supplied Ubuntu results after the Phase 8E repairs: focused tests **72 passed in 46.90s**; full backend suite **371 passed, 1 failed in 194.48s**. The sole failure was `evaluation/tests/test_project_authored_policies.py::test_phase9a_assets_remain_byte_for_byte_unchanged`. These are attributed user-run results, not a Codex-run execution. During the prior audit, WSL could not launch, so Codex did not independently rerun the backend tests. The targeted safety edits from the current follow-up were made after those supplied results and have not been tested. Frontend tests and a production build passed. No backend health, authentication, upload, or chat integration check was run because no listener was found on ports 8000 or 5173.

No Gemini/OpenAI calls were made. No API credentials were accessed. No production database, ChromaDB, uploads, official evidence, or Phase 9A files were modified.

## Phase 9A fingerprint investigation

### Fingerprint algorithm and scope

`backend/evaluation/tests/test_project_authored_policies.py::_phase9a_fingerprint()` recursively selects every file under `backend/evaluation/synthetic_project_data`, excluding files whose path has a `__pycache__` component and files with the `.pyc` suffix. It sorts paths, then hashes each relative POSIX path, a NUL separator, and the SHA-256 digest of that file’s bytes into the aggregate SHA-256. It does not fingerprint only the PDF corpus: Python scripts, manifests, datasets, README material, and generated benchmark outputs are included.

The current tree contains 45 included files. A read-only PowerShell reproduction of the algorithm produced the reported actual hash exactly:

| Check | Result |
|---|---|
| Expected aggregate | `e60703d320a2339b2fc1181a0ca1ce55e980744ce6fe87358eac9c6cecaab4fd` |
| Current aggregate | `2f85936bb776a0fea3fdaed1fffe013cd138022d4e8a37ab954ca2d418cc0013` |
| Current included files | 45 |
| Aggregate comparison | **FAIL** |

### Individual-file comparison and historical limits

There is no `.git` directory available in the project, no Git history to compare, and no per-file baseline hash manifest associated with the expected aggregate. A single aggregate hash cannot be inverted to identify which constituent file or files differ. Therefore, **the exact mismatching file paths and their before/after hashes are unavailable**; it would be inaccurate to label any current file as a confirmed mismatch from the aggregate alone. Current hashes are inventoried in the appendix for a future owner-supplied baseline comparison.

The current files’ modification times fall on November 13, 2026, while the listed Phase 8E backend edits fall on November 15, 2026 and are outside the fingerprint root. This supports, but does not prove, that the fingerprint drift predates the Phase 8E repair. Timestamps can be preserved or changed independently of file content, so the cause and time of drift remain **unknown**. There is no evidence from this audit that Phase 8E changed an included Phase 9A file.

The fingerprint implementation itself is present as described above; without Git or a prior copy of the test file, historical implementation changes cannot be independently ruled out. Sorting and POSIX-relative-path normalization are explicit in the implementation. The PowerShell reproduction used the same path ordering and byte hashing. The mismatch is not explained by an ordering discrepancy in that reproduction. Generated benchmark outputs are included by design, so rerunning benchmark writers could change this aggregate even when source PDFs remain unchanged.

### Current internal integrity checks

- **12/12 PDF files:** byte hashes match the SHA-256 values embedded in their corresponding primary/conflict manifests.
- `datasets/synthetic_questions.json`: matches `master_questions_sha256` in the benchmark validation report.
- `synthetic_dataset_manifest.json`: matches `primary_manifest_sha256` in the benchmark validation report.
- File count: 45, same as the Phase 8C Stage 3 report’s recorded count.
- Individual files differing from the old baseline: **undetermined**, not “zero”; no per-file baseline exists.

No Phase 9A asset was edited, restored, regenerated, or rehashed into the expected test constant during this audit. The failing test must remain failing until the owner supplies a trusted baseline or approves a separate baseline investigation. Do not update the expected fingerprint based on the current tree.

## Phase 8E source audit

### Files reviewed and reported as changed by the repair

Application files:

- `backend/app/services/factual_verifier.py`
- `backend/app/services/document_summarizer.py`
- `backend/app/services/generator.py`
- `backend/app/services/request_interpreter.py`

Tests reported as added or updated:

- `backend/tests/test_factual_verifier.py`
- `backend/tests/test_document_summarizer.py`
- `backend/tests/test_gemini_provider.py`

Reports reviewed:

- `RAARA_PHASE8E_REPAIR_REPORT.md`
- `RAARA_PHASE8E_LIVE_ACCEPTANCE_REPORT.md`

The repair report states eight new test functions were added. As the project has no Git metadata, this list relies on the repair record and file inspection, not a canonical diff. No frontend files are reported as part of the Phase 8E repair.

### Numerical verification — source review

The current verifier strips a leading numbered-list marker and text matching its page-reference pattern before extracting numeric values. The existing model-assisted review is still responsible for subject, unit, condition, date/range, and semantic distinctions; factual numeric tokens are checked for completeness, and evidence IDs are checked against actual cited passages. The summarizer still invokes the verifier.

**Residual risk:** the page-reference regular expression can also remove a factual page count such as “the PDF has 13 pages,” not only a citation locator. This can create a false acceptance if the model-assisted review omits that quantity while the deterministic completeness check has stripped it. The numeric-token comparison is not a proof that each number is attached to the correct subject or unit. The model review is explicitly fail-closed for incomplete/ambiguous responses, but that behavior has not been executed in the current backend runtime. The 40/60 versus 32/45 distinction therefore remains unverified after the repairs.

### Hierarchical summarization — source review

The summarizer deduplicates passages, may use a spread sample at its configured maximum, reduces passages in batches, and tracks original passage IDs represented by verified intermediate citations. Each intermediate response is checked against its batch using `CitationVerifier`; failed batches or batches with no valid cited children are excluded from subsequent summary text and counted as unrepresented. Original IDs and page metadata are remapped for final citations. Sampling, failed intermediate representation, and final citation coverage limitations are described in the response, and a result with coverage notes is downgraded from `SUPPORTED` to `PARTIALLY_SUPPORTED`.

**Residual risk:** the citation verifier validates citation identity and metadata, not whether every sentence in an intermediate summary is entailed by those citations. Where an intermediate answer retains text alongside at least one valid citation but has citation issues, the verifier can preserve the answer with a warning and partial status; that text can become a downstream summary node. This leaves a route for unsupported intermediate prose to persist. Final citation remapping and coverage disclosure do not establish semantic faithfulness. These are review findings, not demonstrated live exploits.

If the document is over the summarizer’s configured chunk cap, a spread sample is used and disclosed; the repair did not change that setting. Runtime behavior, exact five-point output, all-page coverage, and citation page mapping have not been rerun.

### Gemini request interpretation and authorization — source review

The Gemini adapter supplies a structured JSON schema; required fields and nullable fields are represented in the schema, and `RequestInterpretation` performs Pydantic validation. Route consistency checks reject contradictory route/evidence states. Validation diagnostics log exception class and schema location/type details rather than raw model output, prompt, document text, or input values. Public errors remain generic. The old live 503’s exact rejected field remains unknown; the repair report says its detail was not retained.

The chat route and service retain owner-scoped document selection: a selected document is resolved among the authenticated user’s documents, and chat selection is constrained to the authorized document. This was source-reviewed only; cross-user denial, selected-document propagation, conversation context, and current runtime schema acceptance were **NOT TESTED** in this audit.

### Evidence-aware abstention and citation behavior — source review

Abstention disclosures are derived from retrieval/provenance state, including no accessible document, no relevant passages, unavailable indexed text, or synthetic/unverified sources. The code does not itself supply an official policy value in the deterministic disclosure, and a no-evidence NOT_FOUND response has no citations. Unverified sources are explicitly labeled in the citation verifier.

**Residual risk:** where generated prose accompanies the deterministic disclosure, the generated text is not a deterministic semantic guarantee. Citation identity validation cannot prove an answer is correct or faithful. The citation verifier’s own module documentation states this limitation and sets `semantic_faithfulness` to `NOT_VERIFIED`. No post-repair live output was examined.

### General code review

The edited service blocks and corresponding tests were read. No raw prompts or model output are written by the reviewed interpreter validation diagnostics. The repair report records no architecture, provider/model configuration, retrieval threshold, frontend, authentication, or production-store changes. Syntax, imports under the approved runtime, test behavior, and runtime dependency injection cannot be certified because no backend Python execution was permitted in this environment. No Git status/diff is available.

## Test and integration results

### Historical results (not current verification)

| Run | Reported result | Status for this audit |
|---|---:|---|
| Focused Phase 8E tests, Ubuntu run supplied by user | 72 passed in 46.90s | **USER-REPORTED PASS** for the then-current Phase 8E repair; not rerun by Codex |
| Full backend suite, Ubuntu run supplied by user | 371 passed, 1 failed in 194.48s | **USER-REPORTED FAIL**: sole failure `evaluation/tests/test_project_authored_policies.py::test_phase9a_assets_remain_byte_for_byte_unchanged` |
| Prior baseline stated in repair report | 204 backend tests passed before repairs | Historical baseline; does not verify repair files |

### Verification executed for this audit

| Check | Exact command / method | Result |
|---|---|---|
| Backend runtime availability in prior audit | Checked `backend/.venv-wsl311/bin/python` path and WSL status from Windows context | **BLOCKED**: WSL launch returned `Access is denied. Error code: Wsl/E_ACCESSDENIED`; no alternate Python runtime used. |
| Focused backend tests in prior audit | Not run by Codex; user supplied the 72-pass Ubuntu result above | **USER-REPORTED PASS / CODEX NOT RUN** |
| Full backend suite in prior audit | Not run by Codex; user supplied the 371-pass, 1-fail Ubuntu result above | **USER-REPORTED FAIL / CODEX NOT RUN** |
| Evaluation tests in prior audit | No separate Codex run; user’s full backend result includes the protected fingerprint test failure | **CODEX NOT RUN** |
| Frontend tests | `npm test -- --test-reporter=spec` in `frontend` | **PASS**: 8 passed, 0 failed; exit code 0. |
| Frontend production build | `npm run build -- --outDir <temporary audit directory>` in `frontend` | **PASS**: Vite 6.4.5 transformed 26 modules and completed successfully; existing `frontend/dist` was not targeted. |
| Backend health / authenticated integration | Checked listeners on ports 8000 and 5173; none found | **NOT RUN**: no application server was running; no server was started. |
| Frontend key-pattern scan | `rg -l` over `frontend/src` and existing `frontend/dist` for common Gemini/OpenAI key patterns | No matches found. This is a limited static scan, not a security proof. |
| Browser acceptance | Not run | **NOT RUN** |
| Gemini/OpenAI live calls | Not run | **NOT RUN** by instruction; no credentials accessed. |

The supplied backend results are explicitly attributed to the user. The follow-up numerical and summarization regression tests added after that run are not covered by those results.

## Security and data protection

- Production SQLite, ChromaDB, uploads, user data, evidence approvals/registries, and Phase 9A assets were not modified.
- The Phase 9A tree was read and hashed only.
- No live Gemini or OpenAI call was made; credentials were not read, printed, or logged.
- No test server, database, upload, or acceptance account was created.
- No Phase 9A asset was added, removed, or rewritten by this audit.
- Frontend build output was directed to a temporary directory; existing `frontend/dist` was left untouched.
- No tests were disabled, skipped, deleted, weakened, or edited.

## Remaining issues and limitations

1. **Phase 9A aggregate mismatch remains unresolved.** Exact constituent mismatch paths cannot be derived without a trusted per-file baseline or historical tree. Preserve the failing test and expected hash. Owner review is required before changing either.
2. **Backend test verification is blocked for the current follow-up edits.** User-reported prior results are 72 focused tests passed and 371 passed/1 failed in the full suite. A WSL attempt for this follow-up again returned `Wsl/E_ACCESSDENIED`; the newly added targeted tests are unverified here, and no alternative Python runtime was used.
3. **No live acceptance was run.** Gemini interpretation, selected-document whole-PDF summaries, provenance-aware abstention, citation page mapping, numerical safeguards, conversation persistence, and cross-user access remain unverified after repair.
4. **Semantic faithfulness remains unverified by design.** Citation identity is not semantic validation. Numerical checking remains model-assisted. The current follow-up narrows page-locator stripping and labels hierarchical semantic faithfulness NOT_VERIFIED, but those changes are not yet tested.
5. **Intermediate summary limitation.** Citation-checked intermediate text can still contain unsupported prose when its citation identities are valid. The follow-up marks such summaries as semantically unverified and forces PARTIALLY_SUPPORTED with an explicit disclosure; this is an honest limitation, not semantic verification or proof that every claim is supported.
6. **No application integration checks.** No backend/frontend server was running, so health, auth, upload, chat, persistence, and browser contracts were not exercised.

## Manual Ubuntu verification commands

Run only in the project’s approved Ubuntu/WSL environment. These commands create isolated temporary storage and leave production storage paths untouched. Keep test credentials blank and do not run live acceptance as part of pytest.

```bash
cd /mnt/c/prompt_mini_proj/backend
export TIKTOKEN_CACHE_DIR="$HOME/.cache/tiktoken"
ISOLATION="$(mktemp -d /tmp/raara-phase8e-audit-XXXXXX)"
export GEMINI_API_KEY=
export OPENAI_API_KEY=
export DATABASE_URL="sqlite:///$ISOLATION/backend.db"
export CHROMA_PERSIST_DIR="$ISOLATION/chroma"
export UPLOAD_DIR="$ISOLATION/uploads"
export JWT_SECRET_KEY="phase8e-test-only-$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
mkdir -p "$CHROMA_PERSIST_DIR" "$UPLOAD_DIR"

# Focused Phase 8E and adjacent chat regressions
./.venv-wsl311/bin/python -m pytest -v \
  tests/test_factual_verifier.py \
  tests/test_document_summarizer.py \
  tests/test_gemini_provider.py \
  tests/test_chat_behaviors.py \
  tests/test_full_audit_regressions.py

# Relevant evaluation tests, including the protected fingerprint check
./.venv-wsl311/bin/python -m pytest -v evaluation/tests

# Complete backend suite
./.venv-wsl311/bin/python -m pytest -v tests evaluation/tests
```

Record exit codes and actual pytest summaries. Do not change the fingerprint constant to obtain a pass. If the WSL environment remains unavailable, stop and report that blocker. Only after focused and complete local regressions pass should a separately approved, isolated live Gemini acceptance be considered.

## Appendix — current Phase 9A file hashes

These are **current** SHA-256 values, not identified mismatches against the unavailable historical per-file baseline.

```text
__init__.py 5af1dc7ff0eb1b2dfa11eb680ffb59df38022372228eb5bf8c9657f49844e732
build_dataset.py 31df69875801700f855ef985ca3fb5d39f334857d2f2c6f500aeb2df19571718
conflicts/conflict_manifest.json f230eaab90a2e69ec8b1f179d72652046dd0f02ea4734ee3bd980d90239c0b67
conflicts/older_assessment_v0.9.md 69c8919b1f869f1bbc84c9d703926e36aa7b4baa62363ac5d1bda33551a60d28
conflicts/older_attendance_v0.9.md 5ebb63a2e631f0be3345326769e530ab0b53a25bf472dd9ae71cfd16e419e55f
conflicts/pdfs/SYNTH-P9A-ASSESSMENT-OLD-C02.pdf 59301127eab4f8b7e385747903c7e0b512f6af19c8d0c306182a7bc75d174f73
conflicts/pdfs/SYNTH-P9A-ATTENDANCE-OLD-C01.pdf 3af59e76f6af56898613ed181a5576897716cfab8287fed9f5554efdb6d6fdb0
conflicts/synthetic_conflict_scenarios.json b783df2baf572915e08139691d5a05b732ef3bd3d2fdb801727d8a9fd41e5259
corpus/01_programme_structure.md b7ef6639959f5f96e19ec0cd1098b0872d4534855c23054ac5b0d8e9885c1209
corpus/02_lateral_entry_bridge.md 698d65c4b0a4a57a7e702a5c36828dc6fc8c2181386330877d7fdbf32ed7e6af
corpus/03_progression_regular.md 2e0bd785ae6e84abf9992e6d4aa250bf72b168354cbd9c14e9584b44bfe58b76
corpus/04_progression_lateral.md 02852b3f4aac963854e5e03ec52d39b89409ad5dfaa4deda4eff8031e4e87378
corpus/05_attendance_eligibility.md dcf82d11e17be67c664dc466d2ea821ea889a4175446ff59f3428bb516489607
corpus/06_assessment_scheme.md 9d632eaa62f7201dedfeb1b954bb8a9722ec32eb9cffacb96e668168542d4cbf
corpus/07_grading.md eda503c24283a0d6ec2ad22564e2e92d65f3b49261c8c2fb09bf2b72c9e0216f
corpus/08_sgpa_cgpa.md 2f258206d954d69f5497ef1a45ece76aac1f49c456ee6a950d4451fa055ba003
corpus/09_backlog_supplementary.md 9e516c61d7c54bfdfac2980c03a22b72c641c3e7a43600238ea241979e2c8044
corpus/10_revaluation_exam_procedures.md 8a770632a748f09652188a389993f4aa3c7e2708bdf2724a9f9c4d152258d137
corpus/pdfs/SYNTH-P9A-ASSESSMENT-06.pdf b7724c61f3891ac3dcca52ccd39e5c740c0086cc5390f2f153f9302a73ed2a76
corpus/pdfs/SYNTH-P9A-ATTENDANCE-05.pdf d1c3c741ccae3dbe0a1947e69b57370d5451edfa5ec80cdae64485c849937b0b
corpus/pdfs/SYNTH-P9A-BACKLOG-09.pdf c525c9b9b253766f3a402891b3596b9fa5ab0a31e0a180c97e5e8bbc23258b33
corpus/pdfs/SYNTH-P9A-GRADING-07.pdf fb86546ba2909e6daeb8f47fd0c9ccd81618da043bb90cc729c3d894b43173f9
corpus/pdfs/SYNTH-P9A-LATERAL-02.pdf 8cd9c3ac15145e452e865ffdecf27e660ce6b474a9918b41454bb8ab16a6ca78
corpus/pdfs/SYNTH-P9A-PROGRESSION-LAT-04.pdf e0de2b2cb8783b9831e240b351e0be36bc3a32d22a457624595e98353b32d571
corpus/pdfs/SYNTH-P9A-PROGRESSION-REG-03.pdf 2b2e4b91a3e646ab31a7427bf7203fca0bbb44d81830db8b6bff54f79287d629
corpus/pdfs/SYNTH-P9A-REVALUATION-10.pdf 62d16c53794b78ae93b848894cc98aa8924c616472f3814b9385355c674e02d8
corpus/pdfs/SYNTH-P9A-SGPA-08.pdf 590e02f1299ace3fd2ba32d83623509296e53f204ac3e4d950af83c3dcef8dc1
corpus/pdfs/SYNTH-P9A-STRUCTURE-01.pdf c8ebb609647e0267c86e282b622d4a2a91d27457ac07e0cfeb3eda124cb0ca08
datasets/conflict/questions.json ca229a371df348e59dce1c248dd72e5f8a72d05d6e8bf92e8eea1f10e0cabb99
datasets/development/questions.json e7cc1d5c4c9df11242989f08f3bdcabbf0a213f085358915fe3c016fa03a1f8d
datasets/held_out/questions.json 00099697242ef5a873fb502205ad22eccd10556e36475aa9c14b36b9637705c7
datasets/synthetic_questions.json 06d5731d923e69d48aa1724edee63f01e80b14958c65207c7bb77fc74ae12158
README.md e3f5cd9487bbca62155d548c03235fd36acac2c57389c44c7d767c24e9c55231
results/benchmark_validation_report.json 4d4d157a79eb9aebfc6c8fbcd17f2f9dfcb7cf124edc5ad440bf686ecea65bbc
results/benchmark_validation_report.md 821cf5d624a92374156a52deeff47eeff2f5a0f9ead6400351eb3442ed8c251d
results/synthetic_prompt_comparison.json c5ed3c6bfdc354b80cabc9c1482b0ea8c369a25934fda05b8a90d0f4968411b2
results/synthetic_prompt_comparison.md c1a607eb80ac57c4a8109c123d143367f86ae7e6e06f830a665639d7d36f9f16
run_benchmark.py c92872bb07e4df93f3e671ce695f58a5fc1283737f775054b30da00cbc9c08c5
synthetic_conflict_manifest.json 2aff2cd83d430718c6be57ad89a3453c4c8d75a2bd4aafe3af8bdb60d99e15e1
synthetic_dataset_manifest.json 03544709fa49d5004a3c46251645efc6a9e0a12b80e97e84305d430df6b5cab2
SYNTHETIC_CONFLICT_SCENARIOS.md 4fa193ceb836406dc700b693211b7191b18d9faff388a48b8a491ed9c19b40c5
SYNTHETIC_DATASET_DOCUMENTATION.md 5e7cb38d4f80d827d97904ecf43a7c351334c6b8d08b4143c8fda3608bb525c2
SYNTHETIC_POLICY_REGISTER.md 8c4e85728bf65f1702cd40a0019231a3dbc728da9adfe6000633a87fc1767fba
validate.py 110c679ec29729044c98221a50d9a8ff73bdb6a9a9f9ff07a89a7b769508e915
validation.py 645abce4de8b2d140e03f0fa7f3bb11972b9dc6566596f6d3110faf1828bbe72
```
