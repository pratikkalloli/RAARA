# RAARA Phase 8F — Acquisition and Manual Intake Report

**Result: PASS WITH LIMITATIONS** for the requested document-acquisition preparation. This phase prepared a draft request and a manual staging workflow. It did not acquire university documents or change any authority/evidence approval state.

## Work completed

- Audited the Phase 8A–8E reports, held-out source/evidence records, candidate PDFs, registry, readiness artifacts, and Phase 8A import/validation commands.
- Prepared [`PES_DOCUMENT_REQUEST.md`](evaluation/held_out/PES_DOCUMENT_REQUEST.md). It asks for the ten requested categories, versions, scope, dates, issuer, and amendment/supersession history. It is a draft and **has not been sent**; no contact address was invented.
- Prepared [`DOCUMENT_INTAKE_GUIDE.md`](evaluation/held_out/DOCUMENT_INTAKE_GUIDE.md) and [`document_intake_manifest_template.csv`](evaluation/held_out/document_intake_manifest_template.csv), plus an incoming-directory notice. The guide stages unchanged originals, hashes them with SHA-256, checks duplicate hashes, checks PDF readability and page-level extraction, records provenance/scope, and keeps human review pending. It explicitly separates staging from the existing Phase 8A registry importer.
- Updated [`MISSING_REGULATIONS_REPORT.md`](evaluation/held_out/MISSING_REGULATIONS_REPORT.md) with acquisition-specific statuses so a public source lead is not counted as an acquired or verified document.
- Regenerated the existing readiness artifacts using the project validator: [`readiness_report.md`](evaluation/datasets/held_out/readiness_report.md) and [`readiness_report.json`](evaluation/datasets/held_out/readiness_report.json).

No production code, retrieval behavior, prompts, citation verification, benchmark output, SQLite data, or ChromaDB data was changed. No OpenAI call or annotation/evaluation activity was performed.

## Acquisition and review counts

| Measure | Actual status |
|---|---:|
| Existing Phase 8B candidate PDFs in discovery workspace | 3 |
| New PDFs received directly from PES University in Phase 8F | 0 |
| PDFs staged in `evaluation/held_out/incoming/` | 0 |
| Current B.Tech AIML academic regulations acquired | 0 |
| Authoritative held-out registry documents imported | 0 |
| Independently verified authoritative documents | 0 |
| Evidence candidates | 4, all remain `NOT_REVIEWED` |
| Human-approved evidence records | 0 |
| Human authority approvals recorded | 0 |
| Held-out questions | 0 |
| Dataset readiness | `EMPTY` |

Existing candidate classifications are preserved:

- PES University Act PDF: **extraction blocked** (16-page scanned PDF; no extracted text).
- UGC Proforma: **official context only** (archival 2014 submission; not current B.Tech AIML policy).
- AIML Curriculum 2025–26: **pending human review** (programme/batch applicability still needs confirmation; curriculum is not a regulation).

The request remains unsent; a reply has not been received. The actual current B.Tech AIML regulations and the underlying Public Self Disclosure item 3.3 file remain unavailable in the acquired-document set. The status update retains the prior discovery inventory counts: 40 source records, 3 downloaded candidate PDFs, 2 with text extraction and 1 with an extraction warning. These are not counts of direct university receipt or approved policy documents.

## Validation and regression tests

- Held-out dataset readiness validator: **completed successfully**, status `EMPTY`; 0 imported documents, 0 verified official documents, 0 questions, 0 approvals; source inventory remains 40 records.
- Complete backend test suite: **189 passed, 0 failed** (`37.06s`).
- Tests used a unique temporary SQLite file, temporary ChromaDB and upload paths, the existing local tokenizer cache, and an empty `OPENAI_API_KEY`. No production SQLite or ChromaDB data was targeted.
- No new intake application functionality was added, so no new code tests were required. The manual commands and existing importer are documented for future owner-led intake.

## Classification

| Area | Result |
|---|---|
| Intake preparation and reporting | **PASS** — request, manifest, manual guide, source-status update and readiness report are present. |
| Document acquisition | **NOT COMPLETE** — 0 direct university receipts and 0 newly staged PDFs. |
| Human review/approval | **NOT REVIEWED** — no approval state changed; 4 evidence candidates remain `NOT_REVIEWED`. |
| Dataset readiness | **EMPTY / NOT READY** — no authoritative registry documents or held-out questions. |
| Regression tests | **PASS** — full backend suite 189/189 passed. |

No held-out annotation or live evaluation was started. The next step is for the project owner to send the draft request through an authorized university channel and place any received original PDFs in the documented staging directory for human review.

