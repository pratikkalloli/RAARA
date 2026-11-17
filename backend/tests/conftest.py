from __future__ import annotations

import os
from io import BytesIO

# Force provider-safe values for the test process. These are inert placeholders;
# tests must inject/mock model clients and must never issue live provider calls.
os.environ["AI_PROVIDER"] = "groq"
os.environ["GROQ_API_KEY"] = "test-only-not-a-real-key"
os.environ["GROQ_CHAT_MODEL"] = "test-groq-model"
os.environ["EMBEDDING_PROVIDER"] = "local"
os.environ["EMBEDDING_MODEL"] = "sentence-transformers/all-MiniLM-L6-v2"
os.environ["EMBEDDING_DIMENSIONS"] = "384"

import pymupdf as fitz
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database.db import Base
from app.database import models  # noqa: F401


@pytest.fixture
def synthetic_pdf() -> bytes:
    """Synthetic test data only; this file is not an official regulation."""
    document = fitz.open()
    first = document.new_page()
    first.insert_text((60, 55), "SYNTHETIC TEST DOCUMENT", fontsize=18, fontname="hebo")
    first.insert_text((60, 73), "NOT AN OFFICIAL REGULATION", fontsize=9)
    first.insert_text((60, 120), "1. Attendance Requirements", fontsize=15, fontname="hebo")
    first.insert_textbox(
        fitz.Rect(60, 145, 540, 730),
        "This synthetic passage exists only to validate extraction, page metadata, and token chunking. " * 70,
        fontsize=10,
    )

    second = document.new_page()
    second.insert_text((60, 65), "2. Examination Guidance", fontsize=15, fontname="hebo")
    second.insert_textbox(
        fitz.Rect(60, 90, 540, 730),
        "Synthetic test content only. It does not state real university policy. " * 18,
        fontsize=10,
    )

    output = BytesIO()
    document.save(output)
    document.close()
    return output.getvalue()


@pytest.fixture
def empty_pdf() -> bytes:
    """A valid but text-empty synthetic PDF."""
    document = fitz.open()
    document.new_page()
    output = BytesIO()
    document.save(output)
    document.close()
    return output.getvalue()


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield session
    engine.dispose()
