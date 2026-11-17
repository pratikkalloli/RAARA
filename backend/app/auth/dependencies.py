from __future__ import annotations

import logging
from collections.abc import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.db import SessionLocal
from app.database.models import User
from app.services.security import InvalidAccessTokenError, TokenConfigurationError, decode_access_token

_bearer = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)


def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized
    try:
        claims = decode_access_token(credentials.credentials)
    except (InvalidAccessTokenError, TokenConfigurationError):
        raise unauthorized from None
    try:
        user = session.get(User, int(claims["sub"]))
    except SQLAlchemyError as exc:
        logger.error("User lookup failed (exception_type=%s)", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Authentication is temporarily unavailable.") from None
    if user is None or not user.is_active:
        raise unauthorized
    return user


def require_authenticated_user(user: User = Depends(get_current_user)) -> User:
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access is required.")
    return user
