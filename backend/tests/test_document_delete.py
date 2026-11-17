from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.auth.dependencies import get_db
from app.config import settings
from app.database.db import Base
from app.database.models import Document, User
from app.main import app
from app.routes import documents as document_routes
from app.services.security import create_access_token
from app.services.vector_store import VectorStoreError


class FakeVectorStore:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.deleted: list[str] = []

    def delete_document(self, document_id: int) -> None:
        if self.fail:
            raise VectorStoreError("mocked safe delete failure")
        self.deleted.append(str(document_id))


@pytest.fixture
def document_delete_context(tmp_path, monkeypatch) -> Iterator[tuple]:
    upload_root = tmp_path / "uploads"
    upload_root.mkdir()
    engine = create_engine(f"sqlite:///{tmp_path / 'documents.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session: Session = factory()
    suffix = uuid4().hex[:8]
    owner = User(username=f"owner{suffix}", email=f"owner{suffix}@example.edu", password_hash="test", role="student")
    other = User(username=f"other{suffix}", email=f"other{suffix}@example.edu", password_hash="test", role="student")
    admin = User(username=f"admin{suffix}", email=f"admin{suffix}@example.edu", password_hash="test", role="admin")
    session.add_all([owner, other, admin])
    session.commit()
    monkeypatch.setattr(settings, "jwt_secret_key", "document-delete-test-jwt-secret-long-enough")
    monkeypatch.setattr(settings, "upload_dir", str(upload_root))
    vectors = FakeVectorStore()
    monkeypatch.setattr(document_routes, "ChromaVectorStore", lambda: vectors)

    def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    tokens = {role: create_access_token(user.id) for role, user in {"owner": owner, "other": other, "admin": admin}.items()}
    yield client, session, owner, other, admin, tokens, vectors, upload_root
    app.dependency_overrides.pop(get_db, None)
    session.close()
    engine.dispose()


def _create_document(session: Session, owner_id: int, storage_path: str) -> Document:
    document = Document(
        filename="synthetic.pdf",
        document_name="Synthetic test PDF",
        sha256=uuid4().hex + uuid4().hex,
        document_type="test_fixture",
        version="1",
        source_type="synthetic_test",
        verification_status="unverified",
        vector_sync_status="synced",
        uploaded_by_user_id=owner_id,
        processing_status="indexed",
        storage_path=storage_path,
        page_count=1,
        chunk_count=1,
    )
    session.add(document)
    session.commit()
    return document


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_owner_can_delete_owned_document_and_managed_file(document_delete_context):
    client, session, owner, _other, _admin, tokens, vectors, upload_root = document_delete_context
    path = upload_root / "owned.pdf"
    path.write_bytes(b"synthetic fixture only")
    document = _create_document(session, owner.id, str(path))

    response = client.delete(f"/api/documents/{document.id}", headers=_auth(tokens["owner"]))

    assert response.status_code == 204
    assert session.get(Document, document.id) is None
    assert not path.exists()
    assert vectors.deleted == [str(document.id)]


def test_student_cannot_delete_another_users_document(document_delete_context):
    client, session, owner, _other, _admin, tokens, vectors, upload_root = document_delete_context
    path = upload_root / "private.pdf"
    path.write_bytes(b"synthetic fixture only")
    document = _create_document(session, owner.id, str(path))

    response = client.delete(f"/api/documents/{document.id}", headers=_auth(tokens["other"]))

    assert response.status_code == 404
    assert session.get(Document, document.id) is not None
    assert path.exists()
    assert vectors.deleted == []


def test_admin_can_delete_document_owned_by_another_user(document_delete_context):
    client, session, owner, _other, _admin, tokens, vectors, upload_root = document_delete_context
    path = upload_root / "admin-delete.pdf"
    path.write_bytes(b"synthetic fixture only")
    document = _create_document(session, owner.id, str(path))

    response = client.delete(f"/api/documents/{document.id}", headers=_auth(tokens["admin"]))

    assert response.status_code == 204
    assert session.get(Document, document.id) is None
    assert not path.exists()
    assert vectors.deleted == [str(document.id)]


def test_document_delete_refuses_storage_path_outside_managed_uploads(document_delete_context, tmp_path):
    client, session, owner, _other, _admin, tokens, vectors, _upload_root = document_delete_context
    outside = tmp_path / "outside.pdf"
    outside.write_bytes(b"must remain")
    document = _create_document(session, owner.id, str(outside))

    response = client.delete(f"/api/documents/{document.id}", headers=_auth(tokens["owner"]))

    assert response.status_code == 409
    assert outside.read_bytes() == b"must remain"
    assert session.get(Document, document.id) is not None
    assert vectors.deleted == []


def test_document_delete_keeps_record_and_file_when_vector_delete_fails(document_delete_context, monkeypatch):
    client, session, owner, _other, _admin, tokens, vectors, upload_root = document_delete_context
    vectors.fail = True
    path = upload_root / "vector-error.pdf"
    path.write_bytes(b"synthetic fixture only")
    document = _create_document(session, owner.id, str(path))

    response = client.delete(f"/api/documents/{document.id}", headers=_auth(tokens["owner"]))

    assert response.status_code == 503
    assert session.get(Document, document.id) is not None
    assert path.exists()
