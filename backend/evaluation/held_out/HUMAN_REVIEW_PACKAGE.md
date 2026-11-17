# RAARA Phase 8D — Human authority review package

**Purpose:** provide document facts and review questions to a human reviewer. This package is not an approval record. No `reviewer_status` or source classification has been changed by this package; every evidence candidate remains `NOT_REVIEWED`. Do not import a candidate into the Phase 8A registry without a human decision through the established workflow.

Scope requested: PES University Bengaluru B.Tech CSE (AI & ML), Ring Road and Electronic City, current applicable policies and relevant historical versions. “Unknown” means the supplied document or available provenance does not establish the answer.

## Candidate 1 — The PES University Act, 2012 (`SRC-003`)

| Field | Reviewed information |
|---|---|
| File / pages | `documents/university_governance/THE_PES_UNIVERSITY_ACT.pdf`; 16 pages |
| SHA-256 | `1d66332a097f0b2033fffb8398df6328cd1641cd6a9d75e0f0fedf9656948038` |
| Original source URL | <https://pes.edu/wp-content/uploads/2025/09/THE_PES_UNIVERSITY_ACT.pdf> (listed from PES University's Important Information source chain) |
| Issuing authority | Candidate's rendered title page identifies the Karnataka Gazette / Karnataka Act No. 16 of 2013; attribution is to the Karnataka State Legislature, pending human confirmation. PDF metadata names “admin” and is not authority proof. |
| Programme applicability | General institutional governance instrument; whether any provision establishes a B.Tech AIML academic rule is not determined. |
| Campus applicability | Whether/which provisions cover Ring Road and Electronic City is not assessed. |
| Admission batch | Not batch-specific in available metadata; applicability to particular cohorts is not assessed. |
| Effective date / version | Title identifies PES University Act 2012; the rendered gazette first page identifies Karnataka Act No. 16 of 2013. Amendment and current-effect status need legal/source review. PDF creation metadata: 2013-12-13. |
| Exact evidence passages | **None extracted.** PyMuPDF found zero text on all 16 pages. Do not cite OCR or infer statutory text from the title page. |
| Current classification | `EXTRACTION_BLOCKED` |
| Recommended classification | **Recommendation only:** retain `EXTRACTION_BLOCKED` until a reviewed local OCR or accessible text source is produced. The reviewer may separately confirm official provenance and scope. |

**Questions for reviewer:** Is this the current official Act and correct Gazette copy? What amendments or replacement instruments apply? Which provisions, if any, govern B.Tech academic policies or both campuses? Is OCR needed for this review, and can a reliable original text be obtained? If OCR is later used, compare page-aligned output against rendered pages.

## Candidate 2 — PES University Proforma to UGC (`SRC-004`)

| Field | Reviewed information |
|---|---|
| File / pages | `documents/university_governance/PES_University_Profroma_To_UGC.pdf`; 475 pages |
| SHA-256 | `3558ac4222cea3a770a74dedc53510a74318b55842878ad9bf9ee1e7b9d01b06` |
| Original source URL | <https://pes.edu/wp-content/uploads/2025/09/PES_University_Profroma_To_UGC.pdf> (listed from PES University's Important Information source chain) |
| Issuing authority | PES University submission/proforma addressed to the University Grants Commission (UGC); distinguish the submitting institution from the recipient. Human reviewer should confirm provenance and status. |
| Programme applicability | Page 17 contains general prospective university statements but does not establish current B.Tech AIML scope. Later pages include separately headed PES Institute of Technology material; do not attribute those sections to PES University. |
| Campus applicability | Not established for Ring Road or Electronic City. |
| Admission batch | Not specified for current AIML batches. |
| Effective date / version | PDF metadata creation/modification date 2014-03-18; no operative effective date or supersession chain established. |
| Exact evidence passage — PDF p.17, section 5.7 | “The PES university will adopt Continuous In-semester Assessment (CIA) and Semester End Examination (SEE) Scheme for both theory and practical courses.” |
| Exact evidence passage — PDF p.17, section 5.8 | “The performance evaluation shall be done under a Letter Grading System obtained following the Relative Grading System and Absolute Grading System.” |
| Current classification | `VERIFIED_OFFICIAL_CONTEXT_ONLY` |
| Recommended classification | **Recommendation only:** retain `VERIFIED_OFFICIAL_CONTEXT_ONLY` for historical context; do not use these prospective 2014 statements as current B.Tech AIML rules without a later authoritative regulation and scope confirmation. |

**Questions for reviewer:** Does PES University's official source chain establish the exact file and submission date? What cohort/programmes do sections 5.7–5.8 describe? Did these proposals take effect, and which later regulations superseded or amended them? Where does the document switch to PES Institute of Technology, and are all extracted passages correctly scoped? May any passage support a historical statement only?

## Candidate 3 — CSE (AI & ML) Curriculum 2025–26 (`SRC-014`)

| Field | Reviewed information |
|---|---|
| File / pages | `documents/academic_regulations/AIML-Curriculum-2025.pdf`; 118 pages |
| SHA-256 | `c9fae00eb4c9e7ba6d0adb0686fe681a709119c72ace361dee707c0c58ec1c4f` |
| Original source URL | <https://aiml.pes.edu/wp-content/uploads/2025/06/AIML-Curriculum-2025.pdf>; the department syllabus page's download link resolved to Google Drive rather than this exact URL. |
| Issuing authority | PES University is indicated by PDF branding and metadata; exact file linkage/issuance should be confirmed by a reviewer. |
| Programme applicability | Page 3 names B.Tech in Computer Science and Engineering (Artificial Intelligence and Machine Learning). This supports programme identification, not unrelated regulatory rules. |
| Campus applicability | Unknown; the local PDF does not establish Ring Road vs. Electronic City applicability in reviewed material. |
| Admission batch | Page 3 identifies `2025-29 BATCH` for the displayed semesters. Applicability beyond that batch is not established. |
| Effective date / version | Cover says `CURRICULUM – 2025 – 26`; PDF metadata created/modified 2025-06-01. Effective date and supersession status are unknown. |
| Exact evidence passage — PDF p.1, cover | `PES UNIVERSITY                                                                                                                     CURRICULUM – 2025 – 26` |
| Exact evidence passage — PDF p.3 | `B.TECH IN COMPUTER SCIENCE AND ENGINEERING (ARTIFICIAL INTELLIGENCE AND MACHINE LEARNING)` / `I SEMESTER ( 2025-29 BATCH)` |
| Current classification | `PENDING_HUMAN_AUTHORITY_REVIEW` |
| Recommended classification | **Recommendation only:** keep `PENDING_HUMAN_AUTHORITY_REVIEW` until the exact PDF/source relationship and campus applicability are confirmed. If verified, it may support curriculum and batch identification; do not treat it as an attendance, grading, promotion, or examination regulation unless an explicit provision is located and reviewed. |

**Questions for reviewer:** Is this exact binary the document linked by the official AI/ML syllabus page? Does it apply at both campuses or only a particular campus? Does the 2025-29 batch label cover all campus entrants? Is there a separate scheme/regulations document? What effective date, amendment history, or later curriculum supersedes it?

## Evidence status and decision record

The four machine-validated evidence records are in `evidence_candidates.jsonl`; their original hashes, URLs, page numbers, and normalized exact-text matches were checked by the Phase 8C validator. They are not authority approvals. All remain `NOT_REVIEWED`:

| Evidence ID | Source / page | Passage purpose | Review status |
|---|---|---|---|
| `EVID-SRC004-P017-CIA-SEE` | `SRC-004`, p.17, §5.7 | Historical prospective assessment description | `NOT_REVIEWED` |
| `EVID-SRC004-P017-GRADING` | `SRC-004`, p.17, §5.8 | Historical grading description | `NOT_REVIEWED` |
| `EVID-SRC014-P001-CURRICULUM` | `SRC-014`, p.1 | Curriculum title/year | `NOT_REVIEWED` |
| `EVID-SRC014-P003-AIML-BATCH` | `SRC-014`, p.3 | Programme and batch label | `NOT_REVIEWED` |

### Human decision (leave blank until reviewed)

- Reviewer name / role: __________________________________
- Review date: __________________________________________
- Document IDs reviewed: _________________________________
- Decision per document: APPROVE / REJECT / NEEDS_CORRECTION
- Applicability limitations and evidence: __________________
- Follow-up source/version requests: _______________________

Record any decision through the independent Phase 8A review mechanism. Do not edit `reviewer_status` or import a document based on this recommendation package alone.

## Phase 8E official-source search update

The [PES University Public Self Disclosure index](https://pes.edu/naac/upload/UGC-PSD/Public%20Self%20Disclosure.pdf) lists item 3.3, “Statutes/Ordinances Pertaining to Academics/Examinations,” and links `http://www.pes.edu/UGC-PSD/3.3`. That public route could not be retrieved during the Phase 8E review; no regulation bytes or checksum were available. It is a source lead, not a new document or approval candidate. Ask an authorized human/source owner to provide the file and its provenance.

The PES FAQ's general 80% exam attendance statement and 10-point grading statement were confirmed on the public official FAQ, but it does not identify the target B.Tech AIML cohort, campus, effective date, rule exceptions, or controlling regulation. A 2024 official examination-center article is explicitly about MCA at RR and is out of B.Tech scope. Neither is added as page-level PDF evidence or used to change any existing evidence status.

For the new document-by-document source and approval checklist, see `DOCUMENT_APPROVAL_STATUS.md`; regulation gaps by topic are in `MISSING_REGULATIONS_REPORT.md`. **No candidate approval was made; the four evidence records remain `NOT_REVIEWED`.**
