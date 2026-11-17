from __future__ import annotations

import logging

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_db
from app.database.models import User
from app.schemas.conversations import (
    ConversationCreateRequest,
    ConversationDetail,
    ConversationRenameRequest,
    ConversationSummary,
)
from app.services.conversations import (
    ConversationNotFoundError,
    ConversationPersistenceError,
    ConversationService,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.post("", response_model=ConversationSummary, status_code=status.HTTP_201_CREATED)
def create_conversation(
    request: ConversationCreateRequest = Body(default=ConversationCreateRequest()),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> ConversationSummary:
    try:
        return ConversationService(session).create(user_id=user.id, title=request.title)
    except ConversationPersistenceError:
        raise HTTPException(status_code=503, detail="The conversation could not be created.") from None


@router.get("", response_model=list[ConversationSummary])
def list_conversations(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[ConversationSummary]:
    try:
        return ConversationService(session).list_for_user(user.id)
    except ConversationPersistenceError:
        raise HTTPException(status_code=503, detail="Conversation history is temporarily unavailable.") from None


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> ConversationDetail:
    try:
        return ConversationService(session).detail(conversation_id, user.id)
    except ConversationNotFoundError:
        raise HTTPException(status_code=404, detail="Conversation not found.") from None
    except ConversationPersistenceError:
        raise HTTPException(status_code=503, detail="Conversation history is temporarily unavailable.") from None


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> None:
    try:
        ConversationService(session).delete(conversation_id, user.id)
    except ConversationNotFoundError:
        raise HTTPException(status_code=404, detail="Conversation not found.") from None
    except ConversationPersistenceError:
        raise HTTPException(status_code=503, detail="The conversation could not be deleted.") from None


@router.patch("/{conversation_id}", response_model=ConversationSummary)
def rename_conversation(
    conversation_id: int,
    request: ConversationRenameRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> ConversationSummary:
    try:
        return ConversationService(session).rename(conversation_id, user.id, request.title)
    except ConversationNotFoundError:
        raise HTTPException(status_code=404, detail="Conversation not found.") from None
    except ConversationPersistenceError:
        raise HTTPException(status_code=503, detail="The conversation could not be renamed.") from None
