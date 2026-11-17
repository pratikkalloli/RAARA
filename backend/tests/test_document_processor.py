import pytest

from app.services.document_processor import (
    DocumentTooLargeError,
    EmptyPDFError,
    InvalidPDFError,
    extract_pdf_pages,
)


def test_extracts_text_page_numbers_and_headings(synthetic_pdf):
    pages = extract_pdf_pages(synthetic_pdf)

    assert [page.page_number for page in pages] == [1, 2]
    assert "SYNTHETIC TEST DOCUMENT" in pages[0].text
    assert any("Attendance Requirements" in section.heading for section in pages[0].sections)
    assert any("Examination Guidance" in section.heading for section in pages[1].sections)
    assert "NOT AN OFFICIAL REGULATION" in pages[0].text


def test_rejects_invalid_pdf_bytes():
    with pytest.raises(InvalidPDFError):
        extract_pdf_pages(b"not a PDF")


def test_rejects_valid_pdf_without_extractable_text(empty_pdf):
    with pytest.raises(EmptyPDFError):
        extract_pdf_pages(empty_pdf)


def test_enforces_pdf_size_limit(synthetic_pdf):
    with pytest.raises(DocumentTooLargeError):
        extract_pdf_pages(synthetic_pdf, max_file_size_bytes=10)


