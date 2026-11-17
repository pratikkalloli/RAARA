# RAARA Phase 8E — Live Acceptance Failure Repair Report

**Date:** 2026-11-15  
**Implementation status:** Targeted backend repairs made.  
**Regression status:** NOT RUN in this execution.  
**Live Gemini status:** NOT RUN.  
**Overall:** PARTIALLY COMPLETE; runtime verification is blocked by WSL access.

## Scope

This repair addresses the numerical-verification false positive, hierarchical-summary evidence loss and incomplete coverage disclosure, Gemini interpretation diagnostics, and evidence-aware abstention wording. Application architecture, frontend, model configuration, retrieval thresholds, authentication, citation verification rules, production stores, official evidence, and Phase 9A assets were preserved.

## Confirmed findings and repairs

### A. Numerical verification

**Confirmed code defect:** `FactualConsistencyVerifier` previously extracted every number from the answer, including numbered bullet markers and page locators, then required all those digits to appear in the model's numerical claims. This could reject otherwise supported numbered summaries. Dates, academic years, values, and ranges also pass through the same numeric-token completeness check.

**Repair:** The verifier now removes only leading numbered-list labels and explicit page/page-range locators before determining answer claim values. Academic-year/range values and factual quantities remain in the model-assisted review. Value, subject, unit, condition, evidence-ID validation, unsupported-claim withholding, and fail-closed completeness behavior remain in place. The verifier is still applied to whole-document summaries; it was not bypassed.

### B. Hierarchical summary evidence and coverage

**Confirmed code defect:** Intermediate batches returning `NOT_FOUND` or no usable cited child passage were silently skipped. The final stage could then summarize only the surviving nodes while the question still stated that the complete indexed document was supplied. Final citation coverage could also be narrower than the processed source chunks without a coverage disclosure.

**Repair:** Every intermediate response now passes through the existing `CitationVerifier`, and the final hierarchical response is checked against its intermediate passages before citation IDs are remapped to original pages. Reduction tracks original chunk IDs absent from verified intermediary citations, failed batches, sampling omissions, and final source chunks represented by validated citations. Failed batches cannot contribute text or citations to later summaries. If all reductions fail, the service returns a specific `NOT_FOUND` summary failure and coverage explanation. If other batches succeed, their summaries remain usable, but the answer is marked partial and identifies unrepresented chunks. Final prompts no longer claim complete indexed coverage when chunks are absent from usable intermediate summaries. Original document passage IDs and page metadata remain the final citation source.

### C. Gemini request interpretation

**Confirmed behavior and diagnostic gap:** The reported HTTP 503 message corresponds to `RequestInterpretation.model_validate_json()` rejecting the returned structure or route consistency. The old handler discarded the Pydantic error details, so the exact invalid/missing field from the earlier live response was not retained and cannot be reconstructed from the report.

**Repair:** The model schema now gives more explicit field and route descriptions, and interpreter instructions require all schema keys, explicit JSON nulls, and known field-length bounds. Pydantic validation remains strict, including route consistency. Validation logs now contain only exception class plus schema field locations/error types; they exclude model output, prompts, document text, and input values. The public error remains generic. Malformed JSON logs only its exception class. No deterministic phrase routing or automatic repair of inconsistent routes was added.

**Limitation:** This improves schema guidance and makes a future rejection diagnosable without leaking content. Because WSL/live Gemini is unavailable, it does not establish which exact field caused the earlier 503 or prove that Gemini now returns a valid interpretation.

### D. Evidence-aware abstention

**Confirmed code gap:** Abstention explanation quality depended on generated prose, even when the application already knew retrieval and provenance states. The prior live result showed that this could degrade into a generic explanation.

**Repair:** The application now prepends a short disclosure derived from the actual retrieval state and persisted metadata, covering no accessible documents, no relevant passages, unavailable indexed text, synthetic/unverified material, and source verification/issuance limitations. These disclosures do not assert that a policy is absent or supply a policy value. Responses remain `NOT_FOUND`, citation-free, and explicit about the available source’s inability to establish an official rule when metadata marks it synthetic or unverified.

## Files changed

### Application files

- `backend/app/services/factual_verifier.py`
- `backend/app/services/document_summarizer.py`
- `backend/app/services/generator.py`
- `backend/app/services/request_interpreter.py`

### Tests added or updated

- `backend/tests/test_factual_verifier.py` — numbered summary/page locators, academic-year range, and separate student-score claim.
- `backend/tests/test_document_summarizer.py` — failed intermediate batch with page traceability, all batches without usable citations, and final citations covering only a subset.
- `backend/tests/test_gemini_provider.py` — sanitized validation diagnostics, malformed output diagnostics, and explicit provenance disclosure assertions.

Eight new test functions were added; assertions were also extended in an existing abstention test. No frontend files were changed.

### Reports

- Created `RAARA_PHASE8E_REPAIR_REPORT.md`.
- Appended this follow-up to `RAARA_PHASE8E_LIVE_ACCEPTANCE_REPORT.md`. The original Phase 8E acceptance report findings were retained as historical results; this repair attempt is explicitly marked not rerun.

## Test and acceptance results

- Focused Python tests after these changes: **NOT RUN**.
- Complete backend test suite after these changes: **NOT RUN**.
- Prior baseline: 204 backend tests passed before this repair work; that result does not verify the current edits.
- Live Gemini repair cases: **NOT RUN**.
- Frontend tests/build: **NOT RUN**; no frontend files changed.
- No API key was read, displayed, or logged by this repair run. No Gemini or OpenAI calls were made.

The immediately preceding environment check showed that WSL could not launch. To follow the no-repeat instruction, no additional WSL command was attempted during this repair:

```text
Access is denied.
Error code: Wsl/E_ACCESSDENIED
```

Following the project instructions, no further WSL attempts and no unverified Windows Python test runs were made.

## Remaining limitations

- The exact Gemini interpretation field rejected in the historical 503 is unknown until a safe validation-field diagnostic is produced in a future run.
- Live Gemini output quality, the five-point whole-document result, abstention quality, numeric allocation/score distinction, and cross-user behavior after the code changes remain unverified.
- Citation identity checks establish that references map to retrieved passages; they do not prove semantic faithfulness.
- Numerical checking remains model-assisted. The deterministic layer checks completeness of factual numeric tokens and real evidence IDs; it is not a general proof of semantic correctness.
- If the document exceeds `max_chunks`, the existing spread-sampling limit remains; coverage is disclosed. This repair does not change that setting.

## Safe verification commands for Ubuntu

Run these from the project's Ubuntu terminal after confirming the WSL environment and tokenizer cache are available. They set isolated temporary storage and blank API keys. No live calls are part of the test commands.

```bash
cd /mnt/c/prompt_mini_proj/backend
export TIKTOKEN_CACHE_DIR="$HOME/.cache/tiktoken"
ISOLATION=$(mktemp -d /tmp/raara-phase8e-repair-XXXXXX)
export GEMINI_API_KEY=
export OPENAI_API_KEY=
export DATABASE_URL="sqlite:///$ISOLATION/backend.db"
export CHROMA_PERSIST_DIR="$ISOLATION/chroma"
export UPLOAD_DIR="$ISOLATION/uploads"
export JWT_SECRET_KEY="phase8e-test-only-$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
mkdir -p "$CHROMA_PERSIST_DIR" "$UPLOAD_DIR"
./.venv-wsl311/bin/python -m pytest -q \
  tests/test_factual_verifier.py \
  tests/test_document_summarizer.py \
  tests/test_gemini_provider.py \
  tests/test_chat_behaviors.py \
  tests/test_full_audit_regressions.py
./.venv-wsl311/bin/python -m pytest -q
```

Only after those tests pass, live acceptance can be run in a separate new isolated storage root using the securely configured Gemini credential. Do not use the test command environment for live requests.

## Data protection

No production SQLite database, ChromaDB collection, uploaded PDF, user account, official evidence registry/approval, or Phase 9A asset was accessed or modified. Changes were limited to the four backend services, three test modules, and the two Phase 8E reports identified above. No live Gemini/OpenAI call was made.

**Manual Ubuntu verification is required before this repair can be called regression-tested or live-accepted.**

## Targeted safety follow-up — 2026-11-15

### Changes

- `backend/app/services/factual_verifier.py`: page locators are now removed only when explicitly formatted as parenthesized/bracketed locators, abbreviated `p.`/`pp.` citations, or introduced by locator language such as “see page”. Factual counts such as “the PDF contains 13 pages” and “the document has 10 chapters” remain in the numerical completeness check. Numbered-list markers and dates, academic years, values, units, percentages, and ranges remain checked.
- `backend/app/services/document_summarizer.py`: intermediate answers with citation-integrity issues are discarded as a whole batch, even if another citation in the answer was valid. Intermediate summaries without such citation errors are explicitly tagged `NOT_VERIFIED` for semantic faithfulness. Hierarchical output carries a visible warning and coverage limitation and is downgraded to `PARTIALLY_SUPPORTED` when otherwise supported. The code does not claim that citation identity proves sentence-level support.
- `backend/tests/test_factual_verifier.py`: added regressions for factual page/chapter counts and explicitly formatted page citations/ranges.
- `backend/tests/test_document_summarizer.py`: added a mixed supported/unsupported intermediate-summary case with valid citations; asserts the result is not presented as fully supported, the semantic limitation is disclosed, and final citations map to original passages.
- `RAARA_PHASE8E_COMPLETE_VERIFICATION_REPORT.md`: corrected attribution of backend test outcomes and documented these follow-up limitations.

Three focused regression tests were added. No prompt, retrieval setting, provider/model, authorization rule, citation identity rule, or production data path was changed.

### Test results and current verification status

The user supplied these Ubuntu results for the Phase 8E repair before this targeted follow-up:

- Focused suite: **72 passed in 46.90s**.
- Full backend suite: **371 passed, 1 failed in 194.48s**.
- Sole failure: `evaluation/tests/test_project_authored_policies.py::test_phase9a_assets_remain_byte_for_byte_unchanged`.

These supplied outcomes do not include the three tests added in this follow-up. Codex attempted the requested focused run once through WSL, but WSL did not start:

```text
Access is denied.
Error code: Wsl/E_ACCESSDENIED
```

Therefore the focused tests for this follow-up, the full suite, and evaluation tests are **NOT RUN by Codex**. No alternative Python runtime was used. No live Gemini/OpenAI calls were made. The Phase 9A mismatch remains unresolved and the expected fingerprint, test, and assets were not changed.

### Remaining limitation

The summarizer still cannot prove semantic entailment for intermediate prose using citation identity validation alone. It now makes that explicit in the response and status rather than treating such text as fully supported. Live Gemini acceptance and backend regression for this follow-up remain outstanding.

Protected Phase 9A files, production SQLite/ChromaDB/uploads, official approvals, and Phase 9A assets were not modified.

## Undefined disclosure-helper regression fix — 2026-11-15

### Change

`backend/app/services/document_summarizer.py` called `_prepend_once` when adding the hierarchical semantic-faithfulness disclosure, but that helper was not defined in this module. Replaced the call with a local `casefold()` containment check followed by string concatenation. The disclosure remains present for hierarchical summaries, is not duplicated if already present, and the existing downgrade to `PARTIALLY_SUPPORTED` is unchanged. No dependency or shared helper was added.

The existing regression `test_mixed_intermediate_summary_is_marked_unverified_and_never_reported_fully_supported` already verifies the disclosure, `NOT_VERIFIED` faithfulness, original passage citations, and non-`SUPPORTED` status, so no additional test was needed solely for the helper replacement.

### Test result

Attempted the focused suite once from Windows using the approved WSL Python environment and isolated temporary storage. The command was:

```powershell
wsl.exe -e bash -lc '<isolated environment setup>; cd /mnt/c/prompt_mini_proj/backend; ./.venv-wsl311/bin/python -m pytest -v tests/test_factual_verifier.py tests/test_document_summarizer.py tests/test_gemini_provider.py tests/test_chat_behaviors.py tests/test_full_audit_regressions.py'
```

WSL failed before starting Bash or Python:

```text
Access is denied.
Error code: Wsl/E_ACCESSDENIED
```

Focused tests: **NOT RUN / UNVERIFIED**. No pytest pass claim is made. No alternative Python runtime or live model/API call was used. The user-reported preceding run (70 passed, 5 failed due to this `NameError`) remains historical and is not a result for the fix.

Only `backend/app/services/document_summarizer.py` and this report were changed for this minimal repair. Phase 9A assets, fingerprints, expected hashes, evaluation data, production databases, ChromaDB, and uploads remain untouched.


## Source review note

The edited service and test blocks were reread after changes. The project directory has no Git metadata available to this execution, so a canonical `git diff` could not be produced; the changed-file list above is based on the files edited directly. Python syntax and tests remain unverified until the documented Ubuntu commands are run.
