from __future__ import annotations

import pytest
from pydantic import ValidationError

from evaluation.metrics.answer import SemanticAssessment, normalized_exact_match
from evaluation.metrics.citations import (
    citation_precision,
    citation_recall,
    document_identification_accuracy,
    page_accuracy,
)
from evaluation.metrics.performance import estimate_api_cost_usd, total_latency_ms
from evaluation.metrics.retrieval import mean_reciprocal_rank, precision_at_k, recall_at_k, reciprocal_rank


def test_precision_at_k_deduplicates_ids_and_uses_fixed_k_denominator() -> None:
    assert precision_at_k(["a", "a", "irrelevant", "b"], {"a", "b"}, 3) == pytest.approx(2 / 3)


def test_recall_at_k_handles_multiple_relevant_documents_and_duplicates() -> None:
    assert recall_at_k(["doc-1", "doc-1", "doc-2"], {"doc-1", "doc-2", "doc-3"}, 3) == pytest.approx(2 / 3)


def test_mrr_uses_first_unique_relevant_rank_and_averages_queries() -> None:
    rankings = [["x", "x", "a"], ["b", "x"], ["none"]]
    gold = [{"a"}, {"b"}, set()]
    assert reciprocal_rank(rankings[0], gold[0]) == pytest.approx(0.5)
    assert mean_reciprocal_rank(rankings, gold) == pytest.approx(0.75)


def test_mrr_requires_corresponding_relevance_sets() -> None:
    with pytest.raises(ValueError, match="one corresponding"):
        mean_reciprocal_rank([["a"]], [])


def test_retrieval_metrics_handle_empty_and_unanswerable_cases() -> None:
    assert precision_at_k([], {"p1"}, 5) == 0.0
    assert recall_at_k([], {"p1"}, 5) == 0.0
    assert reciprocal_rank([], {"p1"}) == 0.0
    assert recall_at_k(["unexpected"], set(), 5) is None
    assert mean_reciprocal_rank([["unexpected"]], [set()]) is None


def test_citation_precision_recall_deduplicate_evidence_ids() -> None:
    assert citation_precision(["e1", "e1", "e2", "fabricated"], {"e1", "e2", "e3"}) == pytest.approx(2 / 3)
    assert citation_recall(["e1", "e1", "e2"], {"e1", "e2", "e3"}) == pytest.approx(2 / 3)
    assert citation_precision([], {"e1"}) == 0.0
    assert citation_recall([], set()) is None


def test_document_identification_accuracy_is_exact_set_match() -> None:
    assert document_identification_accuracy(["doc-a", "doc-b"], ["doc-b", "doc-a"]) == 1.0
    assert document_identification_accuracy(["doc-a"], ["doc-a", "doc-b"]) == 0.0
    assert document_identification_accuracy([], []) == 1.0


def test_page_accuracy_uses_document_page_pairs() -> None:
    assert page_accuracy([("doc-a", 1), ("doc-b", 2)], [("doc-a", 1)]) == 0.5
    assert page_accuracy([], []) == 1.0
    assert page_accuracy([], [("doc-a", 1)]) == 0.0


def test_normalized_exact_match_is_only_a_normalized_lexical_check() -> None:
    assert normalized_exact_match("15 March, 2026!", "15 march 2026") == 1.0
    assert normalized_exact_match("eighty five percent", "85 percent") == 0.0


def test_semantic_assessment_is_not_claimed_without_an_assessor() -> None:
    assessment = SemanticAssessment()
    assert assessment.faithfulness is None
    with pytest.raises(ValidationError, match="explicit human or llm_judge assessor"):
        SemanticAssessment(faithfulness=1.0)
    judged = SemanticAssessment(assessor="human", faithfulness=0.9)
    assert judged.faithfulness == 0.9


def test_missing_latency_token_usage_and_cost_are_unavailable_not_zero() -> None:
    assert total_latency_ms(12.0, None) is None
    assert total_latency_ms(12.0, 3.5) == pytest.approx(15.5)
    assert estimate_api_cost_usd(1000, None, 1.0, 2.0) is None
    assert estimate_api_cost_usd(1000, 500, 1.0, 2.0) == pytest.approx(0.002)
    assert estimate_api_cost_usd(1000, 500, None, 2.0) is None


def test_invalid_latency_is_rejected() -> None:
    with pytest.raises(ValueError, match="finite"):
        total_latency_ms(float("inf"), 1.0)
