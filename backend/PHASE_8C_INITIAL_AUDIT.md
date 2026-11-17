# RAARA Phase 8C — Initial Repository Audit

Audit date: 2026-11-13  
Project: `C:\prompt_mini_proj`  
Backend environment: `backend\.venv311` (Python 3.11.9)  
Scope: initial audit and decision package only. No application implementation, evidence, authority status, dataset, production storage, or benchmark output was changed for this audit. This report is a new audit artifact requested by the milestone instructions.

## Executive finding

The project has reusable document provenance, PDF extraction, held-out annotation, source-bound evidence validation, synthetic evaluation, and dataset-readiness infrastructure. The real-source registry is empty. Three original PES-hosted candidate PDFs are present locally; none is verified as an authoritative current B.Tech CSE (AI & ML) regulation. Four page-level evidence records are structurally validated but remain `NOT_REVIEWED`. Dataset readiness is `EMPTY`.

The highest-priority gaps are obtaining an applicable official rulebook and amendments from an authorized source, establishing scope/version for each document, completing human authority review, and providing local OCR for the scanned Act if it is to be extracted. The Phase 9A synthetic corpus is explicitly segregated and must not be used as official evidence.

## Existing infrastructure

### Provenance and document intake

- Phase 8A schemas are in `evaluation/schemas/held_out.py`; the registry is `evaluation/datasets/held_out/documents.json`.
- `evaluation/heldout.py` validates registry provenance, SHA-256, PDF readability and page count, unique IDs/checksums, root-contained paths, supersession references, evidence-to-page references, annotation completeness, and exact development-question overlap.
- `evaluation/scripts/import_heldout_document.py` copies original PDF bytes, computes the checksum and page count, rejects duplicates/path overwrite, and records an official authority claim as `pending`. It does not itself prove the publisher's authority or applicability.
- Annotation and review CLIs are `evaluation/scripts/annotate_heldout.py` and `evaluation/scripts/review_heldout_annotation.py`. The review CLI supports independent annotation review; there is no equivalent interactive human approval CLI for the separate Phase 8C evidence-candidate JSONL.

### Evidence extraction and validation

- The production PDF processor `app/services/document_processor.py` uses PyMuPDF and provides one-based page numbering and heuristic section extraction.
- `evaluation/schemas/policy_evidence.py` provides the requested page-level fields: source/document ID, exact text, page, section/subsection, version, effective date, applicability, authority status, extraction method/confidence, reviewer status, URL, checksum, and supersession status.
- `evaluation/policy_evidence.py` verifies source identity, URL/path, checksum, page range, exact normalized text on the declared page, duplicate IDs/spans, and rejects OCR candidates unless a reviewed OCR artifact exists. `authoritative_policy_evidence()` fails closed unless authority is `VERIFIED_AUTHORITATIVE`, review is `HUMAN_APPROVED`, and supersession status is `CURRENT`.
- Existing focused tests cover provenance, page text, checksums, duplicate evidence, OCR evidence rejection, source authority gating, and synthetic fixture labeling.

### Evaluation and synthetic separation

- Evaluation indexing is in `evaluation/retrieval/indexing.py` and uses deterministic local TF/hash embeddings for Phase 9A; it is separate from production indexing.
- `evaluation/synthetic_project_data/` contains 10 current-model synthetic PDFs and sources, two separate historical conflict fixtures, and 50 synthetic questions (36 development, 11 synthetic held-out, 3 conflict). Manifest and documents mark `SYNTHETIC_PROJECT_DATA`, `PROJECT_AUTHORED`, and `is_official_university_policy: false`.
- Phase 9A has validation and tests for source separation and exact evidence references. It is not a PES policy corpus and cannot fill official-source gaps.

## Current official-source inventory and registry

- Discovery inventory: 40 records in `evaluation/held_out/source_inventory.json`; it mixes official source webpages/PDF leads, unverified official-hosted leads, wrong-institution/scope items, and third-party references. A discovery record is not an imported or authoritative policy document.
- Current inventory summary: 14 records classified `OFFICIAL_VERIFIED`, 11 `OFFICIAL_UNVERIFIED`, 7 wrong-institution records, and 8 third-party records. These are discovery-level counts, not authority approvals. The inventory currently tracks three downloaded local PDFs; two are identified as official-source documents, while the AIML candidate remains pending exact-file/source and applicability review.
- Phase 8A registry `evaluation/datasets/held_out/documents.json`: `documents: []` (zero imported genuine documents).
- `evaluation/datasets/held_out/questions.jsonl`: empty (zero genuine held-out questions).
- Current generated readiness report: 0 imported documents, 0 independently verified official documents, 0 valid questions, and `EMPTY`.
- Four structured evidence candidates are present in `evaluation/held_out/evidence_candidates.jsonl`; all four are `NOT_REVIEWED`. They are candidate excerpts, not approved policy evidence.
- No current B.Tech AIML academic regulation was found in the existing inventory. Human authority approvals and authoritative evidence records: zero.

## Local candidate PDF inspection

The actual SHA-256 was recalculated and matches the inventory for each file.

| Candidate | Original URL | SHA-256 | Pages / extractable text | Existing disposition |
|---|---|---|---:|---|
| The PES University Act, 2012 (`THE_PES_UNIVERSITY_ACT.pdf`) | `https://pes.edu/wp-content/uploads/2025/09/THE_PES_UNIVERSITY_ACT.pdf` | `1d66332a097f0b2033fffb8398df6328cd1641cd6a9d75e0f0fedf9656948038` | 16 / 0 | `EXTRACTION_BLOCKED`; image-only scan. |
| PES University Proforma to UGC (`PES_University_Profroma_To_UGC.pdf`) | `https://pes.edu/wp-content/uploads/2025/09/PES_University_Profroma_To_UGC.pdf` | `3558ac4222cea3a770a74dedc53510a74318b55842878ad9bf9ee1e7b9d01b06` | 475 / 475 | `VERIFIED_OFFICIAL_CONTEXT_ONLY`; archival 2014 UGC submission with mixed historical references, not a current AIML rulebook. |
| CSE (AI & ML) Curriculum 2025–26 (`AIML-Curriculum-2025.pdf`) | `https://aiml.pes.edu/wp-content/uploads/2025/06/AIML-Curriculum-2025.pdf` | `c9fae00eb4c9e7ba6d0adb0686fe681a709119c72ace361dee707c0c58ec1c4f` | 118 / 118 | `PENDING_HUMAN_AUTHORITY_REVIEW`; PDF identifies 2025–26 curriculum and 2025–29 batch, but exact live download linkage, campus scope and regulatory authority need review. |

The existing [PDF inspection report](evaluation/held_out/PDF_INSPECTION_REPORT.md) records extraction details, representative page rendering, heuristic section headings and limitations. PyMuPDF can extract page-level text from the two text-bearing PDFs. It cannot extract the Act scan's content.

## External official-source findings

Read-only review of public PES sources on 2026-11-13 found:

- The [PES AIML syllabus page](https://aiml.pes.edu/syllabus/) displays batch-specific curriculum content, including 2025 and 2026. Its “Download Curriculum” link resolves to Google Drive. This is a curriculum discovery source, not an examination or progression rulebook; it does not establish that the local PDF is the exact current download or establish campus scope.
- The [PES B.Tech page](https://pes.edu/btech/) names Ring Road and Electronic City as B.Tech campuses and describes programmes. It is not an academic regulation.
- The [PES FAQ](https://pes.edu/faqs/) publicly states 80% attendance for exam eligibility and a 10-point grading system. It is prospective-student FAQ material and does not identify governing regulation/version, B.Tech AIML batch, campus applicability, effective date, exceptions, or SGPA/CGPA calculation method. It is discovery context only, not controlling evidence.
- The [PES academic calendar page](https://pes.edu/calendar/) lists academic-year calendar links, including 2026–27 and 2025–26. The listed dates/calendars do not substitute for rules on assessment, registration, progression, or eligibility; each target file still requires scope and content review.
- The [PES Important Information page](https://pes.edu/important/) lists the UGC Proforma and PES University Act. The [Public Self Disclosure index](https://pes.edu/naac/upload/UGC-PSD/Public%20Self%20Disclosure.pdf) identifies item 3.3 for academic/examination statutes and ordinances. Its linked [item 3.3 route](http://www.pes.edu/UGC-PSD/3.3) could not be retrieved in the public review; no underlying file bytes or provenance were available.
- The [PES October 2024 examination-centre news item](https://news.pes.edu/11617/) discusses ISA/ESA and SGPA/CGPA in an MCA information-session context; it is not B.Tech AIML regulation evidence.
- A web search index exposes text from the official-hosted Act PDF, but that does not replace extraction and page-by-page validation of the local scanned file. No OCR-derived evidence was created or entered.

No public, applicable current B.Tech AIML rulebook or amendments were located in the reviewed sources. This is a discovery gap, not evidence that such rules do not exist.

## Existing extraction and OCR capability

- Local text extraction: PyMuPDF (`fitz`) is installed and succeeded on all 475 pages of the UGC Proforma and all 118 pages of the AIML curriculum.
- The Act PDF opens as a 16-page image-only scan, but `extract_pdf_pages()` raises `EmptyPDFError`; zero text pages were extracted.
- Local OCR check: no `tesseract` executable; Python `pytesseract`, `easyocr`, `paddleocr`, and `ocrmypdf` modules are unavailable. The existing OCR report also records Windows OCR unavailable.
- No OCR has been run, no OCR page text exists, and there are zero Act evidence records. The original PDF must remain unchanged if a future reviewed OCR workflow is approved.

## Missing implementation and evidence requirements

1. Obtain current authoritative B.Tech CSE (AI & ML) academic regulations and amendments, plus applicability to Ring Road/Electronic City and admission batches.
2. Obtain controlling source documents for attendance/ESA eligibility; ISA/ESA; grading and SGPA/CGPA; backlog/supplementary; revaluation/grievances; registration/withdrawal; progression/promotion; credits; and batch-specific changes.
3. Record issuing authority, publication/effective dates, version, superseded-document links and programme/campus/batch scope for actual source documents.
4. Resolve the exact provenance and scope of the current curriculum file with a human reviewer; do not use a curriculum as a substitute for rules it does not state.
5. Supply/approve a local OCR tool and page-aligned review workflow before attempting Act evidence extraction.
6. Complete independent human decisions for every document/evidence record before authoritative selection; the current CLI reviews question annotations but not `PolicyEvidenceRecord` decisions.
7. Keep discovery inventory separate from the Phase 8A registry and maintain pending/unverified items outside authoritative retrieval/evaluation.

## Risks and blockers requiring human decisions

- Exact authority, applicability, date/version and supersession cannot be inferred from hosting domain, search indexing, branding or a curriculum label alone.
- Current FAQ attendance/grading statements are too broad to establish the controlling rule for a specific student cohort.
- The 2014 Proforma may describe historical or prospective schemes and includes institution-specific references; it cannot be generalized to current AIML.
- The curriculum's currently displayed Google Drive link does not independently prove the exact local PDF file linkage; human confirmation is required.
- The Act is not locally searchable without OCR. OCR inaccuracies could affect exact quotations, subsections, numbers and exceptions.
- No approved official documents means no genuine held-out questions or annotation should be created yet. The official dataset cannot be declared ready.

## Reusable sequence proposed for later approval

1. Receive official PDFs or authorized links and preserve original bytes.
2. Add provenance/discovery records without conflating discovery with authority approval; compute hashes and validate PDFs.
3. Confirm issuer, programme, campus, batches, dates, version and supersession with an independent human reviewer.
4. Use PyMuPDF for text PDFs; only with approved local tooling, create separate page-aligned OCR text for scans and manually verify it.
5. Extract verbatim page evidence as `NOT_REVIEWED`; validate each span against the original PDF and preserve exact page references.
6. Compare only sources with overlapping applicability, documenting both sides of unresolved conflicts.
7. Have humans approve/reject documents and evidence; only then use the existing Phase 8A import/review paths.
8. Regenerate readiness and run evidence, held-out, evaluation and full backend validation with isolated storage. Keep Phase 9A synthetic assets and all production stores untouched.

## Prior recorded validation (not rerun for this initial audit)

The latest recorded Phase 9A report states **198 backend tests passed, 0 failed** on final assets. The Phase 8C report records a later full suite result of **198 passed, 0 failed**, plus passing held-out and Phase 9A validators. These are prior recorded results; this audit did not run pytest or change tests.

## Proposed files for a future approved implementation

No implementation files are changed in this audit. If the owner approves the next step, likely files would be:

- Update: `evaluation/held_out/source_inventory.json` and `.md`, `POLICY_EVIDENCE_MATRIX.md`, `HUMAN_AUTHORITY_REVIEW.md`, `OCR_REPORT.md`, `CONFLICT_AND_VERSION_ANALYSIS.md`, `MISSING_REGULATIONS_REPORT.md`, `evaluation/datasets/held_out/readiness_report.json` and `.md`, and `evaluation/README.md`.
- Possibly add/update: a human evidence-review workflow and its tests, only if approved scope requires the tool; OCR artifacts/tests only after an approved local OCR dependency and human review procedure exist.
- Create/update: `PHASE_8C_REPORT.md` only for a separately approved implementation/research iteration; preserve prior milestone reports and benchmark artifacts.

The current audit file is the only file created by this task. No test run, source import, policy evidence change, approval, dataset annotation, production RAG/configuration change, API call, or database/vector-store write was performed.
