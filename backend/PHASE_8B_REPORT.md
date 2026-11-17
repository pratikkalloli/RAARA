# RAARA Phase 8B — PES University source acquisition and held-out preparation

**Result: PASS WITH LIMITATIONS** for source discovery, candidate preservation, PDF inspection, planning materials, workflow updates, and validation. The real held-out dataset is **not ready for Phase 8B evaluation** and this milestone cannot be closed as a populated dataset: no document has been entered in the authoritative registry, no real questions were authored, and no human annotations were independently reviewed or approved.

Date of source research and local inspection: 2026-11-12. Project: `C:\prompt_mini_proj`; backend: `C:\prompt_mini_proj\backend`; Python: 3.11.9 in `.venv311`.

## 1. Repository audit

Read the Phase 8A, 7E, and final research reports; inspected the evaluation tree, held-out schemas, importer, annotator, reviewer, validator, templates, and tests. The Phase 8A source-of-truth split was empty: `evaluation/datasets/held_out/documents.json` had zero entries and `questions.jsonl` had zero records. The existing importer copies the original PDF bytes, hashes them, checks page count and duplicates, and leaves claimed official authority pending. The existing approval validator requires official documents with independent authority review. The 12-question synthetic development dataset and all production state remain separate.

No production RAG routes/services, prompts, retrieval settings, benchmark result artifacts, frontend files, SQLite data, or ChromaDB data were modified. No API key was read or logged, and no live OpenAI call was made.

## 2. Source discovery and authenticity findings

The source inventory records **24 tracked source resources**:

| Classification | Count | Notes |
|---|---:|---|
| `OFFICIAL_VERIFIED` | 11 | Official PES webpages and exact linked/hosted PDF source records. This is a source-origin inventory classification, not a Phase 8A independent registry review. |
| `OFFICIAL_UNVERIFIED` | 9 | Six calendar files on Google Drive/Docs that could not be inspected; an AIML curriculum file needing exact-link/applicability review; and two CSE PDF variants without locally verified bytes. |
| `WRONG_INSTITUTION` | 4 | Two PES Pre-University sources and two PES Institute of Medical Sciences and Research sources; excluded from PES University B.Tech scope. |

The official PES FAQ page states an 80% exam attendance requirement, but it does not specify an effective date, admission batch, or campus. It is a webpage, not an imported PDF rule. A search result for PES Pre-University College gave a different attendance threshold; that source was identified as the wrong institution and excluded. Neither webpage was converted into a question or gold answer.

The academic calendar page links six Google Drive/Docs calendar resources. Those viewer pages returned loading/sign-in or JavaScript-required screens. File contents, dates, PDF bytes, and hashes therefore remain unverified. The calendar page labels Jan–May 2026 as AY 2026–27; that date/academic-year ambiguity is preserved rather than corrected by assumption.

The official CSE department programmes page links B.Tech course structure, detailed curriculum, and syllabus materials. Three linked CSE PDFs (96, 80, and 130 pages; one is explicitly 2019–20) were readable in the web PDF viewer, but local HTTPS download attempts timed out. They have no local bytes or checksums and were not imported. Two additional CSE PDFs were search-indexed but their relationship to the current linked files could not be confirmed, so they remain unverified.

The complete source URLs, individual status, retrieval outcome, applicability notes, source domain, and hashes where available are in [`evaluation/held_out/SOURCE_INVENTORY.md`](evaluation/held_out/SOURCE_INVENTORY.md) and `evaluation/held_out/source_inventory.json`. The JSON inventory uses explicit `null` values for unknown provenance fields rather than inferring dates, versions, campuses, or programme applicability.

## 3. Downloaded PDFs and extraction

Three candidate PDFs were downloaded from PES-related URLs into `evaluation/held_out/documents/`. The original files were retained unchanged and their SHA-256 values were rechecked against the inventory.

| Candidate PDF | Source classification | Pages | Text-extracted pages | Finding |
|---|---|---:|---:|---|
| PES University Act 2012 | `OFFICIAL_VERIFIED` | 16 | 0 | Official Important Info page links this exact URL; rendered page 1 shows Karnataka Gazette, Karnataka Act No. 16 of 2013, and PES University Act 2012. Image-only scan; extraction raised `EmptyPDFError`. No OCR was run; hold pending a valid extraction/review path. |
| PES University UGC Proforma | `OFFICIAL_VERIFIED` | 475 | 475 | Exact URL linked by the PES Important Info page; first page identifies the UGC proforma and PES University. PDF metadata dates to 2014. It contains historical and mixed-institution references, including PES Institute of Technology; not treated as current B.Tech regulation. |
| CSE (AI & ML) Curriculum 2025–26 | `OFFICIAL_UNVERIFIED` | 118 | 118 | PES branding and metadata inspected; PDF metadata creation date 2025-06-01; content identifies 2025–29 batch. The department page links a Google Drive download rather than this exact URL, and campus applicability is unknown. Curriculum content, not general regulation. |

All three PDFs opened and their page counts were checked. Existing PyMuPDF extraction ran across every page of all three. Two PDFs had text on every page; one had no extractable text. The UGC and curriculum extraction heuristically identified 1,604 and 589 section fragments respectively; these heading boundaries are not human-verified. Representative first pages were rendered and visually inspected. Poppler reported missing display-font warnings for Symbol/ArialUnicode on sampled UGC pages, while text extraction succeeded.

Details are in [`evaluation/held_out/PDF_INSPECTION_REPORT.md`](evaluation/held_out/PDF_INSPECTION_REPORT.md). The folder name `academic_regulations` does not mean the AIML curriculum is a regulation; the accompanying README explains the candidate-only status.

## 4. Registry, question plan, and human review

The Phase 8A registry remains intentionally empty: **0 genuine documents imported; 0 documents independently verified in the registry**. Inventory classification of an official source does not replace the separate human authority review required by Phase 8A. The Act also cannot supply text evidence under the existing extraction path, the UGC Proforma is archival/mixed-scope, and the curriculum needs exact-file and campus review. No source was promoted based only on its name or a search result.

[`evaluation/held_out/question_plan_template.csv`](evaluation/held_out/question_plan_template.csv) is a blank plan with the requested category targets, totaling **54 planned slots**. These are targets only; it contains no fabricated question text, answers, or evidence. Actual held-out questions: **0**. Completed annotations: **0**. Approved annotations: **0**. Rejected annotations: **0**. Pending annotations: **0**. No independent human annotation review was performed or claimed.

The existing annotator now creates `PENDING_REVIEW` records. The reviewer tool accepts `APPROVED`, `REJECTED`, and `NEEDS_CORRECTION`, retaining the legacy `reviewed`/`approved` values for backward compatibility. `DRAFT` remains planning-only. Approval still requires an independent reviewer and verified official source evidence. The grading/academic-performance category was added to the existing held-out schema and authoring choices to match the requested plan; no production schema or service changed.

## 5. Readiness and validation

The existing held-out validator passed against the empty authoritative split. Its readiness report now also incorporates the separate source inventory:

- Discovered source records: **24**.
- Official-verified source records: **11**; official-unverified: **9**; wrong-institution/scope exclusions: **4**.
- Downloaded PDFs: **3**; opened: **3**; text extracted: **2**; extraction warnings: **1**.
- Imported authoritative documents: **0**; questions: **0**; annotations/approvals: **0**.
- Dataset readiness: **EMPTY**; `ready_for_phase_8b=false`; `ready_for_phase_8c=false`.

The source counts represent acquisition inventory records, not approved corpus documents. The readiness output distinguishes those counts from registry and annotation counts. Exact normalized development leakage checks remain enabled.

## 6. Test results

Final verification used Python 3.11.9, the local tokenizer cache, and isolated temporary database, ChromaDB, and upload paths. No paid API calls were made.

| Command | Result |
|---|---|
| `python -m pytest -v evaluation\tests\test_heldout_workflow.py` | **23 passed, 0 failed**. |
| `python -m pytest -v evaluation\tests` | **75 passed, 0 failed**. |
| `python -m evaluation.scripts.validate_heldout_dataset` | **Passed**; reports `EMPTY`, 0 registry docs/questions/approvals, 24 source records and the acquisition/extraction counts above. |
| Full backend `python -m pytest -v` | **180 passed, 0 failed**. |

One initial evaluation-suite attempt without `TIKTOKEN_CACHE_DIR` produced four network-dependent tokenizer-cache failures; rerunning with the existing local cache passed. A default-sandbox full test run stalled at an auth integration test; rerunning through the normal local-socket approval route with isolated stores completed. These were environment issues, not hidden or omitted test failures.

## 7. Outstanding work and decision

**Phase 8B cannot be closed as a populated held-out dataset.** It can close only as a limited acquisition/preparation pass. Required manual follow-up:

1. Have a separate human reviewer confirm source authority, exact file linkage, version, campus, programme and batch applicability before registry import.
2. Obtain downloadable, current RR/EC B.Tech academic regulations and examination/assessment policies; calendar and FAQ sources alone do not cover these rules.
3. Decide whether and how to extract the scanned Act; do not use OCR text until its accuracy is checked against the images.
4. Import only approved source versions using the Phase 8A importer and preserve their original bytes/checksums.
5. Author 40–60 genuine questions from verified sources, annotate exact page/section evidence, and obtain independent human review. The 54 plan slots are not questions.

**Phase 8C live evaluation is not permitted by this result.** The held-out registry has no independently verified documents or approved annotations, and there is no authorization here to run live model evaluation. No Phase 8C work was started.

## 8. Exact PowerShell verification commands

Run from `C:\prompt_mini_proj\backend`:

```powershell
.\.venv311\Scripts\python.exe -m evaluation.scripts.validate_heldout_dataset
.\.venv311\Scripts\python.exe -m pytest -v evaluation\tests\test_heldout_workflow.py
.\.venv311\Scripts\python.exe -m pytest -v evaluation\tests
```

Full backend regression with isolated stores (local Windows socket access is required by existing TestClient tests):

```powershell
$testRoot = Join-Path $env:TEMP ('raara-phase8b-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $testRoot | Out-Null
$dbPath = (Join-Path $testRoot 'raara-test.sqlite').Replace('\', '/')
$env:DATABASE_URL = "sqlite:///$dbPath"
$env:CHROMA_PERSIST_DIR = Join-Path $testRoot 'chroma'
$env:UPLOAD_DIR = Join-Path $testRoot 'uploads'
$env:TIKTOKEN_CACHE_DIR = 'C:\Users\Pratik Kalloli\AppData\Local\Temp\data-gym-cache'
.\.venv311\Scripts\python.exe -m pytest -v
```

Verify the preserved candidate checksums:

```powershell
Get-FileHash evaluation\held_out\documents\university_governance\THE_PES_UNIVERSITY_ACT.pdf -Algorithm SHA256
Get-FileHash evaluation\held_out\documents\university_governance\PES_University_Profroma_To_UGC.pdf -Algorithm SHA256
Get-FileHash evaluation\held_out\documents\academic_regulations\AIML-Curriculum-2025.pdf -Algorithm SHA256
```
