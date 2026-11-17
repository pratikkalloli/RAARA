import tiktoken

from app.services.chunker import TokenChunker
from app.services.document_processor import ExtractedPage, ExtractedSection
from app.services.vector_store import REQUIRED_METADATA


def test_chunks_by_token_count_and_preserves_overlap():
    text = " ".join(f"term{index}" for index in range(1600))
    page = ExtractedPage(4, text, (ExtractedSection("Academic Policies", text),))
    chunker = TokenChunker(chunk_size=700, overlap=100)
    chunks = chunker.chunk_pages([page], {})

    encoder = tiktoken.get_encoding("cl100k_base")
    tokenized = [encoder.encode(chunk.text) for chunk in chunks]
    assert len(chunks) >= 3
    assert all(chunk.token_count <= 700 for chunk in chunks)
    assert all(len(tokens) <= 700 for tokens in tokenized)
    expected_overlap = encoder.decode(encoder.encode(text)[600:700]).strip()
    assert expected_overlap in chunks[0].text
    assert expected_overlap in chunks[1].text
    assert [chunk.page_number for chunk in chunks] == [4] * len(chunks)
    assert all(chunk.section == "Academic Policies" for chunk in chunks)


def test_preserves_every_required_metadata_field():
    text = "A short synthetic test passage."
    page = ExtractedPage(2, text, (ExtractedSection("Test heading", text),))
    metadata = {
        "document_id": "41",
        "document_name": "Synthetic Example.pdf",
        "document_type": "test_fixture",
        "academic_year": "2026-2027",
        "version": "3",
        "effective_date": "2026-08-01",
        "source_type": "synthetic_test",
        "verification_status": "unverified",
        "uploaded_by_user_id": "17",
    }

    [chunk] = TokenChunker().chunk_pages([page], metadata)
    assert set(REQUIRED_METADATA).issubset(chunk.metadata)
    assert chunk.metadata["page_number"] == 2
    assert chunk.metadata["section"] == "Test heading"
    assert chunk.metadata["verification_status"] == "unverified"
