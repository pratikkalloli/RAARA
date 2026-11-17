import hashlib
from pathlib import Path

import chromadb
import pytest

from app.database.models import Document
from app.services.chunker import TextChunk
from app.services.reindex import ReindexError, read_managed_source, reindex_document
from app.services.vector_store import ChromaVectorStore, VectorStoreError


def _metadata(document_id="12", *, page=1):
    return {
        "document_id": str(document_id), "document_name": "Synthetic Test Guide.pdf",
        "document_type": "synthetic_test", "page_number": page, "section": "Synthetic",
        "academic_year": "", "version": "1", "effective_date": "",
        "source_type": "synthetic_test", "verification_status": "unverified",
        "uploaded_by_user_id": "5",
    }


def _chunk(index, *, document_id="12", page=1):
    return TextChunk(
        text=f"Synthetic test chunk {index}; not official policy.",
        page_number=page, section="Synthetic", chunk_index=index, token_count=8,
        metadata=_metadata(document_id, page=page),
    )


class FixedChunker:
    def __init__(self, count=2):
        self.count = count

    def chunk_pages(self, pages, metadata):
        return [
            TextChunk(
                text=f"Synthetic page grounded text {index}.", page_number=index + 1,
                section="Synthetic", chunk_index=index, token_count=5,
                metadata={**metadata, "page_number": index + 1, "section": "Synthetic"},
            )
            for index in range(self.count)
        ]


class FixedEmbedder:
    def embed_texts(self, texts):
        return [[1.0] + [0.0] * 383 for _ in texts]


def test_new_local_collection_is_separate_and_preserves_existing_768d_collection(tmp_path):
    client = chromadb.PersistentClient(path=str(tmp_path / "chroma"))
    old = client.create_collection(
        name="raara_documents_gemini_legacy_768d",
        metadata={"hnsw:space": "cosine", "embedding_provider": "gemini", "embedding_dimensions": 768},
    )
    old.add(ids=["preserve-me"], documents=["old vector"], embeddings=[[1.0] + [0.0] * 767])

    new = ChromaVectorStore(tmp_path / "chroma")

    assert new.collection_name == "raara_documents_groq_local_384"
    assert new.count() == 0
    assert client.get_collection("raara_documents_gemini_legacy_768d").count() == 1


def test_active_local_collection_rejects_existing_768d_metadata_without_deleting_it(tmp_path):
    client = chromadb.PersistentClient(path=str(tmp_path / "chroma"))
    old_name = "raara_documents_groq_local_384"
    old = client.create_collection(
        name=old_name,
        metadata={"hnsw:space": "cosine", "embedding_provider": "gemini", "embedding_dimensions": 768},
    )
    old.add(ids=["preserve-me"], documents=["old vector"], embeddings=[[1.0] + [0.0] * 767])

    with pytest.raises(VectorStoreError, match="does not match local 384-dimensional"):
        ChromaVectorStore(tmp_path / "chroma")

    assert client.get_collection(old_name).count() == 1


def test_active_local_collection_rejects_non_384_vectors(tmp_path):
    store = ChromaVectorStore(tmp_path / "chroma")
    with pytest.raises(ValueError, match="requires 384-dimensional"):
        store.add_chunks("12", [_chunk(0)], [[1.0] + [0.0] * 767])


def test_reindex_reads_only_checksummed_pdfs_under_upload_root(tmp_path):
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    content = b"synthetic-only-pdf-bytes"
    stored = uploads / "12-guide.pdf"
    stored.write_bytes(content)
    document = Document(id=12, storage_path=str(stored), sha256=hashlib.sha256(content).hexdigest())

    assert read_managed_source(document, uploads) == content

    document.sha256 = "0" * 64
    with pytest.raises(ReindexError, match="source_checksum_mismatch"):
        read_managed_source(document, uploads)
    document.storage_path = str(tmp_path / "outside.pdf")
    with pytest.raises(ReindexError, match="outside_upload_directory"):
        read_managed_source(document, uploads)


def test_reindex_uses_only_new_collection_and_preserves_document_provenance(
    tmp_path, synthetic_pdf
):
    upload_root = tmp_path / "uploads"
    upload_root.mkdir()
    path = upload_root / "12-synthetic.pdf"
    path.write_bytes(synthetic_pdf)
    document = Document(
        id=12, filename=path.name, document_name="Synthetic Test Guide.pdf",
        sha256=hashlib.sha256(synthetic_pdf).hexdigest(), document_type="synthetic_test",
        academic_year="", version="1", effective_date="", source_type="synthetic_test",
        verification_status="unverified", vector_sync_status="pending",
        uploaded_by_user_id=5, processing_status="pending", storage_path=str(path),
    )
    client = chromadb.PersistentClient(path=str(tmp_path / "chroma"))
    old = client.create_collection(
        name="raara_documents_gemini_legacy_768d",
        metadata={"hnsw:space": "cosine", "embedding_provider": "gemini", "embedding_dimensions": 768},
    )
    old.add(ids=["old"], documents=["unchanged"], embeddings=[[1.0] + [0.0] * 767])
    store = ChromaVectorStore(tmp_path / "chroma")

    count = reindex_document(
        document,
        synthetic_pdf,
        embedder=FixedEmbedder(),
        vector_store=store,
        chunker=FixedChunker(2),
    )

    records = store.get_document_chunks("12")
    assert count == 2
    assert len(records) == 2
    assert all(record["metadata"]["verification_status"] == "unverified" for record in records)
    assert all(record["metadata"]["source_type"] == "synthetic_test" for record in records)
    assert document.chunk_count == 2
    assert document.processing_status == "indexed"
    assert document.vector_sync_status == "synced"
    assert client.get_collection("raara_documents_gemini_legacy_768d").count() == 1


def test_reindex_replaces_old_local_chunks_only_after_new_chunk_ids_are_confirmed(tmp_path, synthetic_pdf):
    path_root = tmp_path / "uploads"
    path_root.mkdir()
    path = path_root / "12-guide.pdf"
    path.write_bytes(synthetic_pdf)
    document = Document(
        id=12, filename=path.name, document_name="Synthetic Test Guide.pdf",
        sha256=hashlib.sha256(synthetic_pdf).hexdigest(), document_type="synthetic_test",
        version="1", source_type="synthetic_test", verification_status="unverified",
        storage_path=str(path),
    )
    store = ChromaVectorStore(tmp_path / "chroma")

    reindex_document(document, synthetic_pdf, embedder=FixedEmbedder(), vector_store=store, chunker=FixedChunker(3))
    reindex_document(document, synthetic_pdf, embedder=FixedEmbedder(), vector_store=store, chunker=FixedChunker(1))

    assert len(store.get_document_chunks("12")) == 1
