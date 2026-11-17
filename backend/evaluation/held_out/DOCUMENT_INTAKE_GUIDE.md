# Manual University Document Intake Guide

This is a staging procedure for university-supplied source files. Incoming files are not authoritative registry entries. No automatic import, source verification, evidence approval, or question generation occurs during intake.

## 1. Prepare staging

Run from `C:\prompt_mini_proj\backend` in PowerShell:

```powershell
New-Item -ItemType Directory -Force evaluation\held_out\incoming | Out-Null
```

Place each original university-supplied PDF in `evaluation\held_out\incoming\`. Do not edit, optimize, OCR, rename, redact, or overwrite the received original. Use a unique filename if needed; record the supplied filename and any staging filename in the intake notes. Restrict access to the staging directory to the project owner and designated reviewers.

Record receipt in `document_intake_manifest_template.csv` (one row per file), including the sender/source description, actual receipt date, issuing authority as stated by the document/provider, programme, campus, batch scope, publication/effective dates, version and supersession information. Use `UNKNOWN` only when the information is genuinely absent or not yet confirmed; explain uncertainty in a separate reviewer note. Do not infer dates or scope from a filename.

## 2. Preserve and fingerprint originals; detect duplicates

Compute SHA-256 for each staged file:

```powershell
Get-ChildItem -LiteralPath evaluation\held_out\incoming -File -Filter *.pdf |
  Get-FileHash -Algorithm SHA256 |
  Select-Object Path, Hash
```

Copy the resulting lowercase digest into the manifest `checksum` column. Before assigning a new intake ID, compare the digest with all manifest entries and the registry's existing checksums:

```powershell
$incoming = Get-ChildItem -LiteralPath evaluation\held_out\incoming -File -Filter *.pdf
$registry = Get-Content evaluation\datasets\held_out\documents.json -Raw | ConvertFrom-Json
$registryHashes = @($registry.documents | ForEach-Object { $_.sha256.ToLowerInvariant() })
$incoming | ForEach-Object {
  $hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
  [pscustomobject]@{ File = $_.Name; SHA256 = $hash; AlreadyInRegistry = ($registryHashes -contains $hash) }
}
```

Also compare each incoming hash with prior manifest hashes. A matching hash means byte-identical content: record it as a duplicate and link the existing intake/document ID; do not create another registry entry. A different checksum does not by itself establish a new version—confirm version/supersession with the source owner or a human reviewer. Never replace an existing original.

## 3. Validate readability and extract page-level text

Use the installed PyMuPDF package without writing back to the source PDF:

```powershell
.\.venv311\Scripts\python.exe -c "import fitz, pathlib, sys; p=pathlib.Path(sys.argv[1]); d=fitz.open(p); print({'filename':p.name,'pages':d.page_count,'text_chars_by_page':[len(page.get_text('text').strip()) for page in d]}); d.close()" "evaluation\held_out\incoming\<filename>.pdf"
```

If the file cannot be opened, has zero pages, or is encrypted/unreadable, record `extraction_status` as `BLOCKED` and the reason in the reviewer notes. If it opens, inspect the extracted character count page by page. A zero-text page or image-only file is not evidence of an empty policy: keep it pending and request a readable official copy or an explicitly authorized extraction/OCR review. Do not create OCR text silently or alter the original.

For readable PDFs, retain page boundaries and extract exact page text. The existing project helper can be used for an explicit read-only extraction:

```powershell
.\.venv311\Scripts\python.exe -c "from pathlib import Path; from app.services.document_processor import extract_pdf_pages; import sys; pages=extract_pdf_pages(Path(sys.argv[1]).read_bytes()); print('\n'.join(f'--- PAGE {page.page_number} ---\n{page.text}' for page in pages))" "evaluation\held_out\incoming\<filename>.pdf"
```

Review headings and section labels against the PDF page itself. Save extraction notes separately; do not overwrite or transform the received PDF. Record `READABLE` only when the file opens and page-level text has been checked. Partial extraction, missing pages, garbled text, or unresolved section boundaries should be recorded as `PARTIAL` or `BLOCKED`, with details.

## 4. Human review gate

Every new manifest row starts with `human_review_status` = `PENDING_HUMAN_REVIEW`. Intake staff must not mark a source verified or approve evidence. A designated independent reviewer must confirm source provenance, issuing authority, exact file identity, applicability, campus, programme, batch, dates/version, amendment history and supersession. Evidence statements remain pending until separately checked against exact PDF pages and sections.

Keep unknown applicability, conflicting rules, unclear effective dates, and supersession questions unresolved and visible. Public discovery pages or the fact that a file was supplied do not establish that it is current or controlling.

## 5. Registry import is a separate, explicit step

Do not run the importer merely because a file was staged. Only after explicit human approval to import that specific document, use the existing Phase 8A importer from `backend`, providing the actual provenance and authorization details:

```powershell
.\.venv311\Scripts\python.exe -m evaluation.scripts.import_heldout_document `
  --source "evaluation\held_out\incoming\<filename>.pdf" `
  --document-id "<unique-id>" `
  --title "<title copied from source>" `
  --version "<version copied from source or confirmed by issuer>" `
  --authority official `
  --acquisition-method project_owner_supplied `
  --source-description "<who supplied it and how; no invented source details>" `
  --permission-record "<owner authorization or documented permitted-use basis>" `
  --retrieved-at <YYYY-MM-DD> `
  --publication-date <YYYY-MM-DD-if-known> `
  --effective-date <YYYY-MM-DD-if-known> `
  --supersedes "<prior-document-id-if-confirmed>"
```

Omit optional date or `--supersedes` arguments when unknown/not applicable. Use the exact receipt date for `--retrieved-at` for owner-supplied material. The importer copies original bytes, checks PDF opening, calculates SHA-256/page count, detects duplicates and records provenance. Its `official` argument is only a claim: it leaves authority review pending and does not approve the document. Record each confirmed version as a separate document and preserve its predecessors. Do not import unofficial/context-only material as official.

After an approved import, validate the registry using the existing held-out dataset validator. Keep all question/evidence annotation and independent approval steps separate. No questions should be created as part of document intake.

## Manifest fields

Use `document_intake_manifest_template.csv`. The template contains the requested fields; it is an intake log, not the authoritative document registry. Keep the original CSV row and hash audit trail. Do not place secrets or unnecessary personal information in source/receipt notes.

