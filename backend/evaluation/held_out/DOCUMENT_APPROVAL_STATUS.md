# Phase 8E document approval status

**Human approvals recorded: 0.** This status report is an audit aid, not an approval. No `reviewer_status`, `authority_review_status`, or Phase 8A registry entry has been changed. All source/evidence decisions below remain pending or discovery-only unless explicitly labeled context-only, blocked, or out of scope.

## Candidate PDFs and source documents

| Candidate / source | Source and checksum | Issuer | Programme / campus / batch | Effective date / version | Exact page-level evidence | Current status and human questions |
|---|---|---|---|---|---|---|
| `SRC-003` The PES University Act, 2012 | [PES-hosted PDF](https://pes.edu/wp-content/uploads/2025/09/THE_PES_UNIVERSITY_ACT.pdf); SHA-256 `1d66332a097f0b2033fffb8398df6328cd1641cd6a9d75e0f0fedf9656948038` | Candidate title identifies Karnataka Gazette / Karnataka Act No. 16 of 2013; Karnataka State Legislature attribution needs reviewer confirmation. | Governance instrument; B.Tech AIML applicability unknown; campus/batch applicability unknown. | Act title 2012 / Act No. 16 of 2013; amendment/current-effect chain unknown. | None extracted; 16-page scanned PDF yields no PyMuPDF text. | `EXTRACTION_BLOCKED`. Human to confirm official Gazette, amendments, applicable provisions, and whether a readable original/OCR should be reviewed. No OCR data exists to approve. |
| `SRC-004` PES University Proforma to UGC | [PES-hosted UGC Proforma](https://pes.edu/wp-content/uploads/2025/09/PES_University_Profroma_To_UGC.pdf); SHA-256 `3558ac4222cea3a770a74dedc53510a74318b55842878ad9bf9ee1e7b9d01b06` | PES University submission to UGC; recipient is not the document's issuing authority. | General/historical University statements; not proven B.Tech AIML. Campus and cohort unknown. Some later content is explicitly PES Institute of Technology and excluded from PES University attribution. | PDF metadata 2014-03-18; operative/effective date and supersession chain unknown. | PDF p.17 §5.7: “The PES university will adopt Continuous In-semester Assessment (CIA) and Semester End Examination (SEE) Scheme for both theory and practical courses.” PDF p.17 §5.8: “The performance evaluation shall be done under a Letter Grading System obtained following the Relative Grading System and Absolute Grading System.” | `VERIFIED_OFFICIAL_CONTEXT_ONLY`. Human to confirm exact file and what institution/cohorts the prospective statements address; identify superseding regulations. Do not treat as current policy. |
| `SRC-014` CSE (AI & ML) Curriculum 2025–26 | [AIML department PDF](https://aiml.pes.edu/wp-content/uploads/2025/06/AIML-Curriculum-2025.pdf); SHA-256 `c9fae00eb4c9e7ba6d0adb0686fe681a709119c72ace361dee707c0c58ec1c4f` | PES University apparent from branding/metadata; exact binary linkage needs confirmation. | B.Tech CSE (AI & ML); campus unknown; p.3 identifies 2025–29 batch. | Cover says Curriculum 2025–26; PDF metadata 2025-06-01; effective date and supersession unknown. | PDF p.1: `PES UNIVERSITY … CURRICULUM – 2025 – 26`. PDF p.3: `B.TECH IN COMPUTER SCIENCE AND ENGINEERING (ARTIFICIAL INTELLIGENCE AND MACHINE LEARNING)` / `I SEMESTER ( 2025-29 BATCH)`. | `PENDING_HUMAN_AUTHORITY_REVIEW`. Human to confirm exact file is the linked syllabus download, campus(es), cohort scope, effective date, and separate regulations. Curriculum title/batch text is not attendance or exam-rule evidence. |
| `SRC-039` Public Self Disclosure item 3.3 index | [Official one-page disclosure index](https://pes.edu/naac/upload/UGC-PSD/Public%20Self%20Disclosure.pdf); not a regulation file; no candidate PDF checksum. | PES University. | Index lists a general academics category; no programme/campus/batch applicability. | Public disclosure PDF hosted under current site path; version/effective date of index not encoded as a policy version. | Index p.1 lists item 3.3: “Statutes/ Ordinances Pertaining to Academics/ Examinations.” It points to `http://www.pes.edu/UGC-PSD/3.3`. | `OFFICIAL_VERIFIED` source index only; no regulation evidence. Human/source owner should provide item 3.3's underlying files and source metadata. |
| `SRC-040` item 3.3 route (document not acquired) | [Officially indexed route](http://www.pes.edu/UGC-PSD/3.3); route was not retrievable in this review; no checksum or PDF bytes. | PES University is named by the index; the underlying document's issuer is unknown. | Unknown. | Unknown. | No passage/page exists for review. | `OFFICIAL_UNVERIFIED` source lead only. Request the actual public file and provenance; do not import or cite an assumed document. |

## Official discovery pages that are not controlling regulations

| Source | Exact information visible | Applicability issue / action |
|---|---|---|
| [PES University FAQ](https://pes.edu/faqs/) (`SRC-002`) | “80% attendance is mandatory for a student to take the exam”; grading FAQ describes a 10-point system using relative and absolute grading. | No rule document, effective date, B.Tech AIML batch/campus, exceptions, calculation, or SGPA/CGPA formula. Human must identify the controlling regulation before relying on these statements for current advice. |
| [PES B.Tech page](https://pes.edu/btech/) (`SRC-005`) | Identifies Ring Road and Electronic City campuses and lists CSE (AI & ML). | Program/campus discovery, not academic policy. |
| [PES AI & ML syllabus page](https://aiml.pes.edu/syllabus/) (`SRC-013`) | Lists AIML curriculum material. | The existing local PDF's exact link relationship and campus applicability need review. Curriculum is not an academic regulation. |
| [PES examination-center article](https://news.pes.edu/11617/) (`SRC-025`) | Oct. 23, 2024 event describes ISA/ESA, SGPA/CGPA and ISA mark review. | Article explicitly says event was for new MCA admits at RR campus. Exclude as B.Tech AIML policy evidence. |

## Evidence candidate status — unchanged

| Evidence ID | Source/page | Status | Approval requirement |
|---|---|---|---|
| `EVID-SRC004-P017-CIA-SEE` | UGC Proforma p.17 §5.7 | `NOT_REVIEWED` | Human confirms source, historical context and scope; cannot establish current B.Tech rule. |
| `EVID-SRC004-P017-GRADING` | UGC Proforma p.17 §5.8 | `NOT_REVIEWED` | Human confirms source, historical context and scope; cannot establish current grading formula. |
| `EVID-SRC014-P001-CURRICULUM` | AIML curriculum p.1 | `NOT_REVIEWED` | Human confirms file linkage and that it is a curriculum identifier, not policy. |
| `EVID-SRC014-P003-AIML-BATCH` | AIML curriculum p.3 | `NOT_REVIEWED` | Human confirms campus/cohort applicability and limits to programme/batch identification. |

## Approval checklist for the human reviewer

For each document proposed for future authoritative use, record a separate decision:

- [ ] Correct university and identifiable issuing authority
- [ ] Official exact URL/file relationship and original bytes/checksum verified
- [ ] Applies to B.Tech CSE (AI & ML)
- [ ] Applicable campus (RR, EC, both, or other) explicitly established
- [ ] Admission batch/cohorts explicitly established
- [ ] Publication and effective dates established
- [ ] Version, amendment, and supersession chain checked
- [ ] Exact page text, page numbering, headings, conditions, exceptions and tables manually checked
- [ ] Conflicts compared only against overlapping programme/campus/batch/time scope
- [ ] Appropriate policy categories explicitly identified; curriculum/FAQ/news are not overstated as regulations
- [ ] Decision recorded by an independent human: APPROVE / REJECT / NEEDS_CORRECTION
- Reviewer identity/date/reason/source evidence recorded: ______________________________

Only an explicit human approval through the existing Phase 8A review workflow can authorize an import. This report is not that approval.
