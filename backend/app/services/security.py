"""Password hashing and signed access-token helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from pwdlib import PasswordHash

from app.config import settings

_password_hash = PasswordHash.recommended()
_JWT_ALGORITHM = "HS256"


class InvalidAccessTokenError(ValueError):
    """Raised when a bearer token is malformed, expired, or invalid."""


class TokenConfigurationError(RuntimeError):
    """Raised when secure token signing is not configured."""


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hash.verify(password, password_hash)
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str | int, *, expires_delta: timedelta | None = None) -> str:
    secret = _signing_secret()
    now = datetime.now(timezone.utc)
    lifetime = expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    if lifetime.total_seconds() <= 0:
        raise TokenConfigurationError("Access-token expiration must be positive.")
    payload = {
        "sub": str(subject),
        "iat": now,
        "exp": now + lifetime,
        "type": "access",
    }
    return jwt.encode(payload, secret, algorithm=_JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        claims = jwt.decode(
            token,
            _signing_secret(),
            algorithms=[_JWT_ALGORITHM],
            options={"require": ["sub", "exp", "iat", "type"]},
        )
        if claims.get("type") != "access" or not str(claims.get("sub", "")).isdigit():
            raise InvalidAccessTokenError("Invalid access token.")
        return claims
    except InvalidAccessTokenError:
        raise
    except (jwt.InvalidTokenError, TokenConfigurationError, TypeError, ValueError) as exc:
        raise InvalidAccessTokenError("Invalid access token.") from exc


def _signing_secret() -> str:
    secret = settings.jwt_secret_key
    validate_jwt_secret(secret)
    assert secret is not None
    return secret


def validate_jwt_secret(secret: str | None = None) -> None:
    """Fail early with a safe, actionable message for missing or placeholder secrets."""
    candidate = settings.jwt_secret_key if secret is None else secret
    if not candidate:
        raise TokenConfigurationError(
            "JWT_SECRET_KEY is missing. Copy backend/.env.example to backend/.env and set a randomly generated secret of at least 32 bytes."
        )
    if candidate.casefold().startswith(("change-me", "change_me", "replace-")):
        raise TokenConfigurationError(
            "JWT_SECRET_KEY still contains the example placeholder. Set a private randomly generated value in backend/.env."
        )
    if len(candidate.encode("utf-8")) < 32:
        raise TokenConfigurationError(
            "JWT_SECRET_KEY is too short. Configure at least 32 bytes of random secret material in backend/.env."
        )
