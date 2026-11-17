"""Cosine-distance retrieval over the existing persistent Chroma collection."""

from __future__ import annotations

import logging
import math
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from app.config import settings
from app.services.embeddings import EmbeddingError
from app.services.vector_store import ChromaVectorStore, VectorStoreError

logger = logging.getLogger(__name__)
MAX_QUESTION_LENGTH = 4000
MAX_TOP_K = 50
FILTER_FIELDS = {
    "document_id",
    "document_name",
    "document_type",
    "page_number",
    "section",
    "academic_year",
    "version",
    "effective_date",
    "source_type",
    "verification_status",
    "uploaded_by_user_id",
}


class InvalidQuestionError(ValueError):
    pass


class RetrievalError(RuntimeError):
    pass


class Embedder(Protocol):
    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...


class VectorStore(Protocol):
    def query(self, query_embedding: list[float], *, top_k: int = 5, where: dict[str, Any] | None = None) -> list[dict[str, Any]]: ...


DocumentStateLookup = Callable[[list[str]], dict[str, tuple[str, str]]]


@dataclass(frozen=True)
class RetrievedPassage:
    id: str
    text: str
    metadata: dict[str, Any]
    cosine_distance: float
    relevance_score: float


@dataclass(frozen=True)
class RetrievalResult:
    question: str
    passages: tuple[RetrievedPassage, ...]
    top_k: int
    relevance_threshold: float
    retrieval_state: str = "completed"


class Retriever:
    """Turn questions into embeddings and keep only citation-ready relevant passages.

    Chroma's cosine distance is converted to cosine similarity as ``1 - distance``.
    The threshold is intentionally configurable; 0.35 is a starting value for the
    synthetic calibration tests, not a universal relevance boundary.
    """

    def __init__(
        self,
        embedder: Embedder,
        vector_store: VectorStore | None = None,
        *,
        top_k: int | None = None,
        relevance_threshold: float | None = None,
        document_state_lookup: DocumentStateLookup | None = None,
    ) -> None:
        self.embedder = embedder
        self.vector_store = vector_store or ChromaVectorStore()
        self.document_state_lookup = document_state_lookup
        self.top_k = settings.retrieval_top_k if top_k is None else top_k
        self.relevance_threshold = (
            settings.retrieval_min_relevance if relevance_threshold is None else relevance_threshold
        )
        if not 1 <= self.top_k <= MAX_TOP_K:
            raise ValueError(f"top_k must be between 1 and {MAX_TOP_K}")
        if not -1.0 <= self.relevance_threshold <= 1.0:
            raise ValueError("relevance_threshold must be between -1 and 1")

    def retrieve(
        self,
        question: str,
        *,
        top_k: int | None = None,
        metadata_filters: dict[str, str | int | float | bool] | None = None,
        allow_multiple_documents: bool = True,
    ) -> RetrievalResult:
        normalized_question = question.strip() if isinstance(question, str) else ""
        if not normalized_question:
            raise InvalidQuestionError("A question is required.")
        if len(normalized_question) > MAX_QUESTION_LENGTH:
            raise InvalidQuestionError(f"Questions must be {MAX_QUESTION_LENGTH} characters or fewer.")

        embedding_query = normalize_retrieval_query(normalized_question)

        limit = self.top_k if top_k is None else top_k
        if not 1 <= limit <= MAX_TOP_K:
            raise InvalidQuestionError(f"top_k must be between 1 and {MAX_TOP_K}.")
        where = _build_where_clause(metadata_filters)

        # Avoid an unnecessary provider request when the knowledge base has no chunks.
        count = getattr(self.vector_store, "count", None)
        if callable(count):
            try:
                if count() == 0:
                    return RetrievalResult(
                        normalized_question, (), limit, self.relevance_threshold, retrieval_state="empty_index"
                    )
            except VectorStoreError:
                raise

        try:
            embed_query = getattr(self.embedder, "embed_query", None)
            query_vectors = [embed_query(embedding_query)] if callable(embed_query) else self.embedder.embed_texts([embedding_query])
            if len(query_vectors) != 1 or not query_vectors[0]:
                raise RetrievalError("The question embedding could not be generated.")
            candidate_limit = min(MAX_TOP_K, max(limit, limit * 4))
            candidates = self.vector_store.query(query_vectors[0], top_k=candidate_limit, where=where)
            validated = []
            for candidate in candidates:
                passage = _validated_passage(candidate)
                if passage is None:
                    logger.warning("Ignoring malformed retrieval result without citation metadata")
                    continue
                validated.append(passage)
            state_map = (
                self.document_state_lookup(list(dict.fromkeys(item.metadata.get("document_id", "") for item in validated)))
                if self.document_state_lookup is not None and validated
                else {}
            )
        except (EmbeddingError, VectorStoreError, RetrievalError):
            raise
        except Exception as exc:
            logger.error("Question retrieval failed (exception_type=%s)", type(exc).__name__)
            raise RetrievalError("Unable to retrieve academic document passages.") from exc

        passages: list[RetrievedPassage] = []
        for passage in validated:
            metadata = passage.metadata
            if str(metadata.get("verification_status", "")).casefold() == "rejected":
                continue
            if self.document_state_lookup is not None:
                db_state = state_map.get(str(metadata.get("document_id", "")))
                if db_state is None or db_state[1] != "synced" or db_state[0] == "rejected":
                    continue
                metadata = {**metadata, "verification_status": db_state[0]}
            # Chroma is configured for cosine distance; distance 0 means identical direction.
            score = 1.0 - passage.cosine_distance
            if score < self.relevance_threshold:
                continue
            passages.append(
                RetrievedPassage(
                    id=passage.id,
                    text=passage.text,
                    metadata=metadata,
                    cosine_distance=passage.cosine_distance,
                    relevance_score=score,
                )
            )

        passages = _select_diverse_passages(passages, limit, allow_multiple_documents)
        return RetrievalResult(
            question=normalized_question,
            passages=tuple(passages),
            top_k=limit,
            relevance_threshold=self.relevance_threshold,
            retrieval_state="completed" if passages else (
                "no_candidates" if not candidates else "no_relevant_passages"
            ),
        )


@dataclass(frozen=True)
class _ValidatedCandidate:
    id: str
    text: str
    metadata: dict[str, Any]
    cosine_distance: float


def _validated_passage(candidate: dict[str, Any]) -> _ValidatedCandidate | None:
    if not isinstance(candidate, dict):
        return None
    text = candidate.get("text")
    metadata = candidate.get("metadata")
    identifier = candidate.get("id")
    distance = candidate.get("distance")
    if not isinstance(text, str) or not text.strip() or not isinstance(metadata, dict):
        return None
    if not identifier or not metadata.get("document_name") or not metadata.get("verification_status"):
        return None
    try:
        page_number = int(metadata["page_number"])
        distance = float(distance)
    except (KeyError, TypeError, ValueError):
        return None
    if page_number < 1 or not math.isfinite(distance) or not 0.0 <= distance <= 2.0:
        return None
    normalized_metadata = dict(metadata)
    normalized_metadata["page_number"] = page_number
    for field in ("document_id", "document_type", "section", "academic_year", "version", "effective_date", "source_type"):
        normalized_metadata.setdefault(field, "")
    return _ValidatedCandidate(str(identifier), text.strip(), normalized_metadata, distance)


def _select_diverse_passages(
    passages: list[RetrievedPassage],
    limit: int,
    allow_multiple_documents: bool,
) -> list[RetrievedPassage]:
    """Deduplicate and greedily balance relevance with page/section coverage.

    Lexical overlap is used as a safe, dependency-free approximation to MMR because
    Chroma's query API returns distances but not the stored candidate vectors.
    Highly overlapping chunks are suppressed, while relevance remains the main
    selection signal.
    """
    seen_text: set[str] = set()
    unique: list[RetrievedPassage] = []
    for passage in passages:
        normalized = _normalize_passage_text(passage.text)
        if not normalized or normalized in seen_text:
            continue
        seen_text.add(normalized)
        unique.append(passage)

    if not unique:
        return []
    if not allow_multiple_documents:
        best_document_id = str(unique[0].metadata.get("document_id", ""))
        unique = [p for p in unique if str(p.metadata.get("document_id", "")) == best_document_id]

    unique.sort(key=lambda passage: passage.relevance_score, reverse=True)
    selected: list[RetrievedPassage] = []
    remaining = list(unique)
    while remaining and len(selected) < limit:
        best = None
        best_score = float("-inf")
        for candidate in remaining:
            token_set = _token_set(candidate.text)
            max_overlap = max((_containment_overlap(token_set, _token_set(item.text)) for item in selected), default=0.0)
            if max_overlap >= 0.82:
                continue
            metadata = candidate.metadata
            same_page = any(
                str(item.metadata.get("document_id", "")) == str(metadata.get("document_id", ""))
                and item.metadata.get("page_number") == metadata.get("page_number")
                for item in selected
            )
            same_section = any(
                str(item.metadata.get("document_id", "")) == str(metadata.get("document_id", ""))
                and str(item.metadata.get("section", "")) == str(metadata.get("section", ""))
                for item in selected
            )
            diversity_bonus = (0.08 if not same_page else 0.0) + (0.06 if not same_section else 0.0)
            score = 0.78 * candidate.relevance_score + diversity_bonus - 0.28 * max_overlap
            if score > best_score:
                best = candidate
                best_score = score
        if best is None:
            break
        selected.append(best)
        remaining.remove(best)
    return selected


def _normalize_passage_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(re.sub(r"[^\w\s]", " ", value).split())


def _token_set(value: str) -> set[str]:
    return set(re.findall(r"\w+", _normalize_passage_text(value)))


def _containment_overlap(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / min(len(left), len(right))


def _build_where_clause(filters: dict[str, str | int | float | bool] | None) -> dict[str, Any] | None:
    filters = filters or {}
    unknown_fields = set(filters) - FILTER_FIELDS
    if unknown_fields:
        raise InvalidQuestionError(f"Unsupported document filter field(s): {', '.join(sorted(unknown_fields))}.")
    for key, value in filters.items():
        if not isinstance(value, (str, int, float, bool)):
            raise InvalidQuestionError(f"Document filter {key!r} must be a scalar value.")
    clauses = [{key: value} for key, value in filters.items()]
    clauses.append({"verification_status": {"$ne": "rejected"}})
    return clauses[0] if len(clauses) == 1 else {"$and": clauses}


def normalize_retrieval_query(question: str) -> str:
    """Return the query as interpreted by the model without domain-specific rewrites."""
    return question.strip()
