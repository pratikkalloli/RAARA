from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from app.config import settings
from app.database.db import Base, engine
from app.database import models  # noqa: F401 — register tables with SQLAlchemy metadata
from app.database.db import (
    migrate_conversation_schema,
    migrate_document_schema,
    migrate_user_schema,
)
from app.routes.documents import router as documents_router
from app.routes.chat import router as chat_router
from app.routes.auth import router as auth_router
from app.routes.admin_documents import router as admin_documents_router
from app.routes.conversations import router as conversations_router
from app.services.security import TokenConfigurationError, validate_jwt_secret

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Validate auth configuration before opening or migrating the configured database.
    try:
        validate_jwt_secret()
    except TokenConfigurationError as exc:
        logger.critical("RAARA startup configuration error: %s", exc)
        raise RuntimeError(f"RAARA startup configuration error: {exc}") from exc

    try:
        settings.validate_runtime_configuration()
    except ValueError as exc:
        logger.critical("RAARA AI configuration error: %s", exc)
        raise RuntimeError(f"RAARA AI configuration error: {exc}") from exc

    credential_configured = bool(settings.active_api_key)
    logger.info("Groq credential configured=%s", credential_configured)
    if not credential_configured:
        logger.error("GROQ_API_KEY is missing; Groq chat is unavailable until backend/.env is configured.")

    Base.metadata.create_all(bind=engine)
    migrate_document_schema()
    migrate_user_schema()
    migrate_conversation_schema()
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(auth_router)
app.include_router(admin_documents_router)
app.include_router(conversations_router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@app.get("/api/health/ai")
def ai_health() -> dict[str, str | int | bool]:
    """Expose selected provider configuration without making a paid call or exposing secrets."""
    return {
        "provider": settings.ai_provider.strip().casefold(),
        "chat_model": settings.active_chat_model,
        "embedding_provider": settings.active_embedding_provider,
        "embedding_model": settings.active_embedding_model,
        "embedding_dimensions": settings.active_embedding_dimensions,
        "credential_configured": bool(settings.active_api_key),
        "availability": "not_checked",
    }
