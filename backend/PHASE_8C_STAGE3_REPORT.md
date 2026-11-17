# RAARA — Phase 8C Stage 3 Report

**Implementation: PASS WITH LIMITATIONS**  
**Generic project-authored policy records: 28**  
**Project demonstration questions: 30**  
**Official university approvals: 0**  
**Official held-out dataset: EMPTY (0 documents, 0 questions)**  
**Regression: 220 passed, 0 failed**  
**Production changes: NONE**

## Implementation summary

Created a separate dataset at `evaluation/datasets/project_authored_academic_policy/generic_academic_policy_dataset.json`. Its 28 project-authored records cover 12 requested areas: attendance, assessment, passing, grading, SGPA, CGPA, backlogs, revaluation, course registration, credits, academic progression, and academic calendar. Records use the nonofficial labels `PROJECT_AUTHORED`, `GENERIC_PROJECT_POLICY`, `is_official_university_policy: false`, and `authority_status: NOT_OFFICIAL`. `review_status: PROJECT_APPROVED` is defined only as project-demo content status; it is not an institutional or human authority review.

The 30 labeled demonstration questions cover direct facts, calculations, multi-policy reasoning, unanswerable questions, clarification, and a version-conflict test. The v0.9 (70%) versus v1.0 (75%) attendance conflict is explicitly project-authored on both sides; no actual university amendment is represented. Questions about PES University policy, the 2025 AIML batch, medical exemptions, supplementary attempts/dates, revaluation deadlines, add/drop dates, and credit-to-hours are unanswered or require clarification, with no fabricated answer or evidence.

All policies have stable IDs, exact project-authored text, provenance, category, version, applicability, limitations, creator, and optional calculation details. They contain no claimed source URLs or page citations. The assumptions document explains why every requested numeric default is illustrative and why actual institutions may differ. The PES FAQ's separate 80% attendance discovery item is untouched.

## Validation and safety

The strict Pydantic schema and validator enforce unique IDs, approved field values, evidence/question cross-links, answerability rules, and nonofficial provenance. Validation independently recomputes attendance, shortfall, 40:60 weighted assessment, grade-band continuity, SGPA, CGPA, and numerical question examples.

Generic project records cannot be parsed as official `PolicyEvidenceRecord` values and cannot enter the official held-out document registry schema. The offline context formatter labels generic passages as project-authored assumptions; its official-policy query guard abstains. No records were inserted into the Phase 8A registry or any Chroma collection.

### Category counts

Policies:

| Category | Count |
|---|---:|
| Attendance | 5 |
| Assessment | 3 |
| Passing | 1 |
| Grading | 2 |
| SGPA | 2 |
| CGPA | 2 |
| Backlogs | 3 |
| Revaluation | 2 |
| Course registration | 2 |
| Credits | 2 |
| Academic progression | 2 |
| Academic calendar | 2 |
| **Total** | **28** |

Questions: 13 direct factual, 6 numerical calculation, 1 multi-policy, 8 unanswerable, 1 clarification, and 1 conflicting-policy example (**30 total**).

## Tests and validators — observed outcomes

| Check | Command | Result |
|---|---|---|
| Generic dataset validator | `python -m evaluation.scripts.validate_project_authored_policies` | **PASS** — 28 policies, 30 questions, 12 categories, numerical examples PASS, official approvals 0 |
| Focused generic policy tests | `python -m pytest -v evaluation/tests/test_project_authored_policies.py` | **12 passed in 0.48s** |
| Existing policy evidence tests | `python -m pytest -v evaluation/tests/test_policy_evidence.py evaluation/tests/test_policy_evidence_review.py` | **19 passed in 23.28s** |
| Phase 9A validator | `python -m evaluation.synthetic_project_data.validate` | **PASS** — 50 questions, 86 evidence references, 10 primary synthetic policy docs, 2 conflict fixtures |
| Phase 8A held-out validator | `python -m evaluation.scripts.validate_heldout_dataset` | **PASS; readiness EMPTY** — 0 imported docs, 0 verified official docs, 0 questions, 0 approvals |
| Full backend suite | `python -m pytest -v` | **220 passed in 41.67s** |

Commands were run using `backend/.venv311` (Python 3.11.9). The full suite used a unique temporary SQLite database, temporary ChromaDB directory, and temporary upload directory via `DATABASE_URL`, `CHROMA_PERSIST_DIR`, and `UPLOAD_DIR`. `OPENAI_API_KEY` was set empty. No live OpenAI requests were made. The held-out validator refreshed only its readiness report from the existing empty registry.

The Phase 9A tree (45 non-cache files, including dataset/manifests/results) retained composite SHA-256 `e60703d320a2339b2fc1181a0ca1ce55e980744ce6fe87358eac9c6cecaab4fd`; a focused regression test checks this fingerprint. Its validator also confirmed no held-out overlap and reported `production_storage_accessed: false`. Existing official registry remains empty.

An initial focused test run exposed an incorrect expected exception type in the new authority-gate test; the test was corrected to assert the existing review workflow's wrapped validation error. The final focused and full runs passed. No production behavior or storage was changed.

## Files created and changed

Created:

- `evaluation/schemas/project_policy.py`
- `evaluation/project_authored_policies.py`
- `evaluation/scripts/validate_project_authored_policies.py`
- `evaluation/tests/test_project_authored_policies.py`
- `evaluation/datasets/project_authored_academic_policy/generic_academic_policy_dataset.json`
- `evaluation/datasets/project_authored_academic_policy/GENERIC_POLICY_ASSUMPTIONS.md`
- `evaluation/datasets/project_authored_academic_policy/README.md`
- `PHASE_8C_STAGE3_REPORT.md`

Modified:

- `evaluation/README.md`

No existing Phase 9A dataset, manifest, synthetic policy file, prompt, production retriever, application configuration, database, or ChromaDB data was modified.

## Limitations

This is an offline demonstration dataset, not verified university evidence. It is not connected to `/api/chat` and has no retrieval index. The helper for labeling generic context and abstaining on common institutional queries is intentionally simple and is not a production safety control. A future demo integration should use a distinct evaluation-only vector collection and preserve the same nonofficial label in the answer. A future real-policy corpus must be acquired from an authorized source, scoped to institution/programme/campus/batch/version, and pass independent human review before entering the official registry.

**Disposition:** Stage 3 dataset and validators are complete. The result is PASS WITH LIMITATIONS because no retrieval index or chat integration was added; the project corpus remains safely isolated. This is not a real university-policy dataset and does not make the held-out official corpus ready. No later phase was started.

## PowerShell verification commands

From `C:\prompt_mini_proj\backend`:

```powershell
.\.venv311\Scripts\python.exe -m evaluation.scripts.validate_project_authored_policies
.\.venv311\Scripts\python.exe -m pytest -v evaluation\tests\test_project_authored_policies.py
.\.venv311\Scripts\python.exe -m pytest -v evaluation\tests\test_policy_evidence.py evaluation\tests\test_policy_evidence_review.py
.\.venv311\Scripts\python.exe -m evaluation.synthetic_project_data.validate
.\.venv311\Scripts\python.exe -m evaluation.scripts.validate_heldout_dataset

$testRoot = Join-Path $env:TEMP ("raara-stage3-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $testRoot | Out-Null
$dbPath = (Join-Path $testRoot "backend-tests.sqlite").Replace("\", "/")
$env:DATABASE_URL = "sqlite:///$dbPath"
$env:CHROMA_PERSIST_DIR = Join-Path $testRoot "chroma"
$env:UPLOAD_DIR = Join-Path $testRoot "uploads"
$env:TIKTOKEN_CACHE_DIR = "C:\Users\Pratik Kalloli\AppData\Local\Temp\data-gym-cache"
$env:OPENAI_API_KEY = ""
.\.venv311\Scripts\python.exe -m pytest -v
```

