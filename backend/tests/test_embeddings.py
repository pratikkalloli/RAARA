import math
from types import SimpleNamespace

import pytest

from app.config import settings
from app.services.embeddings import (
    EmbeddingError,
    LocalSentenceTransformerEmbeddingService,
    create_embedding_service,
)


class FakeSentenceModel:
    def __init__(self, dimension=384):
        self.dimension = dimension
        self.calls = []

    def get_sentence_embedding_dimension(self):
        return self.dimension

    def encode(self, texts, **kwargs):
        self.calls.append((list(texts), kwargs))
        return [[1.0] + [0.0] * (self.dimension - 1) for _ in texts]


def test_local_embeddings_use_batches_and_return_normalized_384_vectors():
    model = FakeSentenceModel()
    service = LocalSentenceTransformerEmbeddingService(model=model, batch_size=7)

    vectors = service.embed_texts(["first", "second", "third"])

    assert service.provider == "local"
    assert service.model == "sentence-transformers/all-MiniLM-L6-v2"
    assert service.dimensions == 384
    assert len(vectors) == 3
    assert all(len(vector) == 384 for vector in vectors)
    assert all(math.isclose(sum(value * value for value in vector), 1.0) for vector in vectors)
    assert model.calls[0][1]["batch_size"] == 7
    assert model.calls[0][1]["normalize_embeddings"] is True
    assert model.calls[0][1]["show_progress_bar"] is False


def test_query_and_document_embeddings_share_the_same_local_model():
    model = FakeSentenceModel()
    service = LocalSentenceTransformerEmbeddingService(model=model)

    document = service.embed_texts(["document passage"])[0]
    query = service.embed_query("search question")

    assert query == document
    assert [call[0] for call in model.calls] == [["document passage"], ["search question"]]


def test_factory_selects_local_embeddings_without_provider_api_keys(monkeypatch):
    monkeypatch.setattr(settings, "embedding_provider", "local")
    service = create_embedding_service()
    assert isinstance(service, LocalSentenceTransformerEmbeddingService)
    assert service.provider == "local"


def test_wrong_embedding_dimensions_are_rejected():
    with pytest.raises(ValueError, match="384-dimensional"):
        LocalSentenceTransformerEmbeddingService(dimensions=768)


def test_malformed_or_wrong_dimension_vectors_fail_closed():
    model = FakeSentenceModel(dimension=383)
    service = LocalSentenceTransformerEmbeddingService(model=model)
    with pytest.raises(EmbeddingError, match="returned 383 dimensions"):
        service.embed_texts(["document passage"])


def test_empty_embedding_input_makes_no_model_call():
    model = FakeSentenceModel()
    service = LocalSentenceTransformerEmbeddingService(model=model)
    assert service.embed_texts([]) == []
    assert model.calls == []
