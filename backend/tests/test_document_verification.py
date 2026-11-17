from __future__ import annotations

import json
from types import SimpleNamespace
from uuid import uuid4

import pymupdf as fitz
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.auth.dependencies import get_db
from app.config import settings
from app.database.db import Base
from app.database.models import Document, User
from app.main import app
from app.routes import admin_documents
from app.services.citation_verifier import CitationVerifier
from app.services.chunker import TokenChunker
from app.services.generator import GroqAnswerGenerator
from app.services.ingestion import DocumentIngestionService
from app.services.retriever import Retriever
from app.services.security import create_access_token, hash_password
from app.services.vector_store import ChromaVectorStore, VectorStoreError


class FixedEmbedder:
    def embed_texts(self, texts):
        return [[1.0, 0.0, 0.0] for _ in texts]


class FakeResponses:
    def create(self, **_kwargs):
        return SimpleNamespace(
            output_text=json.dumps({
                "answer": "The retrieved synthetic policy states an attendance threshold.",
                "evidence_ids": ["P1"],
                "status": "SUPPORTED",
            })
        )


class FakeModels:
    def retrieve(self, model):
        return SimpleNamespace(id=model)


class ToggleFailureStore:
    def __init__(self, store):
        self.store = store
        self.fail = True

    def update_document_metadata(self, document_id, updates):
        if self.fail:
            records = self.store.collection.get(
                where={"document_id": str(document_id)},
                include=["metadatas"],
            )
            if records["ids"]:
                self.store.collection.update(
                    ids=[records["ids"][0]],
                    metadatas=[{**records["metadatas"][0], **updates}],
                )
            raise VectorStoreError("synthetic test failure")
        return self.store.update_document_metadata(document_id, updates)


@pytest.fixture
def review_context(tmp_path, monkeypatch, synthetic_pdf):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'review.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = factory()
    monkeypatch.setattr(settings, "jwt_secret_key", "phase-6b-test-jwt-signing-key-with-32-bytes")
    suffix = uuid4().hex[:8]
    student = User(
        username=f"student{suffix}",
        email=f"student{suffix}@example.edu",
        password_hash=hash_password("synthetic-test-password"),
        role="student",
    )
    other_student = User(
        username=f"other{suffix}",
        email=f"other{suffix}@example.edu",
        password_hash=hash_password("synthetic-test-password"),
        role="student",
    )
    admin = User(
        username=f"admin{suffix}",
        email=f"admin{suffix}@example.edu",
        password_hash=hash_password("synthetic-test-password"),
        role="admin",
    )
    session.add_all([student, other_student, admin])
    session.commit()

    vector_store = ChromaVectorStore(tmp_path / "chroma", collection_name=f"review_{suffix}")
    ingestion = DocumentIngestionService(
        session,
        embedder=FixedEmbedder(),
        vector_store=vector_store,
        chunker=TokenChunker(chunk_size=120, overlap=20),
        storage_dir=tmp_path / "uploads",
    )
    first = ingestion.ingest_pdf(
        synthetic_pdf,
        filename="synthetic-review-one.pdf",
        document_name="Synthetic Review One",
        source_type="synthetic_test",
        uploaded_by_user_id=student.id,
    )
    pdf = fitz.open(stream=synthetic_pdf, filetype="pdf")
    pdf.set_metadata({"title": "Synthetic Review Two"})
    second_pdf = pdf.tobytes()
    pdf.close()
    second = ingestion.ingest_pdf(
        second_pdf,
        filename="synthetic-review-two.pdf",
        document_name="Synthetic Review Two",
        source_type="synthetic_test",
        uploaded_by_user_id=other_student.id,
    )

    def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    monkeypatch.setattr(admin_documents, "ChromaVectorStore", lambda: vector_store)
    client = TestClient(app)
    tokens = {
        "student": create_access_token(student.id),
        "other_student": create_access_token(other_student.id),
        "admin": create_access_token(admin.id),
    }
    yield client, session, vector_store, first, second, student, other_student, admin, tokens
    app.dependency_overrides.pop(get_db, None)
    session.close()
    engine.dispose()


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_document_list_requires_auth_and_students_only_see_owned_documents(review_context):
    client, _, _, first, second, _, _, _, tokens = review_context
    assert client.get("/api/documents").status_code == 401

    student_response = client.get("/api/documents", headers=headers(tokens["student"]))
    assert student_response.status_code == 200
    assert [item["document_id"] for item in student_response.json()] == [first.id]
    assert "storage_path" not in student_response.json()[0]

    admin_response = client.get("/api/documents", headers=headers(tokens["admin"]))
    assert admin_response.status_code == 200
    assert {item["document_id"] for item in admin_response.json()} == {first.id, second.id}


def test_document_list_filters_by_verification_status(review_context):
    client, session, _, first, _, _, _, _, tokens = review_context
    first.verification_status = "verified"
    session.commit()
    response = client.get(
        "/api/documents?verification_status=verified",
        headers=headers(tokens["admin"]),
    )
    assert response.status_code == 200
    assert [item["document_id"] for item in response.json()] == [first.id]


def test_student_retrieval_filters_chunks_by_server_owned_uploader_id(review_context):
    _, session, store, first, second, student, other_student, _, _ = review_context
    lookup = lambda ids: {
        str(row.id): (row.verification_status, row.vector_sync_status)
        for row in session.scalars(select(Document).where(Document.id.in_([int(value) for value in ids])))
    }
    retriever = Retriever(FixedEmbedder(), store, document_state_lookup=lookup)
    first_result = retriever.retrieve("Question", metadata_filters={"uploaded_by_user_id": student.id})
    second_result = retriever.retrieve("Question", metadata_filters={"uploaded_by_user_id": other_student.id})
    assert {int(item.metadata["document_id"]) for item in first_result.passages} == {first.id}
    assert {int(item.metadata["document_id"]) for item in second_result.passages} == {second.id}


def test_pending_review_requires_admin_and_includes_uploader(review_context):
    client, _, _, first, second, _, _, _, tokens = review_context
    assert client.get("/api/admin/documents/pending").status_code == 401
    assert client.get("/api/admin/documents/pending", headers=headers(tokens["student"])).status_code == 403
    response = client.get("/api/admin/documents/pending", headers=headers(tokens["admin"]))
    assert response.status_code == 200
    assert {item["document_id"] for item in response.json()} == {first.id, second.id}
    assert response.json()[0]["uploaded_by_username"] is not None
    assert "storage_path" not in response.text
    denied_decision = client.post(
        f"/api/admin/documents/{first.id}/verification",
        headers=headers(tokens["student"]),
        json={"decision": "verified"},
    )
    assert denied_decision.status_code == 403


def test_admin_approval_updates_sql_audit_and_all_chroma_chunks(review_context):
    client, session, store, document, _, _, _, admin, tokens = review_context
    response = client.post(
        f"/api/admin/documents/{document.id}/verification",
        headers=headers(tokens["admin"]),
        json={"decision": "verified", "review_note": "Reviewed synthetic test fixture."},
    )
    assert response.status_code == 200
    assert response.json()["verification_status"] == "verified"
    assert response.json()["vector_sync_status"] == "synced"
    session.refresh(document)
    assert document.reviewed_by_user_id == admin.id
    assert document.reviewed_at is not None
    assert document.review_note == "Reviewed synthetic test fixture."

    chunks = store.collection.get(where={"document_id": str(document.id)}, include=["metadatas"])
    assert len(chunks["ids"]) == document.chunk_count
    assert {metadata["verification_status"] for metadata in chunks["metadatas"]} == {"verified"}

    lookup = lambda ids: {
        str(row.id): (row.verification_status, row.vector_sync_status)
        for row in session.scalars(select(Document).where(Document.id.in_([int(value) for value in ids])))
    }
    retrieval = Retriever(FixedEmbedder(), store, document_state_lookup=lookup).retrieve(
        "What is the attendance requirement?",
        metadata_filters={"document_id": str(document.id)},
    )
    assert retrieval.passages
    generated = GroqAnswerGenerator(model="test-groq-model", client=SimpleNamespace(models=FakeModels(), responses=FakeResponses())).generate(
        retrieval
    )
    validated = CitationVerifier().verify(generated, retrieval).answer
    assert validated.evidence[0].verification_status == "verified"
    assert validated.sources[0].verification_status == "verified"
    assert "has not been independently established" in validated.answer


def test_admin_rejection_updates_chroma_and_rejected_document_is_excluded(review_context):
    client, session, store, _, document, _, _, admin, tokens = review_context
    response = client.post(
        f"/api/admin/documents/{document.id}/verification",
        headers=headers(tokens["admin"]),
        json={"decision": "rejected"},
    )
    assert response.status_code == 200
    assert response.json()["verification_status"] == "rejected"
    assert response.json()["review_note"] is None
    session.refresh(document)
    assert document.reviewed_by_user_id == admin.id
    chunks = store.collection.get(where={"document_id": str(document.id)}, include=["metadatas"])
    assert {metadata["verification_status"] for metadata in chunks["metadatas"]} == {"rejected"}

    lookup = lambda ids: {
        str(row.id): (row.verification_status, row.vector_sync_status)
        for row in session.scalars(select(Document).where(Document.id.in_([int(value) for value in ids])))
    }
    retrieval = Retriever(FixedEmbedder(), store, document_state_lookup=lookup).retrieve(
        "What is the attendance requirement?",
        metadata_filters={"document_id": str(document.id)},
    )
    assert retrieval.passages == ()


def test_invalid_document_id_decision_and_repeated_review(review_context):
    client, _, _, document, _, _, _, _, tokens = review_context
    admin_headers = headers(tokens["admin"])
    assert client.post("/api/admin/documents/99999/verification", headers=admin_headers, json={"decision": "verified"}).status_code == 404
    assert client.post(
        f"/api/admin/documents/{document.id}/verification",
        headers=admin_headers,
        json={"decision": "pending"},
    ).status_code == 422
    assert client.post(
        f"/api/admin/documents/{document.id}/verification",
        headers=admin_headers,
        json={"decision": "verified"},
    ).status_code == 200
    repeated = client.post(
        f"/api/admin/documents/{document.id}/verification",
        headers=admin_headers,
        json={"decision": "rejected"},
    )
    assert repeated.status_code == 409


def test_partial_chroma_failure_is_visible_and_retry_reconciles(review_context, monkeypatch):
    client, session, store, document, _, _, _, _, tokens = review_context
    flaky = ToggleFailureStore(store)
    monkeypatch.setattr(admin_documents, "ChromaVectorStore", lambda: flaky)
    response = client.post(
        f"/api/admin/documents/{document.id}/verification",
        headers=headers(tokens["admin"]),
        json={"decision": "verified"},
    )
    assert response.status_code == 503
    assert response.json()["detail"]["vector_sync_status"] == "pending"
    session.refresh(document)
    assert document.verification_status == "verified"
    assert document.vector_sync_status == "pending"
    partial = store.collection.get(where={"document_id": str(document.id)}, include=["metadatas"])
    vector_statuses = {metadata["verification_status"] for metadata in partial["metadatas"]}
    assert "verified" in vector_statuses and "unverified" in vector_statuses

    lookup = lambda ids: {
        str(row.id): (row.verification_status, row.vector_sync_status)
        for row in session.scalars(select(Document).where(Document.id.in_([int(value) for value in ids])))
    }
    blocked = Retriever(FixedEmbedder(), store, document_state_lookup=lookup).retrieve(
        "Question", metadata_filters={"document_id": str(document.id)}
    )
    assert blocked.passages == ()

    flaky.fail = False
    retried = client.post(
        f"/api/admin/documents/{document.id}/verification/retry-sync",
        headers=headers(tokens["admin"]),
    )
    assert retried.status_code == 200
    assert retried.json()["vector_sync_status"] == "synced"
    session.refresh(document)
    assert document.vector_sync_status == "synced"


def test_unverified_documents_remain_retrievable_with_warning_metadata(review_context):
    client, session, store, document, _, _, _, _, tokens = review_context
    lookup = lambda ids: {
        str(row.id): (row.verification_status, row.vector_sync_status)
        for row in session.scalars(select(Document).where(Document.id.in_([int(value) for value in ids])))
    }
    retrieval = Retriever(FixedEmbedder(), store, document_state_lookup=lookup).retrieve(
        "What is the attendance requirement?",
        metadata_filters={"document_id": str(document.id)},
    )
    assert retrieval.passages
    assert all(item.metadata["verification_status"] == "unverified" for item in retrieval.passages)


def test_legacy_document_migration_adds_nullable_owner_and_review_fields_without_data_loss(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy-documents.db'}")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE documents (id INTEGER PRIMARY KEY, filename VARCHAR(255) NOT NULL, sha256 VARCHAR(64) NOT NULL, "
            "verification_status VARCHAR(32) NOT NULL DEFAULT 'unverified')"
        )
        connection.exec_driver_sql("INSERT INTO documents (id, filename, sha256) VALUES (1, 'legacy.pdf', 'abc')")
    # Match application startup order on a legacy SQLite database.
    Base.metadata.create_all(engine)
    from app.database.db import migrate_document_schema

    migrate_document_schema(engine)
    migrate_document_schema(engine)
    with engine.connect() as connection:
        row = connection.exec_driver_sql(
            "SELECT filename, uploaded_by_user_id, vector_sync_status, verification_status FROM documents WHERE id=1"
        ).one()
        assert row == ("legacy.pdf", None, "synced", "unverified")
    engine.dispose()
