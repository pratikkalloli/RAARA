"""User-owned conversation persistence and idempotent chat exchanges."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import case, desc, func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.database.models import Conversation, ConversationMessage
from app.schemas.conversations import ConversationDetail, ConversationMessageView, ConversationSummary
from app.services.generator import StructuredAnswer

logger = logging.getLogger(__name__)


class ConversationNotFoundError(LookupError):
    pass


class ConversationPersistenceError(RuntimeError):
    pass


class IdempotencyConflictError(RuntimeError):
    pass


class ConversationService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, *, user_id: int, title: str | None = None) -> ConversationSummary:
        conversation = Conversation(user_id=user_id, title=title or "New conversation")
        self.session.add(conversation)
        try:
            self.session.commit()
            self.session.refresh(conversation)
            return _summary(conversation, 0, 0)
        except SQLAlchemyError as exc:
            self.session.rollback()
            logger.error("Conversation creation failed (exception_type=%s)", type(exc).__name__)
            raise ConversationPersistenceError from None

    def list_for_user(self, user_id: int) -> list[ConversationSummary]:
        try:
            rows = self.session.execute(
                select(
                    Conversation,
                    func.count(ConversationMessage.id),
                    func.coalesce(
                        func.sum(case((ConversationMessage.role == "user", 1), else_=0)),
                        0,
                    ),
                )
                .outerjoin(ConversationMessage, ConversationMessage.conversation_id == Conversation.id)
                .where(Conversation.user_id == user_id)
                .group_by(Conversation.id)
                .order_by(desc(Conversation.updated_at), desc(Conversation.id))
            ).all()
        except SQLAlchemyError as exc:
            logger.error("Conversation listing failed (exception_type=%s)", type(exc).__name__)
            raise ConversationPersistenceError from None
        return [
            _summary(conversation, int(message_count), int(question_count))
            for conversation, message_count, question_count in rows
        ]

    def get_owned(self, conversation_id: int, user_id: int) -> Conversation:
        try:
            conversation = self.session.scalar(
                select(Conversation).where(
                    Conversation.id == conversation_id,
                    Conversation.user_id == user_id,
                )
            )
        except SQLAlchemyError as exc:
            logger.error("Conversation ownership lookup failed (exception_type=%s)", type(exc).__name__)
            raise ConversationPersistenceError from None
        if conversation is None:
            raise ConversationNotFoundError
        return conversation

    def detail(self, conversation_id: int, user_id: int) -> ConversationDetail:
        conversation = self.get_owned(conversation_id, user_id)
        try:
            messages = list(
                self.session.scalars(
                    select(ConversationMessage)
                    .where(ConversationMessage.conversation_id == conversation.id)
                    .order_by(ConversationMessage.created_at.asc(), ConversationMessage.id.asc())
                )
            )
        except SQLAlchemyError as exc:
            logger.error("Conversation messages could not be loaded (exception_type=%s)", type(exc).__name__)
            raise ConversationPersistenceError from None
        return ConversationDetail(
            **_summary(
                conversation,
                len(messages),
                sum(message.role == "user" for message in messages),
            ).model_dump(),
            messages=[ConversationMessageView.model_validate(message, from_attributes=True) for message in messages],
        )

    def recent_context(
        self,
        conversation_id: int,
        *,
        max_messages: int | None = None,
        max_chars: int | None = None,
    ) -> list[dict[str, object]]:
        """Return bounded, chronological conversation context; caller must check ownership first."""
        message_limit = settings.conversation_history_max_messages if max_messages is None else max_messages
        char_limit = settings.conversation_history_max_chars if max_chars is None else max_chars
        if message_limit <= 0 or char_limit <= 0:
            return []
        try:
            rows = list(self.session.scalars(
                select(ConversationMessage)
                .where(ConversationMessage.conversation_id == conversation_id)
                .order_by(desc(ConversationMessage.created_at), desc(ConversationMessage.id))
                .limit(message_limit)
            ))
        except SQLAlchemyError as exc:
            logger.error("Conversation context lookup failed (exception_type=%s)", type(exc).__name__)
            raise ConversationPersistenceError from None
        rows.reverse()
        remaining = char_limit
        context: list[dict[str, object]] = []
        for row in rows:
            if remaining <= 0:
                break
            content = row.content[:remaining]
            if content:
                item: dict[str, object] = {"role": row.role, "content": content}
                # Preserve a small amount of application-generated response
                # state so the model can distinguish a supported answer from
                # an abstention. Never treat an abstention as factual context.
                if row.role == "assistant" and isinstance(row.structured_response, dict):
                    status = row.structured_response.get("status")
                    evidence = row.structured_response.get("evidence")
                    if isinstance(status, str) and status in {
                        "SUPPORTED", "PARTIALLY_SUPPORTED", "NOT_FOUND",
                        "CONFLICTING_SOURCES", "CONVERSATIONAL",
                    }:
                        item["answer_status"] = status
                    if isinstance(evidence, list):
                        item["evidence_count"] = len(evidence)
                context.append(item)
                remaining -= len(content)
        return context

    def existing_exchange(
        self,
        conversation_id: int,
        idempotency_key: UUID | None,
        question: str | None = None,
    ) -> StructuredAnswer | None:
        if idempotency_key is None:
            return None
        try:
            user_message = self.session.scalar(
                select(ConversationMessage).where(
                    ConversationMessage.conversation_id == conversation_id,
                    ConversationMessage.role == "user",
                    ConversationMessage.idempotency_key == str(idempotency_key),
                )
            )
            if user_message is None:
                return None
            if question is not None and user_message.content != question:
                raise IdempotencyConflictError("This idempotency key was already used for another question.")
            assistant_message = self.session.scalar(
                select(ConversationMessage)
                .where(
                    ConversationMessage.conversation_id == conversation_id,
                    ConversationMessage.role == "assistant",
                    ConversationMessage.idempotency_key == str(idempotency_key),
                )
                .limit(1)
            )
            if assistant_message is None or assistant_message.structured_response is None:
                raise IdempotencyConflictError("The prior chat exchange is incomplete and cannot be replayed.")
            return StructuredAnswer.model_validate(assistant_message.structured_response)
        except IdempotencyConflictError:
            raise
        except SQLAlchemyError as exc:
            logger.error("Idempotent exchange lookup failed (exception_type=%s)", type(exc).__name__)
            raise ConversationPersistenceError from None

    def persist_exchange(
        self,
        conversation: Conversation,
        *,
        question: str,
        answer: StructuredAnswer,
        idempotency_key: UUID | None,
    ) -> StructuredAnswer:
        user_message = ConversationMessage(
            conversation_id=conversation.id,
            role="user",
            content=question,
            idempotency_key=str(idempotency_key) if idempotency_key else None,
        )
        assistant_message = ConversationMessage(
            conversation_id=conversation.id,
            role="assistant",
            content=answer.answer,
            structured_response=answer.model_dump(mode="json"),
            idempotency_key=str(idempotency_key) if idempotency_key else None,
        )
        conversation.updated_at = datetime.now(timezone.utc)
        self.session.add_all([user_message, assistant_message])
        try:
            self.session.commit()
            return answer
        except IntegrityError:
            self.session.rollback()
            if idempotency_key is not None:
                existing = self.existing_exchange(conversation.id, idempotency_key, question)
                if existing is not None:
                    return existing
                logger.warning("Conversation exchange conflicted with an existing request key")
                raise IdempotencyConflictError("This idempotency key has already been used.") from None
            logger.error("Conversation exchange violated a database constraint")
            raise ConversationPersistenceError from None
        except SQLAlchemyError as exc:
            self.session.rollback()
            logger.error("Conversation exchange could not be saved (exception_type=%s)", type(exc).__name__)
            raise ConversationPersistenceError from None

    def delete(self, conversation_id: int, user_id: int) -> None:
        conversation = self.get_owned(conversation_id, user_id)
        try:
            self.session.query(ConversationMessage).filter(
                ConversationMessage.conversation_id == conversation.id
            ).delete(synchronize_session=False)
            self.session.delete(conversation)
            self.session.commit()
        except SQLAlchemyError as exc:
            self.session.rollback()
            logger.error("Conversation deletion failed (exception_type=%s)", type(exc).__name__)
            raise ConversationPersistenceError from None

    def rename(self, conversation_id: int, user_id: int, title: str) -> ConversationSummary:
        conversation = self.get_owned(conversation_id, user_id)
        conversation.title = title.strip()[:160]
        try:
            self.session.commit()
            self.session.refresh(conversation)
            message_count, question_count = self.session.execute(
                select(
                    func.count(ConversationMessage.id),
                    func.coalesce(
                        func.sum(case((ConversationMessage.role == "user", 1), else_=0)),
                        0,
                    ),
                ).where(ConversationMessage.conversation_id == conversation.id)
            ).one()
            return _summary(conversation, int(message_count or 0), int(question_count or 0))
        except SQLAlchemyError as exc:
            self.session.rollback()
            logger.error("Conversation rename failed (exception_type=%s)", type(exc).__name__)
            raise ConversationPersistenceError from None


def _summary(conversation: Conversation, message_count: int, question_count: int) -> ConversationSummary:
    return ConversationSummary(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=message_count,
        question_count=question_count,
    )
