"""Local sentence-transformer embeddings for document and query vectors."""

from __future__ import annotations

import logging
import math
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingError(RuntimeError):
    pass


class EmbeddingConfigurationError(EmbeddingError):
    """The local embedding runtime or model is unavailable."""


class LocalSentenceTransformerEmbeddingService:
    """Create matching 384-dimensional document and query embeddings locally."""

    def __init__(
        self,
        *,
        model_name: str | None = None,
        model: Any | None = None,
        batch_size: int | None = None,
        dimensions: int | None = None,
    ) -> None:
        self.model_name = model_name or settings.active_embedding_model
        self.dimensions = settings.active_embedding_dimensions if dimensions is None else dimensions
        self.batch_size = settings.embedding_batch_size if batch_size is None else batch_size
        if self.dimensions != 384:
            raise ValueError("all-MiniLM-L6-v2 embeddings must be 384-dimensional.")
        if self.batch_size <= 0:
            raise ValueError("batch_size must be positive")
        self._model = model

    @property
    def provider(self) -> str:
        return "local"

    @property
    def collection_name(self) -> str:
        return settings.active_embedding_collection_name

    @property
    def model(self) -> str:
        """Keep the prior embedder interface's public model identifier."""
        return self.model_name

    def _load_model(self) -> Any:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise EmbeddingConfigurationError(
                    "Local embeddings require sentence-transformers. Install backend requirements."
                ) from exc
            try:
                loaded = SentenceTransformer(self.model_name, device="cpu")
                actual_dimensions = loaded.get_sentence_embedding_dimension()
                if actual_dimensions != self.dimensions:
                    raise EmbeddingConfigurationError(
                        f"The configured local model returned {actual_dimensions} dimensions; expected 384."
                    )
                self._model = loaded
            except EmbeddingConfigurationError:
                raise
            except Exception as exc:
                logger.error(
                    "Local embedding model could not be loaded (model=%s, exception_type=%s)",
                    self.model_name,
                    type(exc).__name__,
                )
                raise EmbeddingConfigurationError(
                    f"Could not load {self.model_name}. Check the local model cache or network access, then retry."
                ) from None
        return self._model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if any(not isinstance(text, str) or not text.strip() for text in texts):
            raise ValueError("Embedding input must contain non-empty strings.")
        try:
            vectors = self._load_model().encode(
                texts,
                batch_size=self.batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
            values = vectors.tolist() if hasattr(vectors, "tolist") else list(vectors)
            if len(values) != len(texts):
                raise EmbeddingError("The local model returned an unexpected number of vectors.")
            normalized = [_validate_vector(vector, self.dimensions) for vector in values]
            return normalized
        except EmbeddingError:
            raise
        except Exception as exc:
            logger.error("Local embedding generation failed (exception_type=%s)", type(exc).__name__)
            raise EmbeddingError("The local model could not generate document embeddings.") from None

    def embed_query(self, question: str) -> list[float]:
        vectors = self.embed_texts([question])
        if not vectors:
            raise EmbeddingError("The question embedding could not be generated.")
        return vectors[0]


def _validate_vector(values: Any, expected_dimensions: int) -> list[float]:
    try:
        vector = [float(value) for value in values]
    except (TypeError, ValueError) as exc:
        raise EmbeddingError("The local model returned a malformed embedding vector.") from exc
    if len(vector) != expected_dimensions:
        raise EmbeddingError(
            f"The local model returned {len(vector)} dimensions; the active collection requires {expected_dimensions}."
        )
    if any(not math.isfinite(value) for value in vector):
        raise EmbeddingError("The local model returned a non-finite embedding value.")
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        raise EmbeddingError("The local model returned a zero-length embedding vector.")
    return [value / norm for value in vector]


def create_embedding_service() -> LocalSentenceTransformerEmbeddingService:
    if settings.embedding_provider.strip().casefold() != "local":
        raise EmbeddingConfigurationError("EMBEDDING_PROVIDER must be 'local'.")
    return LocalSentenceTransformerEmbeddingService()
