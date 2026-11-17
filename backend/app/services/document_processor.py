"""Extract clean, page-aware text and section headings from PDF documents."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import pymupdf as fitz

logger = logging.getLogger(__name__)
PDF_SIGNATURE = b"%PDF-"


class DocumentProcessingError(ValueError):
    """Base class for expected document validation and extraction errors."""


class InvalidPDFError(DocumentProcessingError):
    pass


class EmptyPDFError(DocumentProcessingError):
    pass


class DocumentTooLargeError(DocumentProcessingError):
    pass


@dataclass(frozen=True)
class ExtractedSection:
    heading: str
    text: str


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int
    text: str
    sections: tuple[ExtractedSection, ...]


_CLAUSE_HEADING = re.compile(
    r"^(?:(?:chapter|section|part|article)\s+[\w.-]+|\d+(?:\.\d+)*[.)]?)\s+\S+",
    re.IGNORECASE,
)


def clean_text(value: str) -> str:
    """Normalize whitespace while retaining line breaks needed for headings."""
    value = value.replace("\u00a0", " ").replace("\u00ad", "")
    cleaned_lines = [re.sub(r"[ \t\f\v]+", " ", line).strip() for line in value.splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(cleaned_lines)).strip()


def _looks_like_heading(text: str, font_size: float, is_bold: bool) -> bool:
    if not text or len(text) > 140:
        return False
    if font_size >= 14 or _CLAUSE_HEADING.match(text):
        return True
    letters = [character for character in text if character.isalpha()]
    return bool(letters) and text.upper() == text and len(letters) >= 4 and is_bold


def _page_lines(page: fitz.Page) -> list[tuple[str, float, bool]]:
    """Read text lines with basic font cues, falling back to plain page text."""
    lines: list[tuple[str, float, bool]] = []
    try:
        page_dict = page.get_text("dict", sort=True)
        for block in page_dict.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                line_text = "".join(span.get("text", "") for span in spans)
                if not line_text.strip():
                    continue
                size = max((float(span.get("size", 0)) for span in spans), default=0)
                bold = any("bold" in str(span.get("font", "")).lower() for span in spans)
                lines.append((line_text, size, bold))
    except Exception:
        logger.exception("Unable to read PDF text layout; falling back to plain page text")

    if lines:
        return lines
    return [(line, 0, False) for line in page.get_text("text", sort=True).splitlines()]


def extract_pdf_pages(
    content: bytes,
    *,
    max_file_size_bytes: int | None = None,
) -> list[ExtractedPage]:
    """Extract non-empty PDF text while preserving 1-based page and section data."""
    if not content:
        raise EmptyPDFError("The uploaded PDF is empty.")
    if max_file_size_bytes is not None and len(content) > max_file_size_bytes:
        raise DocumentTooLargeError("The uploaded PDF exceeds the configured file-size limit.")
    if PDF_SIGNATURE not in content[:1024]:
        raise InvalidPDFError("The uploaded file does not contain a valid PDF signature.")

    try:
        pdf = fitz.open(stream=content, filetype="pdf")
    except Exception as exc:
        logger.info("PyMuPDF rejected uploaded PDF: %s", exc)
        raise InvalidPDFError("The uploaded file could not be opened as a PDF.") from exc

    try:
        if pdf.needs_pass:
            raise InvalidPDFError("Password-protected PDFs are not supported.")
        if pdf.page_count == 0:
            raise EmptyPDFError("The PDF contains no pages.")

        result: list[ExtractedPage] = []
        active_section = ""
        has_text = False
        for page_index, page in enumerate(pdf, start=1):
            current_lines: list[str] = []
            page_sections: list[ExtractedSection] = []
            section_heading = active_section
            section_lines: list[str] = []

            def save_section() -> None:
                nonlocal section_lines
                section_text = clean_text("\n".join(section_lines))
                if section_text:
                    page_sections.append(ExtractedSection(section_heading, section_text))
                section_lines = []

            for raw_line, font_size, is_bold in _page_lines(page):
                line = clean_text(raw_line)
                if not line:
                    if current_lines and current_lines[-1] != "":
                        current_lines.append("")
                    if section_lines and section_lines[-1] != "":
                        section_lines.append("")
                    continue

                if _looks_like_heading(line, font_size, is_bold):
                    save_section()
                    section_heading = line[:160]
                    active_section = section_heading
                current_lines.append(line)
                section_lines.append(line)

            save_section()
            page_text = clean_text("\n".join(current_lines))
            if page_text:
                has_text = True
            result.append(ExtractedPage(page_index, page_text, tuple(page_sections)))

        if not has_text:
            raise EmptyPDFError("The PDF contains no extractable text.")
        return result
    finally:
        pdf.close()
