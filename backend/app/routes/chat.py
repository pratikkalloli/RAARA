"""Question answering API for retrieval-grounded academic information."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_db
from app.database.models import Document, User
from app.prompting.system_prompt import InvalidPromptConfigurationError, PromptType
from app.services.chat import AcademicChatService
from app.services.conversations import (
    ConversationNotFoundError,
    ConversationPersistenceError,
    ConversationService,
    IdempotencyConflictError,
)
from app.services.embeddings import EmbeddingError, create_embedding_service
from app.services.generator import (
    GenerationError,
    ModelAccessError,
    ModelUnavailableError,
    StructuredAnswer,
    create_answer_generator,
)
from app.services.document_summarizer import DocumentSummarizer
from app.services.factual_verifier import FactualConsistencyVerifier
from app.services.retriever import InvalidQuestionError, RetrievalError, Retriever
from app.services.vector_store import ChromaVectorStore, VectorStoreError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=4000)
    prompt_type: PromptType = PromptType.C
    top_k: int | None = Field(default=None, ge=1, le=50)
    metadata_filters: dict[str, Any] | None = None
    conversation_id: int | None = Field(default=None, ge=1)
    document_id: int | None = Field(default=None, ge=1)
    idempotency_key: UUID | None = None

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Question must not be blank.")
        return value


def get_chat_service(session: Session = Depends(get_db)) -> AcademicChatService:
    def lookup_document_states(document_ids: list[str]) -> dict[str, tuple[str, str]]:
        numeric_ids = [int(value) for value in document_ids if str(value).isdigit()]
        if not numeric_ids:
            return {}
        documents = session.scalars(select(Document).where(Document.id.in_(numeric_ids)))
        return {
            str(document.id): (document.verification_status, document.vector_sync_status)
            for document in documents
        }

    vector_store = ChromaVectorStore()
    embedding_service = create_embedding_service()
    generator = create_answer_generator()
    factual_verifier = FactualConsistencyVerifier(
        checker=getattr(generator, "verify_numerical_claims", None)
    )
    return AcademicChatService(
        retriever=Retriever(
            embedding_service,
            vector_store,
            document_state_lookup=lookup_document_states,
        ),
        generator=generator,
        document_summarizer=DocumentSummarizer(
            vector_store,
            generator,
            document_state_lookup=lookup_document_states,
            factual_verifier=factual_verifier,
        ),
        factual_verifier=factual_verifier,
    )


@router.post("/chat", response_model=StructuredAnswer, response_model_exclude_none=True)
def chat(
    request: ChatRequest,
    service: AcademicChatService = Depends(get_chat_service),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> StructuredAnswer:
    try:
        history = ConversationService(session)
        conversation = None
        conversation_context: list[dict[str, str]] = []
        if request.conversation_id is not None:
            conversation = history.get_owned(request.conversation_id, user.id)
            prior_answer = history.existing_exchange(
                conversation.id,
                request.idempotency_key,
                request.question,
            )
            if prior_answer is not None:
                return prior_answer
            conversation_context = history.recent_context(conversation.id)

        metadata_filters = dict(request.metadata_filters or {})
        if user.role != "admin":
            metadata_filters["uploaded_by_user_id"] = user.id
        accessible_statement = select(Document).where(Document.verification_status != "rejected")
        if user.role != "admin":
            accessible_statement = accessible_statement.where(Document.uploaded_by_user_id == user.id)
        accessible_documents = list(session.scalars(
            accessible_statement.order_by(Document.created_at.desc(), Document.id.desc()).limit(100)
        ))
        if request.document_id is not None:
            selected_document = session.scalar(accessible_statement.where(Document.id == request.document_id))
            if selected_document is None:
                raise HTTPException(status_code=404, detail="The selected document was not found in your document library.")
            if all(document.id != selected_document.id for document in accessible_documents):
                accessible_documents.append(selected_document)
        answer_options = {
            "top_k": request.top_k,
            "metadata_filters": metadata_filters or None,
            "prompt_type": request.prompt_type,
            "available_documents": [
                {
                    "document_id": str(document.id),
                    "document_name": document.document_name,
                    "filename": document.filename,
                    "document_type": document.document_type,
                    "academic_year": document.academic_year or "",
                    "version": document.version or "",
                    "verification_status": document.verification_status,
                    "source_type": document.source_type or "",
                    "processing_status": document.processing_status,
                    "vector_sync_status": document.vector_sync_status,
                }
                for document in accessible_documents
            ],
        }
        document_id = request.document_id
        if document_id is not None:
            answer_options["document_id"] = document_id
        if conversation is not None:
            answer_options["conversation_history"] = conversation_context
        answer = service.answer(request.question, **answer_options)
        if conversation is not None:
            answer = history.persist_exchange(
                conversation,
                question=request.question,
                answer=answer,
                idempotency_key=request.idempotency_key,
            )
        return answer
    except HTTPException:
        raise
    except ConversationNotFoundError:
        raise HTTPException(status_code=404, detail="Conversation not found.") from None
    except IdempotencyConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except ConversationPersistenceError:
        raise HTTPException(status_code=503, detail="Conversation history is temporarily unavailable.") from None
    except InvalidQuestionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except InvalidPromptConfigurationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ModelUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (EmbeddingError, ModelAccessError, GenerationError, RetrievalError, VectorStoreError) as exc:
        logger.error("Chat request could not be completed (exception_type=%s)", type(exc).__name__)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Unexpected chat request failure (exception_type=%s)", type(exc).__name__)
        raise HTTPException(status_code=500, detail="The question could not be answered.") from exc


