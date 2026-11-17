# RAARA Phase 8E — Official Regulation Acquisition and Human Approval

Review date: 2026-11-13. **Implementation status: PASS WITH LIMITATIONS. Human approval status: NOT REVIEWED. Dataset readiness: EMPTY. Regression tests: PASS.**

Phase 8E audited the Phase 8A–8D reports, candidate PDFs, source/evidence records, and existing import/review workflow; searched official PES sources; updated discovery and review reports; and reran the requested regression groups. The search did **not** yield an accessible current B.Tech AIML academic-regulation PDF. No source was human-approved or imported, and no OpenAI call was made.

## Audit and official-source search

The Phase 8A–8D reports and workflows confirm that the separate Phase 8A registry is authoritative only after independent human source review. Phase 8C has three local PDF candidates and four exact-text evidence candidates. Their original checksums still match the inventory.

The most significant new discovery is the PES University [Public Self Disclosure index](https://pes.edu/naac/upload/UGC-PSD/Public%20Self%20Disclosure.pdf). It lists item 3.3 as “Statutes/Ordinances Pertaining to Academics/Examinations” and points to `http://www.pes.edu/UGC-PSD/3.3`. That public route could not be retrieved in this review. No underlying regulation file, checksum, effective date, issuer text, programme/campus/batch scope, or amendment chain could be reviewed. The missing file is recorded as `SRC-040`, a source lead, not as an acquired regulation.

The official PES FAQ currently gives a broad 80% attendance threshold and describes a 10-point relative/absolute grading system, but provides no target batch, campus, effective date, exceptions, calculation details, controlling regulation, or SGPA/CGPA formula. These remain discovery statements, not verified B.Tech AIML policy evidence. The [B.Tech page](https://pes.edu/btech/) identifies RR and EC campuses and the CSE (AI & ML) programme, but is not a regulation. The [AIML syllabus page](https://aiml.pes.edu/syllabus/) and the candidate curriculum identify programme/course material, not academic-rule coverage. PES University's [October 2024 examination-center article](https://news.pes.edu/11617/) concerns an MCA information session at RR; its high-level ISA/ESA and SGPA/CGPA content is out of B.Tech AIML scope.

No public, current B.Tech AIML regulations were located for attendance/ESA eligibility, ISA/ESA weighting, grading/SGPA/CGPA formulas, backlog/supplementary exams, revaluation, course registration, progression, or admission-batch amendments. Search coverage and limitations are itemized in [MISSING_REGULATIONS_REPORT.md](evaluation/held_out/MISSING_REGULATIONS_REPORT.md).

## Documents that require human review

| Candidate | Current classification/status | Human review needed before authoritative use |
|---|---|---|
| University Act PDF (`SRC-003`) | `EXTRACTION_BLOCKED`; 16-page image-only scan | Confirm official Gazette, amendments/current effect and policy relevance; if needed, obtain and manually validate readable text/OCR. No text evidence is available now. |
| PES University UGC Proforma (`SRC-004`) | `VERIFIED_OFFICIAL_CONTEXT_ONLY`; 2014 archival submission | Confirm exact provenance, historical cohorts and section-level institution boundaries; identify superseding rules. The p.17 CIA/SEE and grading passages remain historical context, not current rules. |
| AIML Curriculum 2025–26 (`SRC-014`) | `PENDING_HUMAN_AUTHORITY_REVIEW` | Confirm exact file linkage, campus applicability, 2025–29 cohort coverage, effective date and supersession. Curriculum pages identify programme/year/batch only. |
| Public Disclosure item 3.3 (`SRC-040`) | Official link listed; underlying document unavailable/unverified | Obtain the real file through an authorized source and then review its issuer, version, effective date, B.Tech AIML scope, campus, cohort and amendments. No file is present to approve or import. |
| Official FAQ (`SRC-002`) | Official discovery webpage, not a regulation | Confirm the 80%/grading statements against the binding regulation and target B.Tech AIML campus/batch before applying them. |

The detailed document-by-document checklist and evidence status is in [DOCUMENT_APPROVAL_STATUS.md](evaluation/held_out/DOCUMENT_APPROVAL_STATUS.md). The reviewer package is updated at [HUMAN_REVIEW_PACKAGE.md](evaluation/held_out/HUMAN_REVIEW_PACKAGE.md). **No human review was marked complete.** All four evidence records remain `NOT_REVIEWED`.

## Registry, evidence and readiness

- New public regulation files acquired: **0**.
- Phase 8A authoritative registry documents: **0**; no import performed.
- Existing exact page-level evidence candidates: **4**, all unchanged; human-approved evidence: **0**.
- Held-out questions: **0**; annotations/approvals: **0**.
- Updated inventory: **40 sources** — 14 official-verified discovery records, 11 official-unverified, 7 wrong-institution, 8 third-party references. These are source discovery counts, not approved authoritative documents.
- Readiness validator result: `EMPTY`; 0 imported documents, 0 questions, 0 approvals; Phase 8B/8C readiness false.

Updated artifacts: [source inventory JSON](evaluation/held_out/source_inventory.json), [source inventory Markdown](evaluation/held_out/SOURCE_INVENTORY.md), [policy evidence matrix](evaluation/held_out/POLICY_EVIDENCE_MATRIX.md), [document approval status](evaluation/held_out/DOCUMENT_APPROVAL_STATUS.md), [missing regulations report](evaluation/held_out/MISSING_REGULATIONS_REPORT.md), [readiness JSON](evaluation/datasets/held_out/readiness_report.json), and [readiness Markdown](evaluation/datasets/held_out/readiness_report.md).

## Test results and isolation

Tests ran with unique temporary SQLite, ChromaDB and upload paths, the Phase 8D SHA-verified local `cl100k_base` cache, and an empty `OPENAI_API_KEY`. The complete run used the normal approved local-socket execution mechanism required by the existing FastAPI tests.

- Phase 8C evidence plus Phase 8A/8B held-out workflow tests: **32 passed, 0 failed** (`33.07s`).
- Evaluation suite: **84 passed, 0 failed** (`114.95s`).
- Complete backend suite: **189 passed, 0 failed** (`142.29s`).
- Dataset readiness validator: completed successfully with `EMPTY` and the updated 40-source inventory.
- No live OpenAI calls; no production SQLite or ChromaDB writes; no production RAG, prompt, retrieval, benchmark, or frontend changes.

## Final classification

| Area | Result |
|---|---|
| Implementation/reporting | **PASS WITH LIMITATIONS** — search and reviewer support are documented; public regulations remain unavailable. |
| Human approval | **NOT REVIEWED** — zero approvals; four evidence records remain `NOT_REVIEWED`. |
| Dataset readiness | **EMPTY / NOT READY** — no imported official documents or held-out questions. |
| Regression tests | **PASS** — complete backend suite 189/189 passed. |

No held-out evaluation or annotation was started. The next required input is a human-approved, scope-appropriate source document, especially the actual item 3.3 statutes/ordinances file or the current B.Tech AIML regulations and batch history.
