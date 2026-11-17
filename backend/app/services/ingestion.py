"""Orchestrate validation, PDF extraction, chunking, embedding and durable indexing."""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database.models import Document
from app.services.chunker import TextChunk, TokenChunker
from app.services.document_processor import (
    DocumentProcessingError,
    extract_pdf_pages,
)
from app.services.embeddings import EmbeddingError, create_embedding_service
from app.services.vector_store import ChromaVectorStore, VectorStoreError

logger = logging.getLogger(__name__)


class DuplicateDocumentError(ValueError):
    pass


class IngestionError(RuntimeError):
    pass


class Embedder(Protocol):
    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...


class VectorStore(Protocol):
    def add_chunks(self, document_id: int | str, chunks: list[TextChunk], embeddings: list[list[float]]) -> list[str]: ...
    def delete(self, ids: list[str]) -> None: ...
    def delete_document(self, document_id: int | str) -> None: ...


class DocumentIngestionService:
    def __init__(
        self,
        session: Session,
        *,
        embedder: Embedder | None = None,
        vector_store: VectorStore | None = None,
        chunker: TokenChunker | None = None,
        storage_dir: str | Path | None = None,
        max_file_size_bytes: int | None = None,
    ) -> None:
        self.session = session
        self.embedder = embedder or create_embedding_service()
        self.vector_store = vector_store or ChromaVectorStore()
        self.chunker = chunker or TokenChunker(settings.chunk_size_tokens, settings.chunk_overlap_tokens)
        self.storage_dir = Path(storage_dir or settings.upload_dir).resolve()
        self.max_file_size_bytes = max_file_size_bytes or settings.max_upload_size_mb * 1024 * 1024

    def ingest_pdf(
        self,
        content: bytes,
        *,
        filename: str,
        document_name: str | None = None,
        document_type: str = "policy",
        academic_year: str | None = None,
        version: str | None = None,
        effective_date: str | None = None,
        source_type: str = "uploaded",
        uploaded_by_user_id: int | None = None,
    ) -> Document:
        safe_filename = Path(filename.replace("\\", "/")).name.strip()
        if not safe_filename or not safe_filename.lower().endswith(".pdf"):
            raise DocumentProcessingError("Only PDF files can be ingested.")
        if len(content) > self.max_file_size_bytes:
            from app.services.document_processor import DocumentTooLargeError

            raise DocumentTooLargeError("The uploaded PDF exceeds the configured file-size limit.")

        digest = hashlib.sha256(content).hexdigest()
        try:
            pages = extract_pdf_pages(content, max_file_size_bytes=self.max_file_size_bytes)
            existing = self.session.scalar(select(Document).where(Document.sha256 == digest))
            if existing:
                raise DuplicateDocumentError("This exact PDF has already been uploaded.")

            resolved_name = (document_name or safe_filename).strip()
            if not resolved_name:
                raise DocumentProcessingError("A document name is required.")
            resolved_type = document_type.strip()
            if not resolved_type:
                raise DocumentProcessingError("A document type is required.")
            resolved_version = self._resolve_version(resolved_name, resolved_type, version)

            document = Document(
                filename=safe_filename[:255],
                document_name=resolved_name[:255],
                sha256=digest,
                document_type=resolved_type[:64],
                academic_year=(academic_year.strip()[:32] if academic_year and academic_year.strip() else None),
                version=resolved_version[:32],
                effective_date=(effective_date.strip()[:32] if effective_date and effective_date.strip() else None),
                source_type=source_type.strip()[:64] or "uploaded",
                verification_status="unverified",
                vector_sync_status="synced",
                uploaded_by_user_id=uploaded_by_user_id,
                processing_status="processing",
                page_count=len(pages),
            )
            self.session.add(document)
            self.session.flush()

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
            chunks = self.chunker.chunk_pages(pages, metadata)
            if not chunks:
                raise DocumentProcessingError("The PDF did not produce any text chunks.")
            embeddings = self.embedder.embed_texts([chunk.text for chunk in chunks])
            if len(embeddings) != len(chunks):
                raise EmbeddingError("The embedding provider returned an unexpected number of vectors.")

            self.storage_dir.mkdir(parents=True, exist_ok=True)
            storage_path = self.storage_dir / f"{document.id}-{digest[:12]}.pdf"
            storage_path.write_bytes(content)
            vector_ids = self.vector_store.add_chunks(document.id, chunks, embeddings)
            document.storage_path = str(storage_path)
            document.chunk_count = len(chunks)
            document.processing_status = "indexed"
            self.session.commit()
            logger.info(
                "Ingested document id=%s name=%r version=%s pages=%d chunks=%d status=%s",
                document.id,
                document.document_name,
                document.version,
                len(pages),
                len(chunks),
                document.verification_status,
            )
            return document
        except (DocumentProcessingError, DuplicateDocumentError, EmbeddingError, VectorStoreError):
            self.session.rollback()
            self._cleanup_partial("document" in locals() and document.id is not None, locals())
            raise
        except Exception as exc:
            self.session.rollback()
            self._cleanup_partial("document" in locals() and document.id is not None, locals())
            logger.exception("Unexpected failure while ingesting PDF %r", safe_filename)
            raise IngestionError("The document could not be ingested.") from exc

    def _cleanup_partial(self, has_document: bool, local_values: dict[str, object]) -> None:
        """Best-effort cleanup must not mask the original ingestion failure."""
        if has_document:
            try:
                self.vector_store.delete_document(local_values["document"].id)
            except Exception as exc:
                logger.error("Partial vector cleanup failed (exception_type=%s)", type(exc).__name__)
        elif "vector_ids" in local_values:
            try:
                self.vector_store.delete(local_values["vector_ids"])
            except Exception as exc:
                logger.error("Partial vector cleanup failed (exception_type=%s)", type(exc).__name__)
        storage_path = local_values.get("storage_path")
        if storage_path is not None:
            try:
                storage_path.unlink(missing_ok=True)
            except OSError as exc:
                logger.error("Partial uploaded-file cleanup failed (exception_type=%s)", type(exc).__name__)

    def _resolve_version(self, document_name: str, document_type: str, requested: str | None) -> str:
        existing_versions = list(
            self.session.scalars(
                select(Document.version).where(
                    Document.document_name == document_name,
                    Document.document_type == document_type,
                )
            )
        )
        if requested:
            requested = requested.strip()
            if not requested:
                raise DocumentProcessingError("A supplied version cannot be blank.")
            if requested in existing_versions:
                raise DuplicateDocumentError("That document version already exists.")
            return requested
        numeric_versions = [int(value) for value in existing_versions if re.fullmatch(r"\d+", value or "")]
        return str(max(numeric_versions, default=0) + 1)
