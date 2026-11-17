# Human authority review checklist — Phase 8C

**Review state: NOT REVIEWED.** No human review has been completed or approved. Codex has not marked any review complete. A reviewer should record their identity, date, decision, evidence, and any conditions in the appropriate Phase 8A workflow only after completing this checklist.

## Candidate 1 — The PES University Act, 2012 (`SRC-003`)

- [ ] Correct institution: PES University, Bengaluru
- [ ] Issuing authority identifiable (candidate's first page identifies Karnataka legislature / Act)
- [ ] Exact source URL and file are official
- [ ] Applies to B.Tech
- [ ] Applies to AIML
- [ ] Relevant to Ring Road and Electronic City
- [ ] Applicable admission batches established
- [ ] Publication and effective dates established
- [ ] Amendments/supersession checked
- [ ] OCR text manually checked against sampled pages
- [ ] Original page numbers correct
- [ ] Exceptions and conditions preserved
- [ ] Appropriate to support the proposed academic-policy answer
- **Decision:** [ ] APPROVE [ ] REJECT [ ] NEEDS CORRECTION
- Reviewer / date / notes: ______________________________

Current blocker: scanned PDF has no extractable text; local OCR was unavailable. Classification remains `EXTRACTION_BLOCKED`.

## Candidate 2 — PES University Proforma to UGC (`SRC-004`)

- [ ] Correct institution and submission context confirmed
- [ ] Issuing authority identifiable
- [ ] Exact file and source URL confirmed
- [ ] Historical statements distinguished from operative regulations
- [ ] Applies to B.Tech AIML (if claimed)
- [ ] Applies to relevant campus (if claimed)
- [ ] Admission-batch scope established
- [ ] Publication/effective dates established
- [ ] Supersession and later changes checked
- [ ] Extracted text and page references checked
- [ ] PES Institute of Technology passages kept separate from PES University passages
- [ ] Exceptions and conditions preserved
- [ ] Appropriate to support the proposed answer
- **Decision:** [ ] APPROVE [ ] REJECT [ ] NEEDS CORRECTION
- Reviewer / date / notes: ______________________________

Current classification: `VERIFIED_OFFICIAL_CONTEXT_ONLY`. The archival 2014 submission includes prospective language and mixed institutional scope. It is not an established current B.Tech AIML rulebook.

## Candidate 3 — CSE (AI & ML) Curriculum 2025-26 (`SRC-014`)

- [ ] Correct PES University and issuing authority confirmed
- [ ] Exact local PDF linked from the official syllabus page confirmed
- [ ] Applies to B.Tech CSE (AI & ML)
- [ ] Ring Road / Electronic City applicability established
- [ ] 2025-29 batch applicability confirmed
- [ ] Publication/effective date established
- [ ] Supersession checked
- [ ] Extracted text and page references checked
- [ ] Curriculum content distinguished from academic regulations
- [ ] Appropriate to support the proposed answer
- **Decision:** [ ] APPROVE [ ] REJECT [ ] NEEDS CORRECTION
- Reviewer / date / notes: ______________________________

Current classification: `PENDING_HUMAN_AUTHORITY_REVIEW`. The official AI/ML syllabus page's download link resolved to Google Drive rather than the exact local URL; campus scope is unknown. The curriculum is not evidence of attendance or examination rules.

## Reviewer decision rule

Use the Phase 8A independent review workflow. A document may enter an authoritative registry only after a human establishes the exact document, issuing authority, applicability, version, and provenance. Leave the decision blank until a human reviewer completes it. Do not infer approval from official hosting, successful extraction, or a valid hash.

## Resumption check (2026-11-13)

No reviewer decision was entered. All existing approval checkboxes and candidate/evidence statuses remain unchanged.

### Additional review item for candidate 3 — AIML curriculum exact-file provenance

The live [AIML syllabus page](https://aiml.pes.edu/syllabus/) lists Batch 2025 and Batch 2026 and its “Download Curriculum” link resolves to Google Drive. The local candidate PDF is hosted at `https://aiml.pes.edu/wp-content/uploads/2025/06/AIML-Curriculum-2025.pdf`; search indexing surfaced that official-hosted URL, but the current syllabus page does not link to that exact URL. A human reviewer should obtain/compare the official download bytes or request confirmation from the issuing department before identifying the local file as the page’s linked curriculum.

- [ ] Exact file matches current official download
- [ ] Department/issuing authority confirmed
- [ ] Programme, campus, batch and lateral-entry scope confirmed
- [ ] Publication/effective date, version and supersession confirmed
- [ ] Each evidence candidate reviewed verbatim and within its proper curriculum scope
- **Decision:** [ ] APPROVE [ ] REJECT [ ] NEEDS CORRECTION
- Reviewer / date / notes: ______________________________

This checklist is preparatory only. Status remains `PENDING_HUMAN_AUTHORITY_REVIEW`; all four evidence candidates remain `NOT_REVIEWED`.

## Phase 8C Stage 2 review ledger workflow (2026-11-13)

An explicit, append-only human decision workflow is available in `evaluation/policy_evidence_review.py` and `evaluation/scripts/review_policy_evidence.py`. To inspect and decide an individual candidate, run from `backend`:

```powershell
.\.venv311\Scripts\python.exe -m evaluation.scripts.review_policy_evidence --help
.\.venv311\Scripts\python.exe -m evaluation.scripts.review_policy_evidence --evidence-id <evidence-id>
```

The reviewer must provide an identity, APPROVE or REJECT, a rationale, and exact confirmation. Approval is accepted only when the source is classified `VERIFIED_AUTHORITATIVE` and current. The candidate JSONL and PDFs are not edited; decisions are appended to a separate hash-chained review log, and effective status is derived from that ledger. This is tamper-evident bookkeeping, not a cryptographic signature or proof of reviewer identity. No review was run; all four existing evidence candidates remain `NOT_REVIEWED` and checklist decisions remain blank.

The new disclosure index, CSE syllabus handbook, and CSE course structure are discovery/context material only. The linked AIML handbook and calendar files remain inaccessible behind Google Drive sign-in; no access-control bypass was attempted.

