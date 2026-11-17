# Held-out evaluation split — NOT POPULATED

Current state: **0 genuine documents, 0 questions, 0 approved annotations**. Only the blank registry, empty JSONL and workflow template are present. No official or unofficial real-world university document has been imported. The 12-item development dataset and its synthetic PDFs are separate and must never be copied, adapted, or relabeled into this split.

The held-out data are sealed from tuning. Do not use these questions or labels to tune prompts, retrieval thresholds, top-K, or production behavior. Exact normalized question and ID overlap with development data is programmatically rejected; manual review is still required to catch semantic rewording or paraphrased leakage.

## 1. Import a document with provenance

Only import an original PDF supplied by the project owner or obtained through an authorized public source. Preserve the input file unchanged. Record title, version, publication/effective date when available, source URL or supplied-source description, retrieval date, and permission/access record. The importer checks that the PDF opens, computes SHA-256, detects byte-identical duplicates, refuses ID/path overwrites, copies original bytes under `sources/`, and records page count. It does **not** decide whether a source is official or verify a public source automatically.

Run the importer from `backend` in `.venv311` (quote paths containing spaces):

```powershell
.\.venv311\Scripts\python.exe -m evaluation.scripts.import_heldout_document `
  --source "C:\path\to\authorized-original.pdf" `
  --document-id UNI-POLICY-2026 `
  --title "<title copied from document>" `
  --version "<version printed by source>" `
  --authority official `
  --acquisition-method authorized_public_source `
  --source-url "https://university.example/policy.pdf" `
  --source-description "<official university source page and retrieval context>" `
  --retrieved-at 2026-11-12 `
  --permission-record "<public access or owner authorization basis>"
```

For an owner-supplied source, use `--acquisition-method project_owner_supplied` and describe the handoff in `--source-description` and `--permission-record`; a URL may be omitted. The `official` option records the claimed authority with **pending** review. A separate human must confirm the issuing body/source before changing `authority_review_status` to `verified` and recording reviewer ID/date. Unofficial references remain `unofficial_reference` / `not_official` and cannot support an approved regulatory annotation as authoritative evidence.

Do not overwrite source bytes or silently replace versions. Import each distinct version with a distinct document ID and use `--supersedes <older-document-id>` to record explicit history. Registry validation checks every PDF checksum, page count, source path containment, unique ID/checksum, source provenance fields, version references, and supersession references.

## 2. Create pending annotations

After a source has verified provenance, use the interactive annotator:

```powershell
.\.venv311\Scripts\python.exe -m evaluation.scripts.annotate_heldout
```

It lists registered documents and version/authority states, then asks for the question, category, answerability, expected answer/status, exact evidence text, page, section, document version, claims, notes, and annotator ID. New complete annotations are saved as `PENDING_REVIEW`; the annotator cannot self-approve. Before appending, the complete proposed dataset is validated against the registry, original PDF page text, and development split. `DRAFT` is for planning and is not a scored or approved dataset item.

Supported categories: direct factual, multi-passage, multi-document, unanswerable, conflicting policy, version-sensitive, academic eligibility, examination/assessment, grading and academic performance, policy interpretation, and prompt-injection resistance. Unanswerable examples must have `NOT_FOUND`, `answerable=false`, no expected answer, and no mandatory evidence.

## 3. Independent review and approval

The independent reviewer checks the question and answer, exact source passage, page and heading, source version/date, conflict/supersession handling, answerability, claims, and leakage risk. Record status with a different reviewer ID. The tool accepts `APPROVED`, `REJECTED`, and `NEEDS_CORRECTION` (and legacy Phase 8A `reviewed`/`approved` values):

```powershell
.\.venv311\Scripts\python.exe -m evaluation.scripts.review_heldout_annotation `
  --question-id "<id>" --reviewer-id "<independent-reviewer>" --status NEEDS_CORRECTION

.\.venv311\Scripts\python.exe -m evaluation.scripts.review_heldout_annotation `
  --question-id "<id>" --reviewer-id "<independent-reviewer>" --status APPROVED
```

Approval is rejected if annotation/review metadata is incomplete, reviewer equals annotator, provenance or evidence fails validation, development overlap is found, or a cited source is unofficial/unverified. `REJECTED` and `NEEDS_CORRECTION` remain unapproved; correct the record and submit a new pending-review revision. `APPROVED` entries are immutable; issue a new dataset version to amend labels.

## 4. Validate and check readiness

```powershell
.\.venv311\Scripts\python.exe -m evaluation.scripts.validate_heldout_dataset
```

This validator reads the question JSONL, registry, development split, source PDFs, and optional Phase 8B acquisition inventory without changing source data. It checks source hashes and PDF page counts, exact evidence text/page/version, annotation completeness, conflicting versions, official-source approval, unique IDs/evidence mappings, development overlap, and supersession references. Its readiness reports include acquisition counts when `evaluation/held_out/source_inventory.json` is present. Discovery records and staged candidate PDFs do not count as imported registry documents.

`ready_for_phase_8b` requires at least one independently verified official document. `ready_for_phase_8c` requires at least 40 approved questions. The target is approximately 40–60 genuinely sourced questions; neither the importer nor annotator generates question content. Do not begin 8C until real document sourcing, annotations, independent approvals, and permission checks are complete.

## 5. Data minimization and split security

- Keep original PDFs byte-for-byte under this directory and store their checksums in `documents.json`.
- Do not add synthetic fixtures to the real held-out registry. Unit tests create clearly labeled synthetic PDFs only under temporary test directories.
- Restrict access to `questions.jsonl` because it contains reference answers, labels, exact passages, and annotation metadata.
- Preserve superseded versions rather than replacing them; add a new manifest entry that references the earlier ID.
- Publicly accessible does not automatically mean permitted for every use. Record the lawful/public-access basis or owner authorization.
