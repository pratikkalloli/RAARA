from __future__ import annotations

from collections.abc import Iterable, Sequence

PageKey = tuple[str, int]


def citation_precision(predicted_evidence_ids: Sequence[str], relevant_evidence_ids: Iterable[str]) -> float:
    """Fraction of unique predicted evidence IDs that are in ground truth; empty prediction is 0."""
    predicted = set(predicted_evidence_ids)
    if not predicted:
        return 0.0
    return len(predicted & set(relevant_evidence_ids)) / len(predicted)


def citation_recall(predicted_evidence_ids: Sequence[str], relevant_evidence_ids: Iterable[str]) -> float | None:
    """Fraction of unique gold evidence IDs cited; None when the question has no gold evidence."""
    relevant = set(relevant_evidence_ids)
    if not relevant:
        return None
    return len(set(predicted_evidence_ids) & relevant) / len(relevant)


def document_identification_accuracy(predicted_document_ids: Iterable[str], relevant_document_ids: Iterable[str]) -> float:
    """Exact set accuracy for source document IDs, including empty/empty unanswerable cases."""
    return float(set(predicted_document_ids) == set(relevant_document_ids))


def page_accuracy(predicted_pages: Iterable[PageKey], relevant_pages: Iterable[PageKey]) -> float:
    """Precision of unique (document_id, page) citations; empty/empty is correct abstention."""
    predicted = set(predicted_pages)
    relevant = set(relevant_pages)
    if not predicted:
        return float(not relevant)
    return len(predicted & relevant) / len(predicted)
