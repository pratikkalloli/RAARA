import pytest

from app.services.retriever import InvalidQuestionError, Retriever, normalize_retrieval_query
from app.services.vector_store import ChromaVectorStore


class FixedEmbedder:
    def __init__(self, vector=None):
        self.vector = vector or [1.0, 0.0]
        self.questions = []

    def embed_texts(self, texts):
        self.questions.extend(texts)
        return [self.vector]


class FixedVectorStore:
    def __init__(self, results):
        self.results = results
        self.query_args = None

    def query(self, query_embedding, *, top_k=5, where=None):
        self.query_args = (query_embedding, top_k, where)
        return self.results[:top_k]


def candidate(*, distance=0.1, metadata=None, text="Synthetic test evidence"):
    return {
        "id": "chunk-1",
        "text": text,
        "metadata": metadata or {
            "document_id": "3",
            "document_name": "Synthetic Test Handbook.pdf",
            "document_type": "test_fixture",
            "page_number": 2,
            "section": "Test section",
            "academic_year": "2026-2027",
            "version": "1",
            "effective_date": "",
            "source_type": "synthetic_test",
            "verification_status": "unverified",
            "uploaded_by_user_id": "17",
        },
        "distance": distance,
    }


def test_successful_retrieval_uses_embedding_top_k_and_preserves_metadata():
    embedder = FixedEmbedder([0.25, 0.75])
    store = FixedVectorStore([candidate(distance=0.15)])
    retriever = Retriever(embedder, store, top_k=5, relevance_threshold=0.35)

    result = retriever.retrieve("  What does the test handbook say?  ", metadata_filters={"version": "1"})

    assert embedder.questions == ["What does the test handbook say?"]
    assert store.query_args[0] == [0.25, 0.75]
    assert store.query_args[1] == 20
    assert store.query_args[2] == {"$and": [{"version": "1"}, {"verification_status": {"$ne": "rejected"}}]}
    assert len(result.passages) == 1
    assert result.passages[0].relevance_score == pytest.approx(0.85)
    assert result.passages[0].metadata["document_name"] == "Synthetic Test Handbook.pdf"
    assert result.passages[0].metadata["page_number"] == 2
    assert result.passages[0].metadata["section"] == "Test section"
    assert result.passages[0].metadata["verification_status"] == "unverified"


def test_empty_chroma_collection_returns_no_passages(tmp_path):
    store = ChromaVectorStore(tmp_path / "empty", collection_name="empty_test")
    embedder = FixedEmbedder()
    result = Retriever(embedder, store).retrieve("A question with no indexed documents")

    assert result.passages == ()
    assert embedder.questions == []
    assert result.retrieval_state == "empty_index"


def test_cosine_threshold_calibration_keeps_similar_and_drops_irrelevant_candidates(tmp_path):
    store = ChromaVectorStore(tmp_path / "threshold", collection_name="threshold_test")
    seed = Retriever(FixedEmbedder(), store)
    # Controlled vectors calibrate the score mapping: identical=1, orthogonal=0, opposite=-1.
    # A threshold of 0.35 keeps the near-identical case and rejects unrelated/opposed candidates.
    from app.services.chunker import TextChunk

    chunks = [
        TextChunk("near", 1, "section", 0, 1, {**candidate()["metadata"], "document_id": "1"}),
        TextChunk("unrelated", 1, "section", 1, 1, {**candidate()["metadata"], "document_id": "2"}),
        TextChunk("opposed", 1, "section", 2, 1, {**candidate()["metadata"], "document_id": "4"}),
    ]
    store.add_chunks("calibration", chunks, [[1.0, 0.0], [0.0, 1.0], [-1.0, 0.0]])

    result = seed.retrieve("a test question", top_k=3)

    assert [passage.text for passage in result.passages] == ["near"]
    assert result.passages[0].relevance_score == pytest.approx(1.0)


def test_below_threshold_results_are_not_treated_as_evidence():
    store = FixedVectorStore([candidate(distance=0.8)])  # cosine similarity = 0.2
    result = Retriever(FixedEmbedder(), store, relevance_threshold=0.35).retrieve("Question")

    assert result.passages == ()
    assert result.retrieval_state == "no_relevant_passages"


def test_missing_citation_metadata_is_rejected():
    malformed = candidate(metadata={"document_name": "Synthetic.pdf", "verification_status": "unverified"})
    result = Retriever(FixedEmbedder(), FixedVectorStore([malformed])).retrieve("Question")

    assert result.passages == ()


def test_invalid_question_and_filter_are_rejected():
    retriever = Retriever(FixedEmbedder(), FixedVectorStore([]))

    with pytest.raises(InvalidQuestionError):
        retriever.retrieve("   ")
    with pytest.raises(InvalidQuestionError):
        retriever.retrieve("Question", metadata_filters={"password": "secret"})


def test_multiple_metadata_filters_are_combined():
    store = FixedVectorStore([candidate()])
    Retriever(FixedEmbedder(), store).retrieve(
        "Question",
        metadata_filters={"document_type": "policy", "academic_year": "2026-2027"},
    )

    assert store.query_args[2] == {
        "$and": [
            {"document_type": "policy"},
            {"academic_year": "2026-2027"},
            {"verification_status": {"$ne": "rejected"}},
        ]
    }


def test_retrieval_suppresses_duplicate_text_and_prefers_page_section_diversity():
    base = candidate(text="A distinct synthetic policy passage about registration and credits.")
    candidates = [
        {**base, "id": "doc-3-chunk-0", "metadata": {**base["metadata"], "page_number": 1, "section": "Registration"}, "distance": 0.05},
        {**base, "id": "doc-3-chunk-1", "metadata": {**base["metadata"], "page_number": 1, "section": "Registration"}, "distance": 0.06},
        {**base, "id": "doc-3-chunk-2", "text": "A separate synthetic passage about examination schedules and term dates.", "metadata": {**base["metadata"], "page_number": 4, "section": "Examinations"}, "distance": 0.12},
        {**base, "id": "doc-3-chunk-3", "text": "A third synthetic passage about course withdrawal deadlines.", "metadata": {**base["metadata"], "page_number": 7, "section": "Course Withdrawal"}, "distance": 0.15},
    ]
    result = Retriever(FixedEmbedder(), FixedVectorStore(candidates), relevance_threshold=0.35).retrieve("Question")

    assert [item.id for item in result.passages] == ["doc-3-chunk-0", "doc-3-chunk-2", "doc-3-chunk-3"]
    assert [item.metadata["page_number"] for item in result.passages] == [1, 4, 7]


def test_default_chat_retrieval_can_be_restricted_to_single_document():
    first = candidate(text="A relevant synthetic passage from the first document.")
    second = {**candidate(text="Another relevant synthetic passage from another document."),
              "id": "doc-9-chunk-0", "metadata": {**candidate()["metadata"], "document_id": "9", "document_name": "Synthetic Other.pdf"}}
    result = Retriever(FixedEmbedder(), FixedVectorStore([first, second])).retrieve(
        "Question", allow_multiple_documents=False
    )
    assert {item.metadata["document_id"] for item in result.passages} == {"3"}


def test_rejected_vectors_are_never_returned_as_evidence():
    metadata = {**candidate()["metadata"], "verification_status": "rejected"}
    result = Retriever(FixedEmbedder(), FixedVectorStore([candidate(metadata=metadata)])).retrieve("Question")
    assert result.passages == ()


def test_database_sync_state_blocks_stale_vector_metadata_and_refreshes_status():
    states = {"3": ("verified", "synced")}
    lookup = lambda document_ids: {key: value for key, value in states.items() if key in document_ids}
    retriever = Retriever(FixedEmbedder(), FixedVectorStore([candidate()]), document_state_lookup=lookup)

    result = retriever.retrieve("Question")
    assert result.passages[0].metadata["verification_status"] == "verified"

    states["3"] = ("rejected", "pending")
    assert retriever.retrieve("Question").passages == ()


def test_unresolvable_document_status_fails_closed():
    retriever = Retriever(FixedEmbedder(), FixedVectorStore([candidate()]), document_state_lookup=lambda _ids: {})
    assert retriever.retrieve("Question").passages == ()


def test_retriever_uses_model_supplied_query_without_domain_specific_rewrite():
    question = "Could you explain the attendance eligibility requirement?"
    embedder = FixedEmbedder()
    store = FixedVectorStore([])

    result = Retriever(embedder, store).retrieve(question)

    assert embedder.questions == [question]
    assert result.question == question
    assert store.query_args[1] == 20


def test_retrieval_query_cleanup_does_not_maintain_greeting_or_topic_rules():
    original = "attendance, eligibility?"
    assert normalize_retrieval_query(original) == original
