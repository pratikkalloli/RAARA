"""Administrator review lifecycle with fail-closed vector metadata synchronization."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Literal, Protocol

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.models import Document
from app.services.vector_store import VectorStoreError

logger = logging.getLogger(__name__)
VerificationDecision = Literal["verified", "rejected"]


class DocumentVerificationError(RuntimeError):
    pass


class DocumentNotFoundError(DocumentVerificationError):
    pass


class InvalidVerificationTransitionError(DocumentVerificationError):
    pass


class VerificationPersistenceError(DocumentVerificationError):
    pass


class VectorSynchronizationPendingError(DocumentVerificationError):
    def __init__(self, verification_status: str) -> None:
        super().__init__("The decision was recorded, but vector metadata synchronization is pending.")
        self.verification_status = verification_status


class MetadataStore(Protocol):
    def update_document_metadata(self, document_id: int | str, updates: dict[str, object]) -> int: ...


class DocumentVerificationService:
    def __init__(self, session: Session, vector_store: MetadataStore) -> None:
        self.session = session
        self.vector_store = vector_store

    def decide(
        self,
        document_id: int,
        *,
        decision: VerificationDecision,
        reviewer_id: int,
        review_note: str | None = None,
    ) -> Document:
        document = self._load_document(document_id)
        if decision not in ("verified", "rejected"):
            raise InvalidVerificationTransitionError
        if document.verification_status != "unverified" or document.vector_sync_status != "synced":
            raise InvalidVerificationTransitionError

        document.verification_status = decision
        document.reviewed_by_user_id = reviewer_id
        document.reviewed_at = datetime.now(timezone.utc)
        document.review_note = review_note.strip() if review_note and review_note.strip() else None
        document.vector_sync_status = "pending"
        self._commit_or_raise()
        return self._synchronize(document)

    def retry_synchronization(self, document_id: int) -> Document:
        document = self._load_document(document_id)
        if document.vector_sync_status != "pending" or document.verification_status not in ("verified", "rejected"):
            raise InvalidVerificationTransitionError
        return self._synchronize(document)

    def _synchronize(self, document: Document) -> Document:
        try:
            updated_count = self.vector_store.update_document_metadata(
                document.id,
                {"verification_status": document.verification_status},
            )
            if document.chunk_count is None or updated_count != document.chunk_count:
                raise VectorStoreError("The number of synchronized chunks did not match the document record.")
        except Exception as exc:
            logger.error(
                "Document vector synchronization remains pending (document_id=%s, exception_type=%s)",
                document.id,
                type(exc).__name__,
            )
            self.session.refresh(document)
            raise VectorSynchronizationPendingError(document.verification_status) from None

        document.vector_sync_status = "synced"
        try:
            self.session.commit()
            self.session.refresh(document)
        except SQLAlchemyError as exc:
            self.session.rollback()
            logger.error(
                "Document vector synchronization marker could not be committed (document_id=%s, exception_type=%s)",
                document.id,
                type(exc).__name__,
            )
            raise VectorSynchronizationPendingError(document.verification_status) from None
        return document

    def _commit_or_raise(self) -> None:
        try:
            self.session.commit()
        except SQLAlchemyError as exc:
            self.session.rollback()
            logger.error("Document verification decision could not be committed (exception_type=%s)", type(exc).__name__)
            raise VerificationPersistenceError from None

    def _load_document(self, document_id: int) -> Document:
        try:
            document = self.session.get(Document, document_id)
        except SQLAlchemyError as exc:
            logger.error("Document review lookup failed (exception_type=%s)", type(exc).__name__)
            raise VerificationPersistenceError from None
        if document is None:
            raise DocumentNotFoundError
        return document
