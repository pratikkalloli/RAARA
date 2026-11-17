# RAARA Phase 8C — Document Authority Review and Evidence Extraction

**Result: PASS WITH LIMITATIONS** for the review, extraction-validation workflow, and reports. **The authoritative evidence corpus is not ready for human annotation.**

Review date: 2026-11-12. Scope: PES University Bengaluru B.Tech CSE (AI & ML), Ring Road and Electronic City, with historical/batch scope considered. No production RAG source, prompt, database, or ChromaDB collection was changed.

## Documents inspected and classifications

| Candidate | SHA-256 verified | Classification | Disposition |
|---|---|---|---|
| `THE_PES_UNIVERSITY_ACT.pdf` (16 pages) | `1d66332a097f0b2033fffb8398df6328cd1641cd6a9d75e0f0fedf9656948038` | `EXTRACTION_BLOCKED` | Official-source linked scan; no extractable text and no available local OCR. No evidence extracted. |
| `PES_University_Profroma_To_UGC.pdf` (475 pages) | `3558ac4222cea3a770a74dedc53510a74318b55842878ad9bf9ee1e7b9d01b06` | `VERIFIED_OFFICIAL_CONTEXT_ONLY` | 2014 UGC submission; mixed institution references; not current AIML regulations. |
| `AIML-Curriculum-2025.pdf` (118 pages) | `c9fae00eb4c9e7ba6d0adb0686fe681a709119c72ace361dee707c0c58ec1c4f` | `PENDING_HUMAN_AUTHORITY_REVIEW` | Identifies 2025-26 curriculum and 2025-29 AIML batch; exact file linkage and campus applicability need human review. A curriculum does not establish attendance/examination regulations. |

Counts across the three candidates: **0 VERIFIED_AUTHORITATIVE**, **1 VERIFIED_OFFICIAL_CONTEXT_ONLY**, **1 PENDING_HUMAN_AUTHORITY_REVIEW**, **1 EXTRACTION_BLOCKED**. No candidate was rejected as a whole; wrong-scope material within the UGC Proforma was excluded from University policy attribution. The 38-record inventory contains 7 wrong-institution and 8 third-party references, which remain excluded from authoritative evidence.

## Evidence and policy coverage

Four page-level evidence candidates were extracted and validated against exact original PDF hashes, page bounds, and normalized verbatim page text. Two identify historical UGC Proforma statements on page 17; two identify the curriculum/batch on pages 1 and 3. All are marked `NOT_REVIEWED`; **0 are authoritative evidence records**. None proves a current policy rule.

For attendance/eligibility, ISA/ESA, current grading and SGPA/CGPA, backlog/supplementary exams, revaluation, course registration, progression, credit rules, current calendar applicability, and extracted governance provisions, the matrix records **NO VERIFIED EVIDENCE FOUND** for the requested scope. Official discovery sources include the [PES University FAQ](https://pes.edu/faqs/), [B.Tech page](https://pes.edu/btech/), [academic calendar page](https://pes.edu/calendar/), [important information page](https://pes.edu/important/), and [AI & ML syllabus page](https://aiml.pes.edu/syllabus/). They do not provide a scope-complete, verified current regulation set in the inspected material.

## OCR, versions, and conflicts

The Act OCR workflow is **BLOCKED**: Tesseract/OCRmyPDF and Python OCR packages were unavailable, and Windows local OCR was unavailable. No external OCR was used; the original PDF is preserved. No OCR quality review was possible.

No overlapping verified current policy pair was found: **0 conflicts identified, 0 resolved, 0 evidenced unresolved**. That is not proof that unreviewed documents contain no conflicts. The FAQ's 80% language and the 75% PU College material concern different/unclear scopes; third-party claims were excluded. The 2014 Proforma and 2025-26 curriculum have different purposes and do not conflict as operative rules.

## Human review and registry

Human approvals still required: **3 candidate document reviews**, including resolution of AIML PDF linkage/campus applicability and OCR for the Act if its text is needed. The Phase 8A registry remains at **0 documents**, and the held-out question set remains **0 questions**. No human review was marked complete. The dataset readiness remains **EMPTY** and Phase 8B/8C annotation readiness is **NO**.

## Validation and test results

The evidence validator checks source inventory membership, authority classification, URL/path agreement, root containment, original SHA-256, PDF page range, exact page text, duplicate IDs/mappings, and refuses OCR-derived evidence without a separately reviewed OCR artifact. Authoritative selection fails closed unless a record is `VERIFIED_AUTHORITATIVE`, `HUMAN_APPROVED`, and `CURRENT`.

Phase 8C evidence and existing held-out workflow tests: **32 passed, 0 failed**. The readiness validator completed and reported `EMPTY`, 0 imported documents, 0 questions, 0 approvals, and 38 discovered sources. The full backend command collected **189 tests** but did not complete: existing evaluation tests attempted to download the missing `cl100k_base.tiktoken` encoding from `openaipublic.blob.core.windows.net`; network name resolution was unavailable. The focused reproduction yielded **1 passed, 3 failed**, with all three failures caused by that missing tokenizer cache/network dependency, not by policy-evidence validation. The full run was interrupted after it stalled while proceeding through the remaining backend tests; therefore a full-suite pass is **NOT VERIFIED**. No live OpenAI request was made.

The tests include synthetic PDF fixtures visibly labeled “SYNTHETIC TEST DOCUMENT — NOT OFFICIAL POLICY”; no synthetic records enter the genuine held-out inventory or registry. Readiness validation is also run through the existing Phase 8A validator.

## Isolation and limitations

- No production RAG logic, prompt, retrieval setting, SQLite database, ChromaDB, or live OpenAI API was used or changed.
- No held-out questions or expected answers were generated.
- Public calendar documents behind Google Drive/Docs loading or sign-in and official CSE downloads that timed out remain uninspected; no access-control bypass was attempted.
- Semantic correctness of any generated answer was not evaluated.
- Current academic regulations, campus mapping, effective dates, amendments, and supersession remain unverified.

**Decision:** PASS WITH LIMITATIONS for Phase 8C workflow and evidence preparation. The authoritative corpus is **not ready** for held-out question generation or annotation. Human authority review and acquisition of current, scope-specific regulations are required first.

## Phase 8C resumption review (2026-11-13)

**Result: PASS WITH LIMITATIONS.** This resumption rechecked official public discovery sources and the existing page-level evidence; it did not establish a current B.Tech AIML academic-regulation corpus. No source was imported, no evidence status changed, and no human approval was recorded.

### Official-source discovery and authority findings

- The [PES AIML syllabus page](https://aiml.pes.edu/syllabus/) currently lists Batch 2025 and Batch 2026 curriculum content. Its “Download Curriculum” link resolves to Google Drive. This confirms a live programme-level curriculum listing, but does not establish the exact provenance of the locally held `AIML-Curriculum-2025.pdf`, academic-rule applicability, campus, effective date, or authority for attendance/examination policy. `SRC-014` remains `PENDING_HUMAN_AUTHORITY_REVIEW`; its four candidate-related records remain `NOT_REVIEWED`.
- The [PES Important Information page](https://pes.edu/important/) lists its UGC Proforma and PES University Act. Neither is a current B.Tech AIML academic rulebook. The item 3.3 target remains inaccessible at [the disclosed route](http://www.pes.edu/UGC-PSD/3.3); it is treated as unavailable, not as proof that no rule exists.
- The [PES FAQ](https://pes.edu/faqs/) is prospective-student FAQ material. Any broad attendance or grading statement remains discovery context without the policy version, effective date, governing text, B.Tech AIML batch scope, or complete exceptions; it is not elevated to verified evidence.
- No additional regulation PDF or directly university-received file was acquired in this resumption.

### Counts and state

| Measure | Result |
|---|---:|
| Existing candidate PDFs inspected | 3 |
| Newly acquired documents | 0 |
| Verified authoritative B.Tech AIML policy documents | 0 |
| Official context-only documents | 1 (archival UGC Proforma) |
| Pending human authority review | 1 (AIML curriculum) |
| Extraction-blocked | 1 (University Act scan) |
| Page-level evidence candidates | 4; all `NOT_REVIEWED` |
| Human approvals / authoritative imports | 0 / 0 |
| Current-policy conflicts evidenced | 0; unreviewed/unavailable sources prevent a completeness claim |
| Held-out questions / readiness | 0 / EMPTY |

The three candidate classifications are preserved: Act `EXTRACTION_BLOCKED`; UGC Proforma `VERIFIED_OFFICIAL_CONTEXT_ONLY`; AIML curriculum `PENDING_HUMAN_AUTHORITY_REVIEW`. Synthetic Phase 9A data remains isolated from the official-source registry and evidence matrix.

### OCR and regression

PyMuPDF confirmed the Act remains an image-only PDF with zero text-extractable pages. Local checks found no `tesseract` executable and no Python `pytesseract`, `easyocr`, `paddleocr`, or `ocrmypdf` module; no OCR was performed and no OCR text or Act evidence was created. The PDF remains byte-for-byte unchanged.

Regression and validators were run for this resumption; actual results are recorded in the closing test section below after execution. Isolated test storage was used. No production SQLite or ChromaDB writes, live OpenAI calls, synthetic-to-official mixing, prompt/retrieval changes, or human-approval changes were made.

### Outstanding human decisions

A qualified university authority/reviewer must confirm the AIML curriculum’s exact source-file linkage, issuing authority, campus and admission-batch applicability, effective date/version and supersession history, and assess each of the four quoted candidates. A separate official rule document is required for every policy subject in the matrix. The Act extraction blocker requires a future local OCR tool plus page-by-page human comparison; no machine extraction alone constitutes approval.

## Resumption validation results

- Full backend suite: **198 passed, 0 failed**, completed in 68.48 seconds using `backend/.venv311` and Python 3.11.9. Mocked/no live OpenAI calls; `OPENAI_API_KEY` was empty. The first sandboxed execution stalled at a local FastAPI `TestClient` request; the same full command completed when run with local loopback permission. No test was skipped or weakened.
- Held-out readiness validator: **PASS**; 0 imported genuine documents, 0 verified official policy documents, 0 valid questions, readiness `EMPTY`; 40 discovery source records and 3 downloaded PDFs (2 officially verified at the document-source level; none current authoritative B.Tech AIML policy).
- Phase 9A synthetic validator: **PASS**; 50 items, 10 primary synthetic documents, 2 separate conflict fixtures, 86 evidence references; official registry modification `false`, production storage accessed `false`.
- Evidence candidate states: **4 `NOT_REVIEWED`**, 0 approved. The Phase 8A registry JSON contains `documents: []`; held-out questions JSONL is empty.
- Candidate PDF SHA-256 checks were re-run and match the recorded hashes for all 3 local PDFs. No document bytes changed.
- No application source, production database, or production ChromaDB content was intentionally written by this review. Validators report no production storage access. Evaluation fixtures and backend tests use isolated temporary storage.

### Final classification

**PASS WITH LIMITATIONS** for the Phase 8C audit/resumption, public-source inventory update, evidence review, validation and regression testing. **Official corpus readiness: NOT READY; dataset readiness: EMPTY.** No authoritative current B.Tech AIML regulation was established; no human approval was recorded; no held-out evaluation or annotation may proceed on the basis of this review. Phase 8D/8E work is not started.
