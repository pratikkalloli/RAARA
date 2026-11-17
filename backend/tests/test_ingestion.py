import pymupdf as fitz
import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.database.models import Document, User
from app.main import app
from app.routes.documents import get_ingestion_service
from app.services.chunker import TokenChunker
from app.services.document_processor import EmptyPDFError, InvalidPDFError
from app.services.ingestion import DocumentIngestionService, DuplicateDocumentError
from app.services.vector_store import ChromaVectorStore, REQUIRED_METADATA


class FakeEmbedder:
    def __init__(self):
        self.inputs = []

    def embed_texts(self, texts):
        self.inputs.append(list(texts))
        return [[1.0, 0.0, 0.0] for _ in texts]


def make_service(session, tmp_path, *, collection_name="ingestion_test"):
    store = ChromaVectorStore(tmp_path / "chroma", collection_name=collection_name)
    service = DocumentIngestionService(
        session,
        embedder=FakeEmbedder(),
        vector_store=store,
        chunker=TokenChunker(chunk_size=120, overlap=20),
        storage_dir=tmp_path / "uploads",
        max_file_size_bytes=5 * 1024 * 1024,
    )
    return service, store


def test_ingestion_persists_document_chunks_and_required_metadata(db_session, tmp_path, synthetic_pdf):
    service, store = make_service(db_session, tmp_path)

    record = service.ingest_pdf(
        synthetic_pdf,
        filename="synthetic-test-document.pdf",
        document_type="test_fixture",
        academic_year="2026-2027",
        effective_date="2026-08-01",
        source_type="synthetic_test",
    )

    assert record.id is not None
    assert record.document_name == "synthetic-test-document.pdf"
    assert record.version == "1"
    assert record.verification_status == "unverified"
    assert record.processing_status == "indexed"
    assert record.page_count == 2
    assert record.chunk_count > 0
    assert record.sha256
    assert record.storage_path
    assert (tmp_path / "uploads" / f"{record.id}-{record.sha256[:12]}.pdf").is_file()

    results = store.query([1.0, 0.0, 0.0], top_k=record.chunk_count)
    assert len(results) == record.chunk_count
    for result in results:
        metadata = result["metadata"]
        assert set(REQUIRED_METADATA).issubset(metadata)
        assert metadata["document_id"] == str(record.id)
        assert metadata["document_name"] == "synthetic-test-document.pdf"
        assert metadata["document_type"] == "test_fixture"
        assert metadata["academic_year"] == "2026-2027"
        assert metadata["version"] == "1"
        assert metadata["effective_date"] == "2026-08-01"
        assert metadata["source_type"] == "synthetic_test"
        assert metadata["verification_status"] == "unverified"
        assert metadata["page_number"] in (1, 2)


def test_duplicate_pdf_hash_is_rejected(db_session, tmp_path, synthetic_pdf):
    service, _ = make_service(db_session, tmp_path)
    service.ingest_pdf(synthetic_pdf, filename="synthetic-test-document.pdf")

    with pytest.raises(DuplicateDocumentError):
        service.ingest_pdf(synthetic_pdf, filename="copy-of-synthetic-test-document.pdf")

    assert db_session.query(Document).count() == 1


def test_new_pdf_creates_next_version_for_same_document(db_session, tmp_path, synthetic_pdf):
    service, _ = make_service(db_session, tmp_path, collection_name="version_test")
    first = service.ingest_pdf(
        synthetic_pdf,
        filename="attendance-handbook.pdf",
        document_name="Attendance Handbook",
        document_type="handbook",
    )

    pdf = fitz.open(stream=synthetic_pdf, filetype="pdf")
    pdf.set_metadata({"title": "Synthetic Test Document v2"})
    revised_bytes = pdf.tobytes()
    pdf.close()
    second = service.ingest_pdf(
        revised_bytes,
        filename="attendance-handbook-revised.pdf",
        document_name="Attendance Handbook",
        document_type="handbook",
    )

    assert first.version == "1"
    assert second.version == "2"
    assert first.sha256 != second.sha256


def test_invalid_and_empty_pdfs_do_not_create_records(db_session, tmp_path, empty_pdf):
    service, _ = make_service(db_session, tmp_path, collection_name="invalid_pdf_test")

    with pytest.raises(InvalidPDFError):
        service.ingest_pdf(b"not a PDF", filename="invalid.pdf")
    with pytest.raises(EmptyPDFError):
        service.ingest_pdf(empty_pdf, filename="empty.pdf")

    assert db_session.query(Document).count() == 0


def test_upload_endpoint_uses_injected_service_without_openai_calls(db_session, tmp_path, synthetic_pdf):
    service, _ = make_service(db_session, tmp_path, collection_name="upload_route_test")
    user = User(
        id=71,
        username="upload.student",
        email="upload.student@example.edu",
        password_hash="unused-test-hash",
        role="student",
    )
    db_session.add(user)
    db_session.commit()
    app.dependency_overrides[get_ingestion_service] = lambda: service
    try:
        anonymous = TestClient(app).post(
            "/api/documents/upload",
            files={"file": ("synthetic-test-document.pdf", synthetic_pdf, "application/pdf")},
        )
        app.dependency_overrides[get_current_user] = lambda: user
        response = TestClient(app).post(
            "/api/documents/upload",
            files={"file": ("synthetic-test-document.pdf", synthetic_pdf, "application/pdf")},
            data={
                "document_type": "test_fixture",
                "academic_year": "2026-2027",
                "source_type": "synthetic_test",
            },
        )
    finally:
        app.dependency_overrides.pop(get_ingestion_service, None)
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 201
    assert response.json()["verification_status"] == "unverified"
    assert response.json()["document_type"] == "test_fixture"
    assert response.json()["chunk_count"] > 0
    assert db_session.query(Document).one().uploaded_by_user_id == user.id
    assert anonymous.status_code == 401
