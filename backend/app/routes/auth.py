from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_db
from app.config import settings
from app.database.models import User
from app.schemas.auth import LoginRequest, LoginResponse, RegisterRequest, UserProfile
from app.services.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["authentication"])
logger = logging.getLogger(__name__)


@router.post("/register", response_model=UserProfile, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, session: Session = Depends(get_db)) -> User:
    try:
        duplicate = session.scalar(
            select(User.id).where(
                or_(func.lower(User.username) == request.username, func.lower(User.email) == request.email)
            )
        )
        if duplicate is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username or email is already registered.",
            )
        user = User(
            username=request.username,
            email=request.email,
            password_hash=hash_password(request.password),
            role="student",
            is_active=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
    except HTTPException:
        session.rollback()
        raise
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email is already registered.",
        ) from None
    except SQLAlchemyError:
        session.rollback()
        raise HTTPException(status_code=500, detail="The account could not be created.") from None
    return user


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, session: Session = Depends(get_db)) -> LoginResponse:
    try:
        user = session.scalar(
            select(User).where(
                or_(func.lower(User.username) == request.identifier, func.lower(User.email) == request.identifier)
            )
        )
    except SQLAlchemyError as exc:
        logger.error("Login database operation failed (exception_type=%s)", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Authentication is temporarily unavailable.") from None
    if user is None or not user.is_active or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        token = create_access_token(user.id)
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Authentication is not configured.") from None
    return LoginResponse(
        access_token=token,
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserProfile.model_validate(user),
    )


@router.get("/me", response_model=UserProfile)
def me(user: User = Depends(get_current_user)) -> User:
    return user
