# Phase 8B PDF inspection report

Inspection date: 2026-11-12. Original bytes were retained in the candidate repository and were not modified. Extraction used the existing `app.services.document_processor.extract_pdf_pages` (PyMuPDF); no OCR or OpenAI calls were made. Files are not registered in `evaluation/datasets/held_out/documents.json`.

| PDF | SHA-256 | Pages | Text pages | Extraction result | Scope and warnings |
|---|---|---:|---:|---|---|
| `documents/university_governance/THE_PES_UNIVERSITY_ACT.pdf` | `1d66332a097f0b2033fffb8398df6328cd1641cd6a9d75e0f0fedf9656948038` | 16 | 0 | PDF opens; `extract_pdf_pages` raises `EmptyPDFError: The PDF contains no extractable text.` | Visual first-page inspection shows Karnataka Gazette, Karnataka Act No. 16 of 2013, PES University Act 2012. Image-only scan. OCR is not in the current pipeline; all 16 pages require human-readable OCR review before evidence use. |
| `documents/university_governance/PES_University_Profroma_To_UGC.pdf` | `3558ac4222cea3a770a74dedc53510a74318b55842878ad9bf9ee1e7b9d01b06` | 475 | 475 | Existing extraction succeeded on all pages; 1,604 extracted sections, 922 distinct heuristic headings. | PDF metadata dates to 2014-03-18. First-page visual inspection shows UGC form heading and PES University address. Contains historical/mixed institutional references, including PES Institute of Technology. Section headings are heuristic; do not interpret this as a current B.Tech rulebook. Poppler logged missing display-font warnings for Symbol/ArialUnicode on sampled pages; text extraction succeeded. |
| `documents/academic_regulations/AIML-Curriculum-2025.pdf` | `c9fae00eb4c9e7ba6d0adb0686fe681a709119c72ace361dee707c0c58ec1c4f` | 118 | 118 | Existing extraction succeeded on all pages; 589 extracted sections, 280 distinct heuristic headings. | PDF metadata identifies PES University, Curriculum 2025-2026, creation date 2025-06-01. Cover has PES University branding. Page 3 identifies CSE (AI & ML), 2025-29 batch. Campus applicability is not stated in the checked pages. It is curriculum content, not general academic regulations. Headings are heuristic and need human review before annotation.

## Inspection coverage and limitations

- All three files opened with PyMuPDF and page counts were checked. Text extraction was run over every page of each text-bearing file.
- Representative first pages were rendered and visually reviewed for the Act, UGC Proforma, and AI/ML curriculum. This was not a full page-by-page visual proofread.
- The two text-bearing PDFs had no page with blank extracted text. This does not establish that every extracted character or heuristic heading is accurate.
- The Act's 16 image-only pages are the sole text-extraction warning. No OCR was run.
- None was imported. The Act is not text searchable; the UGC submission is archival and mixed-scope; the AI/ML curriculum's exact file link and campus applicability need independent confirmation. Phase 8A requires separate human authority review before official registry status becomes verified.
- Two current CSE PDFs were readable in the web PDF viewer, but local HTTPS download timed out. They were not locally hashed or run through the PyMuPDF pipeline; details are in `SOURCE_INVENTORY.md`.
