from app.services.factual_verifier import FactualConsistencyVerifier
from app.services.generator import (
    AnswerStatus,
    CitationValidationSummary,
    EvidenceItem,
    SourceItem,
    StructuredAnswer,
)
from app.services.retriever import RetrievalResult, RetrievedPassage


def _passage(text):
    metadata = {
        "document_id": "synthetic-1",
        "document_name": "Synthetic numerical test (NOT OFFICIAL)",
        "document_type": "synthetic_test",
        "page_number": 2,
        "section": "Fictional assessment examples",
        "academic_year": "",
        "version": "1",
        "effective_date": "",
        "source_type": "synthetic_test",
        "verification_status": "unverified",
    }
    return RetrievedPassage("passage-1", text, metadata, 0.1, 0.9)


def _answer(passage, text):
    metadata = passage.metadata
    return StructuredAnswer(
        answer=text,
        evidence=[EvidenceItem(
            text=passage.text,
            document=metadata["document_name"],
            page=metadata["page_number"],
            section=metadata["section"],
            passage_id=passage.id,
            document_id=metadata["document_id"],
            version=metadata["version"],
            effective_date=metadata["effective_date"],
            academic_year=metadata["academic_year"],
            verification_status=metadata["verification_status"],
        )],
        sources=[SourceItem(
            document=metadata["document_name"], document_id=metadata["document_id"],
            document_type=metadata["document_type"], pages=[metadata["page_number"]],
            sections=[metadata["section"]], academic_year="", version="1", effective_date="",
            source_type="synthetic_test", verification_status="unverified",
        )],
        status=AnswerStatus.PARTIALLY_SUPPORTED,
        validation=CitationValidationSummary(citation_status="VERIFIED"),
    )


def _retrieval(passage):
    return RetrievalResult("What is the fictional assessment distribution?", (passage,), 5, 0.35)


def test_correct_numeric_values_require_question_relevant_evidence_mapping():
    passage = _passage(
        "Fictional allocation: ISA receives 40 marks and ESA receives 60 marks. "
        "Separate fictional student scores are 32 ISA marks and 45 ESA marks."
    )
    answer = _answer(passage, "The allocation is 40 ISA marks and 60 ESA marks.")
    verifier = FactualConsistencyVerifier(lambda *_: {
        "checks": [{"claim": "40 ISA allocation and 60 ESA allocation marks", "verdict": "SUPPORTED", "evidence_ids": [passage.id]}]
    })

    result = verifier.verify("What are the marks allocated to ISA and ESA?", answer, _retrieval(passage))

    assert result.status == AnswerStatus.PARTIALLY_SUPPORTED
    assert "40" in result.answer and "60" in result.answer
    assert result.evidence[0].passage_id == passage.id


def test_numbered_summary_ordinals_and_page_locators_are_not_factual_claims():
    passage = _passage(
        "Synthetic assessment allocation: ISA is 40 marks and ESA is 60 marks."
    )
    answer = _answer(
        passage,
        "1. ISA allocation is 40 marks (page 2).\n2. ESA allocation is 60 marks (page 2).",
    )
    verifier = FactualConsistencyVerifier(lambda *_: {
        "checks": [
            {"claim": "40 marks allocated to ISA", "verdict": "SUPPORTED", "evidence_ids": [passage.id]},
            {"claim": "60 marks allocated to ESA", "verdict": "SUPPORTED", "evidence_ids": [passage.id]},
        ]
    })

    result = verifier.verify("Summarize the synthetic allocation.", answer, _retrieval(passage))

    assert result.status == AnswerStatus.PARTIALLY_SUPPORTED
    assert "40 marks" in result.answer and "60 marks" in result.answer


def test_academic_year_range_is_checked_but_incidental_page_number_is_ignored():
    passage = _passage("Synthetic example for academic year 2025-2026 lists an 80 percent value.")
    answer = _answer(passage, "For academic year 2025–2026, the value is 80%. See page 2.")
    verifier = FactualConsistencyVerifier(lambda *_: {
        "checks": [{
            "claim": "80 percent applies in academic year 2025-2026; page 2 is a citation locator",
            "verdict": "SUPPORTED",
            "evidence_ids": [passage.id],
        }]
    })

    result = verifier.verify("Summarize the dated synthetic example.", answer, _retrieval(passage))

    assert result.status == AnswerStatus.PARTIALLY_SUPPORTED
    assert "2025–2026" in result.answer and "80%" in result.answer


def test_factual_page_count_and_chapter_count_are_not_stripped_as_citations():
    passage = _passage("The synthetic PDF contains 13 pages and the guide has 10 chapters.")
    answer = _answer(passage, "The PDF contains 13 pages and the document has 10 chapters.")

    incomplete = FactualConsistencyVerifier(lambda *_: {
        "checks": [{"claim": "The document has 10 chapters", "verdict": "SUPPORTED", "evidence_ids": [passage.id]}]
    }).verify("How long is the PDF and how many chapters?", answer, _retrieval(passage))
    assert incomplete.status == AnswerStatus.NOT_FOUND
    assert "NUMERICAL_REVIEW_INCOMPLETE" in incomplete.validation.issues

    complete = FactualConsistencyVerifier(lambda *_: {
        "checks": [{
            "claim": "The synthetic PDF contains 13 pages and its guide has 10 chapters",
            "verdict": "SUPPORTED", "evidence_ids": [passage.id],
        }]
    }).verify("How long is the PDF and how many chapters?", answer, _retrieval(passage))
    assert complete.status == AnswerStatus.PARTIALLY_SUPPORTED


def test_explicit_page_citation_and_page_range_are_not_factual_quantities():
    passage = _passage("Synthetic allocation: ISA is 40 marks and ESA is 60 marks.")
    answer = _answer(passage, "ISA is 40 marks (pp. 2–3); ESA is 60 marks. See pages 2–4.")
    verifier = FactualConsistencyVerifier(lambda *_: {
        "checks": [
            {"claim": "40 ISA marks", "verdict": "SUPPORTED", "evidence_ids": [passage.id]},
            {"claim": "60 ESA marks", "verdict": "SUPPORTED", "evidence_ids": [passage.id]},
        ]
    })

    result = verifier.verify("What are the synthetic allocations?", answer, _retrieval(passage))

    assert result.status == AnswerStatus.PARTIALLY_SUPPORTED
    assert "40 marks" in result.answer and "60 marks" in result.answer


def test_nearby_but_unrelated_numeric_values_are_withheld_even_with_valid_citation():
    passage = _passage(
        "Fictional assessment allocation: ISA receives 40 marks and ESA receives 60 marks. "
        "A different fictional learner's achieved scores are 32 ISA marks and 45 ESA marks."
    )
    answer = _answer(passage, "ISA has 32 marks and ESA has 45 marks.")
    verifier = FactualConsistencyVerifier(lambda *_: {
        "checks": [{"claim": "32 ISA allocation and 45 ESA allocation marks", "verdict": "UNSUPPORTED", "evidence_ids": [passage.id]}]
    })

    result = verifier.verify("What is the assessment allocation for ISA and ESA?", answer, _retrieval(passage))

    assert result.status == AnswerStatus.NOT_FOUND
    assert "32" not in result.answer and "45" not in result.answer
    assert result.evidence[0].passage_id == passage.id
    assert result.validation.citation_status == "VERIFIED"
    assert result.validation.unsupported_claims_flagged is True
    assert "NUMERICAL_CLAIM_UNSUPPORTED" in result.validation.issues


def test_individual_student_scores_are_supported_only_for_the_score_question():
    passage = _passage(
        "Synthetic allocation: ISA 40 marks and ESA 60 marks. "
        "Separate synthetic individual student scores: ISA 32 marks and ESA 45 marks."
    )
    answer = _answer(passage, "The individual student's scores are ISA 32 marks and ESA 45 marks.")
    verifier = FactualConsistencyVerifier(lambda *_: {
        "checks": [{
            "claim": "32 ISA marks and 45 ESA marks are the individual student's achieved scores",
            "verdict": "SUPPORTED",
            "evidence_ids": [passage.id],
        }]
    })

    result = verifier.verify("What are the individual student's scores?", answer, _retrieval(passage))

    assert result.status == AnswerStatus.PARTIALLY_SUPPORTED
    assert "32 marks" in result.answer and "45 marks" in result.answer


def test_conflicting_numerical_values_are_abstained_not_replaced():
    passage = _passage("Two conflicting fictional versions list 75% and 80% for the same sample condition.")
    answer = _answer(passage, "The required fictional value is 75%.")
    verifier = FactualConsistencyVerifier(lambda *_: {
        "checks": [{"claim": "75 percent, ambiguous due to conflicting values", "verdict": "AMBIGUOUS", "evidence_ids": [passage.id]}]
    })

    result = verifier.verify("What is the sample condition value?", answer, _retrieval(passage))

    assert result.status == AnswerStatus.NOT_FOUND
    assert "75" not in result.answer and "80" not in result.answer
    assert "multiple plausible" in result.answer
    assert "NUMERICAL_CLAIM_AMBIGUOUS" in result.validation.issues


def test_percentages_dates_ranges_and_units_are_reviewed():
    passage = _passage("Synthetic test range is 2025-2026; 75 percent attendance; 12 credits; 3 to 5 days.")
    answer = _answer(passage, "For 2025-2026, the synthetic example uses 75 percent, 12 credits, and 3 to 5 days.")
    reviewed = "2025-2026 75 percent attendance 12 credits 3 to 5 days"
    verifier = FactualConsistencyVerifier(lambda *_: {
        "checks": [{"claim": reviewed, "verdict": "SUPPORTED", "evidence_ids": [passage.id]}]
    })

    result = verifier.verify("Summarize the dated example quantities.", answer, _retrieval(passage))

    assert result.status == AnswerStatus.PARTIALLY_SUPPORTED
    assert "75 percent" in result.answer


def test_irrelevant_present_value_is_withheld_when_checker_rejects_relation():
    passage = _passage("Synthetic answer deadline is 10 days. This unrelated example has 90 marks.")
    answer = _answer(passage, "The answer deadline is 90 days.")
    verifier = FactualConsistencyVerifier(lambda *_: {
        "checks": [{"claim": "90 days deadline", "verdict": "UNSUPPORTED", "evidence_ids": [passage.id]}]
    })

    result = verifier.verify("What is the answer deadline?", answer, _retrieval(passage))

    assert result.status == AnswerStatus.NOT_FOUND
    assert "90" not in result.answer


def test_fabricated_evidence_id_or_incomplete_numeric_review_fails_closed():
    passage = _passage("Synthetic value is 18 of 20, or 90%.")
    answer = _answer(passage, "The value is 90% (18 of 20).")
    fake_id = FactualConsistencyVerifier(lambda *_: {
        "checks": [{"claim": "90 percent from synthetic value", "verdict": "SUPPORTED", "evidence_ids": ["fabricated"]}]
    })
    incomplete = FactualConsistencyVerifier(lambda *_: {
        "checks": [{"claim": "90 percent", "verdict": "SUPPORTED", "evidence_ids": [passage.id]}]
    })

    assert fake_id.verify("What is the ratio?", answer, _retrieval(passage)).status == AnswerStatus.NOT_FOUND
    result = incomplete.verify("What is the ratio?", answer, _retrieval(passage))
    assert result.status == AnswerStatus.NOT_FOUND
    assert "NUMERICAL_REVIEW_INCOMPLETE" in result.validation.issues


def test_checker_failure_fails_closed_but_non_numeric_answer_needs_no_review():
    passage = _passage("A synthetic qualitative example.")
    numeric = _answer(passage, "The result is 4 marks.")
    non_numeric = _answer(passage, "The example describes a fictional process.")
    calls = []

    def broken(*_):
        calls.append(True)
        raise RuntimeError("mock checker failure")

    verifier = FactualConsistencyVerifier(broken)
    result = verifier.verify("What is the result?", numeric, _retrieval(passage))
    passed = verifier.verify("What is described?", non_numeric, _retrieval(passage))

    assert result.status == AnswerStatus.NOT_FOUND
    assert "NUMERICAL_REVIEW_UNAVAILABLE" in result.validation.issues
    assert passed.status == AnswerStatus.PARTIALLY_SUPPORTED
    assert len(calls) == 1
