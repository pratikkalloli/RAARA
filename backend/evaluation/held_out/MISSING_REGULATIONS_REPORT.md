# Phase 8E — Missing official regulation documents

## Phase 8F acquisition-status update

This update distinguishes source discovery from document acquisition. Search/listing results are not downloaded or received documents, and download does not establish that a document is current, applicable, or verified official. The status vocabulary below is used per source/document: **Publicly located**, **Downloaded**, **Received directly from university**, **Verified official**, **Pending human review**, **Rejected**, and **Unavailable**. Multiple statuses may apply to a single record (for example, a downloaded file can still be pending human review).

| Regulation/source | Publicly located | Downloaded | Received directly from university | Verified official | Pending human review | Rejected | Unavailable |
|---|---|---|---|---|---|---|---|
| Current B.Tech AIML academic regulations / item 3.3 underlying file | Index lead located; linked route inaccessible | No | No | No | No file to review | No | **Underlying regulation unavailable** |
| B.Tech AIML rules by admission batch; ISA/ESA; attendance/eligibility; grading/SGPA/CGPA; backlogs/supplementary; revaluation/grievances; registration/withdrawal; progression/credits; amendments/circulars | Some official discovery pages and historical/context records; no controlling current rule located | No applicable current regulation PDF | No | No applicable regulation verified | No applicable regulation file received for review | No | **Applicable controlling documents unavailable** |
| The PES University Act, 2012 (`SRC-003`) | Yes, PES-hosted source URL | Yes; 16-page scanned PDF, extraction blocked | No | Yes — source provenance; applicability as an academic regulation is not established | Extraction/applicability follow-up required; existing classification remains `EXTRACTION_BLOCKED` | No | No |
| PES University Proforma to UGC (`SRC-004`) | Yes, PES-hosted source URL | Yes; 2014 archival submission | No | Official context-only source; not verified as current B.Tech AIML policy | Context/applicability questions remain; classification remains official context only | No | No |
| CSE (AI & ML) Curriculum 2025–26 (`SRC-014`) | Yes, AIML department source URL | Yes; 118-page PDF | No | No; exact linked file/applicability not independently confirmed | **Yes**; remains pending human review | No | No |
| Public Self Disclosure index item 3.3 (`SRC-039`/`SRC-040`) | Yes, index and route are publicly identified | Index only; underlying regulation not downloaded | No | Index source only, not underlying regulation | Underlying document unavailable for review | No | **Underlying route/document unavailable** |

Phase 8F request/intake status: document request drafted but **not sent**; university response **not received**; incoming staged PDFs **0**. Candidate PDFs already in the discovery workspace: **3**. Authoritative registry imports: **0**. Verified current B.Tech AIML regulations: **0**. The existing candidate classifications and human review statuses are unchanged.

For future supplied material, use [`DOCUMENT_INTAKE_GUIDE.md`](DOCUMENT_INTAKE_GUIDE.md), [`PES_DOCUMENT_REQUEST.md`](PES_DOCUMENT_REQUEST.md), and [`document_intake_manifest_template.csv`](document_intake_manifest_template.csv). Staging does not count as acquisition into the authoritative registry.

Search date: 2026-11-12. Scope: PES University Bengaluru, B.Tech CSE (AI & ML), Ring Road and Electronic City, applicable admission batches and historical versions. Searches covered official PES domains and the University's public self-disclosure index, programme/syllabus pages, FAQ, academic calendar, Important Information, and public examination-center information. No login, restricted portal, payment wall, guessed file path, or access-control bypass was used.

## Highest-priority missing source

The official [PES University Public Self Disclosure index](https://pes.edu/naac/upload/UGC-PSD/Public%20Self%20Disclosure.pdf) identifies item **3.3: “Statutes/ Ordinances Pertaining to Academics/ Examinations”** and gives the route `http://www.pes.edu/UGC-PSD/3.3`. That route could not be retrieved in the available public web review. No underlying document bytes, document title/version, checksum, effective date, issuer details, programme/campus/batch scope, or amendment history could be verified. It is recorded as `SRC-040`, an official source lead only. Request the actual document through an authorized PES public contact or source owner; do not infer its content.

## Topic-by-topic availability

| Requested regulation | Public official material found | Missing information / disposition |
|---|---|---|
| B.Tech academic regulations | The official disclosure index points to academics/examinations item 3.3; the route is inaccessible. B.Tech page identifies campuses/programme, not rules. | No current B.Tech regulation file, version, effective date, or applicability statement obtained. |
| AIML programme regulations | Official AI & ML syllabus page and 2025–26 curriculum identify program/course structure. | No separate AIML regulation or binding academic-rule document found. Curriculum does not establish attendance, grading, progression, or exam rules. |
| Attendance and ESA eligibility | PES FAQ states “80% attendance is mandatory for a student to take the exam.” | FAQ does not define B.Tech AIML applicability, campus, admission batch, effective date, calculation, exceptions, condonation, or controlling ESA eligibility rule. Not sufficient as current policy evidence. |
| ISA and ESA assessment | UGC Proforma p.17 §5.7 has prospective 2014 CIA/SEE text. Official Oct. 2024 news describes ISA/ESA at a high level. | Proforma is historical context; news item is explicitly about MCA at RR. No current B.Tech AIML assessment structure/weights/rules found. |
| SGPA/CGPA | FAQ describes a 10-point relative/absolute grading system. The 2024 news item says SGPA/CGPA calculation was discussed for MCA. | No B.Tech AIML formula, rounding rule, grade mapping, or operative rule source found. |
| Backlogs and supplementary exams | No applicable public official rule located. | Need B.Tech rules by batch, attempts/limits, eligibility, schedules, and supersession. |
| Revaluation / answer-script review | PES Support lists an Exams & Transcripts support topic for revaluation requests and official copies. | Support category is not a governing regulation; no B.Tech AIML deadlines, scope, procedure, fees, or review standard found. |
| Course registration | Official calendars list dates/events; B.Tech page lists program/campuses. | No registration eligibility, add/drop, course withdrawal, repeat, or batch-specific rulebook obtained. |
| Academic progression / promotion | No applicable B.Tech AIML rule text located. | Need credits, prerequisites, promotion thresholds, probation, vertical mobility, and batch/version definitions. |
| Admission-batch rules and amendments | AIML curriculum p.3 identifies the 2025–29 batch. Official calendars identify semesters/years. | No regulation text mapping cohorts to schemes or establishing amendment/supersession across batches. |

## Sources kept out of B.Tech AIML policy evidence

- The official FAQ's attendance/grading statements remain discovery statements until the applicable regulation and scope are confirmed.
- The 2014 UGC Proforma contains historic/prospective material and later pages with explicit PES Institute of Technology scope. Neither is treated as current B.Tech AIML policy.
- The 2025–26 AIML curriculum establishes program/batch labels only; exact binary linkage and campus applicability remain for human review.
- The official October 2024 examination-center article is about an MCA session at RR; it does not establish B.Tech AIML rules.
- Third-party, mirror, student, or different-institution sources remain excluded.

## Requested source acquisition from PES

An authorized human/source owner should provide the actual documents identified at item 3.3 and, if separately maintained, current B.Tech academic regulations, AIML scheme/regulations, attendance/ESA eligibility, exam/assessment handbook, grading/SGPA/CGPA formula, backlog/supplementary and revaluation rules, registration/progression rules, and historical batch/amendment records. For each file, preserve original bytes and establish URL/provenance, issuer, version, effective date, campuses, programme, batches and supersession before import. No request has been sent by this phase.

## Phase 8C resumption update (2026-11-13)

The official [AIML syllabus page](https://aiml.pes.edu/syllabus/) was rechecked and displays Batch 2025 and Batch 2026 curriculum content. Its Download Curriculum link currently points to Google Drive; the local 2025 PDF's exact linkage remains pending human confirmation. The official [Important Information page](https://pes.edu/important/) lists the archival UGC Proforma and PES University Act, but not a current B.Tech AIML regulation. The disclosed [item 3.3 route](http://www.pes.edu/UGC-PSD/3.3) remained inaccessible. These are discovery leads, not acquired regulations.

For attendance/eligibility, ISA/ESA, grading and SGPA/CGPA, backlog/supplementary, revaluation/grievances, course registration/withdrawal, progression/promotion, credit rules, batch-specific amendments, and applicable current calendars: **NO VERIFIED EVIDENCE FOUND**. Current public discovery does not establish that such rules do not exist. New files acquired: 0; directly received from university: 0; current B.Tech AIML rules verified authoritative: 0; human approvals: 0; readiness: `EMPTY`.

## Phase 8C Stage 2 acquisition-status update (2026-11-13)

The 2025 PES Public Self Disclosure index was downloaded and verified as a PES-hosted **index**, not as the underlying item 3.3 regulation. The linked item 3.3 route remains unavailable. PES AIML curriculum and 2026–27 academic calendar pages expose Google Drive links, but their viewers require sign-in; linked bytes were not acquired and no sign-in was attempted. Public discovery is not document acquisition.

| Requested category | Discovery outcome | Acquisition / review status |
|---|---|---|
| Current B.Tech regulations and AIML programme regulations | Public item 3.3 index lead; underlying route unavailable; AIML syllabus page exists | No applicable regulations downloaded or received; no human approval |
| Admission-batch versions and amendments | AIML page lists 2025 and 2026 batches, but current linked handbook is inaccessible | No batch regulation or amendment chain obtained |
| Attendance and ESA eligibility | FAQ has a broad 80% statement; not cohort-specific | Discovery statement only; no current rule verified |
| ISA/ESA assessment | 2014 UGC Proforma gives historical CIA/SEE context; event material noted in earlier research was MCA-specific | No current B.Tech AIML weighting or eligibility regulation verified |
| Grading, SGPA and CGPA | FAQ offers broad 10-point grading context | No applicable formula/rules obtained |
| Backlogs and supplementary examinations | No applicable public rule located | Unavailable in inspected materials |
| Revaluation and examination grievances | Support category is not a rule; no applicable regulations located | Unavailable in inspected materials |
| Course registration and withdrawal | Calendar links are schedule leads; files require sign-in | No registration/withdrawal rule acquired |
| Academic progression and credit requirements | Historical CSE handbooks/course structure and AIML curriculum are curriculum context | No current AIML progression regulation verified |
| Applicable academic calendars | 2026–27 links publicly located but Drive files inaccessible | No linked bytes or AIML scope reviewed |

Acquisition status vocabulary: **publicly located** means a public page or link was found; **downloaded** means bytes were saved; **received directly** means supplied by an authorized university source; **verified official** describes source provenance, not policy applicability; **pending human review** requires a human decision; **unavailable** means the underlying content could not be obtained in this review. Rejected: none. New current AIML regulation PDFs downloaded: **0**; directly received: **0**; current AIML regulations verified: **0**; authoritative imports: **0**; readiness remains `EMPTY`.
