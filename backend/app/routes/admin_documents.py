from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth.dependencies import get_db, require_admin
from app.database.models import Document, User
from app.schemas.documents import DocumentSummary, VerificationDecisionRequest
from app.services.document_verification import (
    DocumentNotFoundError,
    DocumentVerificationService,
    InvalidVerificationTransitionError,
    VectorSynchronizationPendingError,
    VerificationPersistenceError,
)
from app.services.vector_store import ChromaVectorStore, VectorStoreError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin/documents", tags=["admin documents"])


def _summary(document: Document, uploader_username: str | None) -> DocumentSummary:
    return DocumentSummary(
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
        uploaded_by_username=uploader_username,
        page_count=document.page_count,
        chunk_count=document.chunk_count,
        reviewed_by_user_id=document.reviewed_by_user_id,
        reviewed_at=document.reviewed_at,
        review_note=document.review_note,
    )


@router.get("/pending", response_model=list[DocumentSummary])
def pending_documents(
    _admin: User = Depends(require_admin),
    session: Session = Depends(get_db),
) -> list[DocumentSummary]:
    try:
        rows = session.execute(
            select(Document, User.username)
            .outerjoin(User, User.id == Document.uploaded_by_user_id)
            .where(
                Document.verification_status == "unverified",
                Document.vector_sync_status == "synced",
                Document.processing_status == "indexed",
            )
            .order_by(Document.created_at.asc(), Document.id.asc())
        ).all()
    except SQLAlchemyError as exc:
        logger.error("Pending document query failed (exception_type=%s)", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Document review is temporarily unavailable.") from None
    return [_summary(document, username) for document, username in rows]


@router.post("/{document_id}/verification", response_model=DocumentSummary)
def decide_document_verification(
    document_id: int,
    request: VerificationDecisionRequest,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_db),
) -> DocumentSummary:
    try:
        vector_store = ChromaVectorStore()
    except VectorStoreError:
        raise HTTPException(status_code=503, detail="The document vector store is temporarily unavailable.") from None
    service = DocumentVerificationService(session, vector_store)
    try:
        document = service.decide(
            document_id,
            decision=request.decision,
            reviewer_id=admin.id,
            review_note=request.review_note,
        )
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found.") from None
    except InvalidVerificationTransitionError:
        raise HTTPException(
            status_code=409,
            detail="Document is not awaiting review or its vector synchronization requires retry.",
        ) from None
    except VerificationPersistenceError:
        raise HTTPException(status_code=503, detail="The review decision could not be saved.") from None
    except VectorSynchronizationPendingError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "message": str(exc),
                "document_id": document_id,
                "verification_status": exc.verification_status,
                "vector_sync_status": "pending",
                "retry_endpoint": f"/api/admin/documents/{document_id}/verification/retry-sync",
            },
        ) from None
    return _summary(document, _get_uploader_username(session, document))


@router.post("/{document_id}/verification/retry-sync", response_model=DocumentSummary)
def retry_document_vector_sync(
    document_id: int,
    _admin: User = Depends(require_admin),
    session: Session = Depends(get_db),
) -> DocumentSummary:
    try:
        vector_store = ChromaVectorStore()
    except VectorStoreError:
        raise HTTPException(status_code=503, detail="The document vector store is temporarily unavailable.") from None
    service = DocumentVerificationService(session, vector_store)
    try:
        document = service.retry_synchronization(document_id)
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found.") from None
    except InvalidVerificationTransitionError:
        raise HTTPException(status_code=409, detail="Document has no pending verification synchronization.") from None
    except VerificationPersistenceError:
        raise HTTPException(status_code=503, detail="The synchronization state could not be loaded.") from None
    except VectorSynchronizationPendingError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "message": str(exc),
                "document_id": document_id,
                "verification_status": exc.verification_status,
                "vector_sync_status": "pending",
                "retry_endpoint": f"/api/admin/documents/{document_id}/verification/retry-sync",
            },
        ) from None
    return _summary(document, _get_uploader_username(session, document))


def _get_uploader_username(session: Session, document: Document) -> str | None:
    if document.uploaded_by_user_id is None:
        return None
    uploader = session.get(User, document.uploaded_by_user_id)
    return uploader.username if uploader is not None else None
