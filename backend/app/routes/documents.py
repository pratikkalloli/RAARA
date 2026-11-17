"""Document upload endpoint for the Phase 2 ingestion pipeline."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_db, require_authenticated_user
from app.config import settings
from app.database.models import Document, User
from app.schemas.documents import DocumentSummary
from app.services.document_processor import (
    DocumentProcessingError,
    DocumentTooLargeError,
)
from app.services.embeddings import EmbeddingConfigurationError, EmbeddingError, create_embedding_service
from app.services.ingestion import DocumentIngestionService, DuplicateDocumentError, IngestionError
from app.services.vector_store import ChromaVectorStore, VectorStoreError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["documents"])


def get_ingestion_service(session: Session = Depends(get_db)) -> DocumentIngestionService:
    try:
        return DocumentIngestionService(
            session,
            embedder=create_embedding_service(),
            vector_store=ChromaVectorStore(),
        )
    except Exception as exc:
        logger.error("Document ingestion dependencies unavailable (exception_type=%s)", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Document processing dependencies are unavailable.") from None


@router.get("", response_model=list[DocumentSummary])
def list_documents(
    verification_status: Literal["unverified", "verified", "rejected"] | None = Query(default=None),
    user: User = Depends(require_authenticated_user),
    session: Session = Depends(get_db),
) -> list[DocumentSummary]:
    query = select(Document, User.username).outerjoin(User, User.id == Document.uploaded_by_user_id)
    if user.role != "admin":
        query = query.where(Document.uploaded_by_user_id == user.id)
    if verification_status is not None:
        query = query.where(Document.verification_status == verification_status)
    try:
        rows = session.execute(query.order_by(Document.created_at.desc(), Document.id.desc())).all()
    except SQLAlchemyError as exc:
        logger.error("Document list query failed (exception_type=%s)", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Documents are temporarily unavailable.") from None
    return [
        DocumentSummary(
            document_id=document.id,
            document_name=document.document_name,
            document_type=document.document_type,
            academic_year=document.academic_year,
            version=document.version,
            effective_date=document.effective_date,
            source_type=document.source_type,
            verification_status=document.verification_status,
            vector_sync_status=document.vector_sync_status,
            processing_status=document.processing_status,
            uploaded_at=document.created_at,
            uploaded_by_user_id=document.uploaded_by_user_id,
            uploaded_by_username=username,
            page_count=document.page_count,
            chunk_count=document.chunk_count,
            reviewed_by_user_id=document.reviewed_by_user_id,
            reviewed_at=document.reviewed_at,
            review_note=document.review_note,
        )
        for document, username in rows
    ]


@router.delete("/{document_id}", status_code=204)
def delete_document(
    document_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> Response:
    document = session.get(Document, document_id)
    if document is None or (user.role != "admin" and document.uploaded_by_user_id != user.id):
        raise HTTPException(status_code=404, detail="Document not found.") from None

    managed_root = Path(settings.upload_dir).resolve()
    stored_path: Path | None = None
    if document.storage_path:
        stored_path = Path(document.storage_path).resolve()
        try:
            stored_path.relative_to(managed_root)
        except ValueError:
            logger.warning("Refusing document delete with unmanaged storage path (document_id=%s)", document.id)
            raise HTTPException(status_code=409, detail="This document cannot be safely deleted from managed storage.") from None
        if stored_path.exists() and not stored_path.is_file():
            raise HTTPException(status_code=409, detail="This document cannot be safely deleted from managed storage.") from None

    try:
        vector_store = ChromaVectorStore()
        vector_store.delete_document(document.id)
    except VectorStoreError:
        raise HTTPException(status_code=503, detail="The document index could not be safely deleted. Please retry.") from None

    session.delete(document)
    try:
        session.commit()
    except SQLAlchemyError as exc:
        session.rollback()
        # The vectors are already gone. Fail closed so a surviving row cannot be retrieved.
        try:
            remaining = session.get(Document, document_id)
            if remaining is not None:
                remaining.vector_sync_status = "pending"
                session.commit()
        except SQLAlchemyError:
            session.rollback()
        logger.error("Document row deletion failed after vector removal (exception_type=%s)", type(exc).__name__)
        raise HTTPException(status_code=503, detail="The document record could not be safely deleted. Please retry.") from None

    if stored_path is not None:
        try:
            stored_path.unlink(missing_ok=True)
        except OSError as exc:
            logger.error("Uploaded PDF cleanup failed after document deletion (exception_type=%s)", type(exc).__name__)
    return Response(status_code=204)


@router.post("/upload", status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form("policy"),
    document_name: str | None = Form(None),
    academic_year: str | None = Form(None),
    version: str | None = Form(None),
    effective_date: str | None = Form(None),
    source_type: str = Form("uploaded"),
    service: DocumentIngestionService = Depends(get_ingestion_service),
    user: User = Depends(get_current_user),
) -> dict[str, object]:
    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files can be uploaded.")
    try:
        content = await file.read(settings.max_upload_size_mb * 1024 * 1024 + 1)
        document = service.ingest_pdf(
            content,
            filename=filename,
            document_name=document_name,
            document_type=document_type,
            academic_year=academic_year,
            version=version,
            effective_date=effective_date,
            source_type=source_type,
            uploaded_by_user_id=user.id,
        )
        return {
            "id": document.id,
            "document_id": str(document.id),
            "document_name": document.document_name,
            "document_type": document.document_type,
            "academic_year": document.academic_year,
            "version": document.version,
            "effective_date": document.effective_date,
            "source_type": document.source_type,
            "verification_status": document.verification_status,
            "processing_status": document.processing_status,
            "page_count": document.page_count,
            "chunk_count": document.chunk_count,
        }
    except DocumentTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except DocumentProcessingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DuplicateDocumentError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except EmbeddingConfigurationError as exc:
        logger.warning("Document upload is not configured (exception_type=%s)", type(exc).__name__)
        raise HTTPException(status_code=503, detail=str(exc)) from None
    except (EmbeddingError, VectorStoreError) as exc:
        logger.error("Document upload processing dependency failed (exception_type=%s)", type(exc).__name__)
        raise HTTPException(status_code=503, detail=str(exc)) from None
    except IngestionError as exc:
        logger.exception("Document upload failed")
        raise HTTPException(status_code=500, detail="The document could not be processed.") from exc
    except Exception as exc:
        logger.exception("Unexpected document upload error")
        raise HTTPException(status_code=500, detail="The document could not be processed.") from exc
    finally:
        await file.close()
