from app.services.chunker import TextChunk
from app.services.vector_store import ChromaVectorStore, REQUIRED_METADATA


def test_chromadb_persists_indexed_chunks_and_retrieves_metadata(tmp_path):
    store = ChromaVectorStore(tmp_path / "vectors", collection_name="synthetic_test_docs")
    metadata = {
        "document_id": "8",
        "document_name": "Synthetic Test Document.pdf",
        "document_type": "test_fixture",
        "page_number": 1,
        "section": "Synthetic test heading",
        "academic_year": "2026-2027",
        "version": "1",
        "effective_date": "",
        "source_type": "synthetic_test",
        "verification_status": "unverified",
        "uploaded_by_user_id": "17",
    }
    chunk = TextChunk(
        text="Synthetic test data, not an official regulation.",
        page_number=1,
        section="Synthetic test heading",
        chunk_index=0,
        token_count=9,
        metadata=metadata,
    )

    store.add_chunks("8", [chunk], [[1.0, 0.0, 0.0]])
    reopened = ChromaVectorStore(tmp_path / "vectors", collection_name="synthetic_test_docs")
    [result] = reopened.query([1.0, 0.0, 0.0], top_k=1)

    assert result["text"] == chunk.text
    assert set(REQUIRED_METADATA).issubset(result["metadata"])
    assert result["metadata"]["document_id"] == "8"
    assert result["metadata"]["page_number"] == 1
    assert result["metadata"]["verification_status"] == "unverified"


def test_full_document_chunk_read_is_scoped_and_in_page_chunk_order(tmp_path):
    store = ChromaVectorStore(tmp_path / "full-document", collection_name="full_document_test")
    metadata = {
        "document_id": "18", "document_name": "Synthetic Multi Page.pdf", "document_type": "test_fixture",
        "page_number": 2, "section": "Synthetic section", "academic_year": "", "version": "1",
        "effective_date": "", "source_type": "synthetic_test", "verification_status": "unverified",
        "uploaded_by_user_id": "7",
    }
    chunks = [
        TextChunk("page two, chunk one", 2, "Synthetic section", 1, 4, metadata),
        TextChunk("page one, chunk two", 1, "Synthetic section", 2, 4, metadata | {"page_number": 1}),
        TextChunk("page one, chunk one", 1, "Synthetic section", 0, 4, metadata | {"page_number": 1}),
    ]
    other_document = [TextChunk("other fictional document", 1, "Elsewhere", 0, 3, metadata | {"document_id": "19"})]
    store.add_chunks("18", chunks, [[1.0, 0.0, 0.0]] * 3)
    store.add_chunks("19", other_document, [[0.0, 1.0, 0.0]])

    records = store.get_document_chunks("18")

    assert [record["text"] for record in records] == [
        "page one, chunk one", "page one, chunk two", "page two, chunk one"
    ]
    assert all(record["metadata"]["document_id"] == "18" for record in records)
