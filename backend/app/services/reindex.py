"""Safe re-indexing of retained PDFs into the separate local embedding collection."""

from __future__ import annotations

import hashlib
from pathlib import Path

from app.config import settings
from app.database.models import Document
from app.services.chunker import TokenChunker
from app.services.document_processor import extract_pdf_pages
from app.services.embeddings import EmbeddingError
from app.services.vector_store import ChromaVectorStore, VectorStoreError


class ReindexError(RuntimeError):
    pass


def read_managed_source(document: Document, upload_root: str | Path) -> bytes:
    """Read and checksum a document PDF only when it remains under upload_root."""
    if not document.storage_path:
        raise ReindexError("source_missing")
    configured_root = Path(upload_root).resolve()
    original_path = Path(document.storage_path)
    if original_path.is_symlink():
        raise ReindexError("source_symlink_rejected")
    source_path = original_path.resolve()
    try:
        source_path.relative_to(configured_root)
    except ValueError as exc:
        raise ReindexError("source_outside_upload_directory") from exc
    if not source_path.is_file():
        raise ReindexError("source_not_found")
    try:
        content = source_path.read_bytes()
    except OSError as exc:
        raise ReindexError("source_unreadable") from exc
    if hashlib.sha256(content).hexdigest() != document.sha256:
        raise ReindexError("source_checksum_mismatch")
    return content


def reindex_document(
    document: Document,
    content: bytes,
    *,
    embedder,
    vector_store: ChromaVectorStore,
    chunker: TokenChunker | None = None,
) -> int:
    """Rebuild one document's vectors in the current local collection, retaining its PDF and metadata."""
    if hashlib.sha256(content).hexdigest() != document.sha256:
        raise ReindexError("source_checksum_mismatch")
    try:
        pages = extract_pdf_pages(content, max_file_size_bytes=settings.max_upload_size_mb * 1024 * 1024)
        metadata = {
            "document_id": str(document.id),
            "document_name": document.document_name,
            "document_type": document.document_type,
            "academic_year": document.academic_year or "",
            "version": document.version,
            "effective_date": document.effective_date or "",
            "source_type": document.source_type,
            "verification_status": document.verification_status,
            "uploaded_by_user_id": document.uploaded_by_user_id or "",
        }
        chunker = chunker or TokenChunker(settings.chunk_size_tokens, settings.chunk_overlap_tokens)
        chunks = chunker.chunk_pages(pages, metadata)
        if not chunks:
            raise ReindexError("no_text_chunks")
        vectors = embedder.embed_texts([chunk.text for chunk in chunks])
        if len(vectors) != len(chunks):
            raise EmbeddingError("The local model returned an unexpected number of vectors.")
        vector_store.replace_document_chunks(document.id, chunks, vectors)
        indexed = vector_store.get_document_chunks(document.id)
        if len(indexed) != len(chunks):
            raise VectorStoreError("The reindexed chunk count could not be confirmed.")
    except (ReindexError, EmbeddingError, VectorStoreError):
        raise
    except Exception as exc:
        raise ReindexError("document_processing_failed") from exc

    document.page_count = len(pages)
    document.chunk_count = len(chunks)
    document.vector_sync_status = "synced"
    document.processing_status = "indexed"
    return len(chunks)
