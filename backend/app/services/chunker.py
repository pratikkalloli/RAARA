"""Token-aware chunking with controlled overlap and page/section metadata."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import tiktoken

from app.services.document_processor import ExtractedPage, ExtractedSection


@dataclass(frozen=True)
class TextChunk:
    text: str
    page_number: int
    section: str
    chunk_index: int
    token_count: int
    metadata: dict[str, Any]


class TokenChunker:
    def __init__(
        self,
        chunk_size: int = 700,
        overlap: int = 100,
        encoding_name: str = "cl100k_base",
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if overlap < 0 or overlap >= chunk_size:
            raise ValueError("overlap must be non-negative and less than chunk_size")
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.encoding = tiktoken.get_encoding(encoding_name)

    def chunk_pages(
        self,
        pages: Iterable[ExtractedPage],
        metadata: dict[str, Any],
    ) -> list[TextChunk]:
        chunks: list[TextChunk] = []
        chunk_index = 0
        step = self.chunk_size - self.overlap

        for page in pages:
            sections = page.sections or (ExtractedSection("", page.text),)
            for section in sections:
                tokens = self.encoding.encode(section.text)
                if not tokens:
                    continue
                start = 0
                while start < len(tokens):
                    token_slice = tokens[start : start + self.chunk_size]
                    text = self.encoding.decode(token_slice).strip()
                    if text:
                        chunk_metadata = {
                            **metadata,
                            "page_number": int(page.page_number),
                            "section": str(section.heading or ""),
                        }
                        chunks.append(
                            TextChunk(
                                text=text,
                                page_number=page.page_number,
                                section=section.heading or "",
                                chunk_index=chunk_index,
                                token_count=len(token_slice),
                                metadata=chunk_metadata,
                            )
                        )
                        chunk_index += 1
                    if start + self.chunk_size >= len(tokens):
                        break
                    start += step
        return chunks


def chunk_pages(
    pages: Iterable[ExtractedPage],
    metadata: dict[str, Any],
    *,
    chunk_size: int = 700,
    overlap: int = 100,
) -> list[TextChunk]:
    """Convenience wrapper using the project defaults unless explicitly overridden."""
    return TokenChunker(chunk_size, overlap).chunk_pages(pages, metadata)
