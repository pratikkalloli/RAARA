# RAARA Generic Academic Policy Dataset

## Purpose

This standalone dataset contains **28 project-authored generic academic-policy records** and **30 project demonstration questions** for showing policy retrieval, arithmetic, abstention, clarification, and version-conflict behavior. It fills a demonstration need while current applicable PES University B.Tech AIML regulations remain unavailable for review. It is not an official policy corpus and must not be presented as university advice or a production regulation source.

Every policy record states `provenance: PROJECT_AUTHORED`, `source_type: GENERIC_PROJECT_POLICY`, `is_official_university_policy: false`, and `authority_status: NOT_OFFICIAL`. `review_status: PROJECT_APPROVED` means accepted for this project demonstration only. It is not human authority approval. No source URL, document page, or institutional citation is claimed for these authored records.

## Content and numerical assumptions

Coverage includes attendance, assessment, passing requirements, grading, SGPA, CGPA, backlogs, revaluation, course registration, credits, academic progression, and calendar periods. The exact numerical defaults, rationale, and worked arithmetic are in [GENERIC_POLICY_ASSUMPTIONS.md](GENERIC_POLICY_ASSUMPTIONS.md). They are examples only. In particular, this dataset does not define special attendance exemptions, an additional exam-only passing mark, maximum supplementary attempts/dates, fixed revaluation or registration deadlines, real calendar dates, actual promotion criteria, or credit-to-hours mappings.

The 30 questions include answerable facts, calculations, multi-record reasoning, unanswerable questions, clarification cases, and an explicit conflict between two **project-authored** attendance examples (versions 0.9 and 1.0). The conflict is fictional test data, not a university amendment. Questions asking for official PES requirements or real batch applicability have no fabricated expected answer or evidence.

## Isolation and safe use

The files in this directory are separate from:

- the Phase 8A official held-out registry and question file;
- the Phase 9A synthetic corpus and its datasets/results;
- production SQLite and ChromaDB;
- production retriever, prompts A/B/C, and application settings.

No production retrieval integration is added. The optional offline display helper in `evaluation/project_authored_policies.py` prefixes retrieved generic text with an explicit nonofficial label and abstains on recognized official-policy queries. It is a demonstration utility, not production chat orchestration. The existing official evidence gate accepts provenance-validated `PolicyEvidenceRecord` records and ledger-backed human decisions; project policies do not match that schema or pass the gate.

A future demonstration may build an evaluation-only index in a temporary directory, tagged by dataset ID and `NOT_OFFICIAL`; it must never share the production collection or official evidence registry. Do not combine this dataset with Phase 9A assets.

## Validate and test

From `backend` in `.venv311`:

```powershell
.\.venv311\Scripts\python.exe -m evaluation.scripts.validate_project_authored_policies
.\.venv311\Scripts\python.exe -m pytest -v evaluation\tests\test_project_authored_policies.py
```

The validator checks strict schema fields, unique identifiers, provenance labels, evidence links, answerability rules, and recomputes grade-band coverage plus attendance, assessment, SGPA, and CGPA examples. Tests also check that official-policy questions abstain, generic evidence cannot pass the official evidence gate or held-out registry schema, and the existing Phase 9A manifests/question files retain their pinned checksums.

## Limitations and replacement path

These policies are authored assumptions, not evidence about PES University or any other institution. They do not establish legal or academic rights, eligibility, deadlines, or cohort applicability. Lexical official-query detection in the demo helper is intentionally simple and is not a safety boundary for production.

To replace examples with real rules, obtain the documents from an authorized source; preserve bytes, source, checksum, issuer, version, effective dates, programme/campus/batch scope, and supersession; extract exact page-level evidence; and complete the separate human review and approval workflow. Keep generic files and results intact as a versioned demonstration corpus. Never relabel these records as official or carry their `PROJECT_APPROVED` label into the official authority gate.
