# OCR report — University Act candidate

**Status: BLOCKED; no OCR run.** The original PDF remains unchanged at `documents/university_governance/THE_PES_UNIVERSITY_ACT.pdf`.

- File: `THE_PES_UNIVERSITY_ACT.pdf`, 16 pages.
- SHA-256: `1d66332a097f0b2033fffb8398df6328cd1641cd6a9d75e0f0fedf9656948038`.
- Source: official PES Important Information page links the candidate PDF; the first rendered page identifies the Karnataka Gazette / PES University Act.
- PyMuPDF extraction: zero text-extractable pages.
- Local OCR checks: `tesseract` and `ocrmypdf` commands not found; Python `pytesseract`, `easyocr`, `ocrmypdf`, and `paddleocr` unavailable; Windows `Windows.Media.Ocr.OcrEngine` unavailable.
- OCR tool/version: none; no OCR output was created.
- External OCR service: not used. No document was uploaded.
- Page numbering and OCR quality: not assessed because there is no OCR text.
- Classification remains `EXTRACTION_BLOCKED`; no evidence record was created from this file.

Next permitted action is to use an available local OCR tool in a later authorized workflow, preserve this source PDF, create a separate page-aligned OCR artifact, and manually compare sampled output to rendered pages. Uncertain tokens must be marked and reviewed before evidence use.

## Phase 8C resumption check (2026-11-13)

The existing Act PDF was rechecked with the installed PyMuPDF (`fitz`) extraction path: 16 pages, zero text-extractable pages. Local dependency checks found `fitz` installed, while the `tesseract` command and Python modules `pytesseract`, `easyocr`, `paddleocr`, and `ocrmypdf` are unavailable. No package installation, network OCR, external service, or API call was used. The original SHA-256 remains `1d66332a097f0b2033fffb8398df6328cd1641cd6a9d75e0f0fedf9656948038`; classification stays `EXTRACTION_BLOCKED`, with zero Act evidence records. Recovery requires an approved local OCR installation, separate page-aligned OCR output, and human comparison to the original rendered pages.

## Phase 8C Stage 2 local capability check (2026-11-13)

The Windows `tesseract` executable remains absent. `winget.exe` and bundled `pdftoppm.exe` are available; `choco` and `scoop` are absent. PyMuPDF is available, but `pytesseract`, `easyocr`, `paddleocr`, `ocrmypdf`, Pillow, and Windows OCR bridge modules are unavailable. Rendering is available locally through PyMuPDF/Poppler, but rendering is not OCR and no OCR was run. The Windows OCR capability query requires elevation and was not elevated; the prior check reported `Windows.Media.Ocr.OcrEngine` unavailable. No software was installed.

For later approved offline recovery, install Tesseract using the Windows installer referenced by upstream Tesseract documentation (UB Mannheim Windows builds), from an authorized package source, then verify the executable and language data locally. `pytesseract` alone is only a Python wrapper and does not provide the Tesseract engine. Keep OCR output in a separate page-aligned artifact, record engine/version/language and checksum, and compare against rendered source pages. Do not edit or replace the original Act PDF. Network/package installation and OCR were not performed in Stage 2.
