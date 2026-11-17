from __future__ import annotations

from collections.abc import Iterable, Sequence


def precision_at_k(retrieved_ids: Sequence[str], relevant_ids: Iterable[str], k: int) -> float:
    """Relevant unique IDs in the first k results divided by k; duplicates keep first rank."""
    if k <= 0:
        raise ValueError("k must be positive.")
    relevant = set(relevant_ids)
    top = _unique_in_order(retrieved_ids)[:k]
    return sum(item in relevant for item in top) / k


def recall_at_k(retrieved_ids: Sequence[str], relevant_ids: Iterable[str], k: int) -> float | None:
    """Recall among relevant IDs; None when ground truth has no relevant IDs (e.g. NOT_FOUND)."""
    if k <= 0:
        raise ValueError("k must be positive.")
    relevant = set(relevant_ids)
    if not relevant:
        return None
    top = set(_unique_in_order(retrieved_ids)[:k])
    return len(top & relevant) / len(relevant)


def reciprocal_rank(retrieved_ids: Sequence[str], relevant_ids: Iterable[str]) -> float | None:
    """Reciprocal rank for one query; None when that query has no gold evidence (e.g. NOT_FOUND)."""
    relevant = set(relevant_ids)
    if not relevant:
        return None
    for rank, item in enumerate(_unique_in_order(retrieved_ids), start=1):
        if item in relevant:
            return 1.0 / rank
    return 0.0


def mean_reciprocal_rank(
    retrieved_rankings: Sequence[Sequence[str]],
    relevant_id_sets: Sequence[Iterable[str]],
) -> float | None:
    """Mean reciprocal rank across queries, excluding queries with no gold relevant IDs."""
    if len(retrieved_rankings) != len(relevant_id_sets):
        raise ValueError("Each retrieval ranking must have one corresponding relevance set.")
    scores = [
        score
        for retrieved, relevant in zip(retrieved_rankings, relevant_id_sets)
        if (score := reciprocal_rank(retrieved, relevant)) is not None
    ]
    return sum(scores) / len(scores) if scores else None


def _unique_in_order(items: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(items))
