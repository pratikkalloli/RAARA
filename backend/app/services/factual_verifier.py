"""Fail-closed checking for numerical claims against cited retrieval evidence."""

from __future__ import annotations

import logging
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.services.generator import AnswerStatus, CitationValidationSummary, StructuredAnswer
from app.services.retriever import RetrievalResult

logger = logging.getLogger(__name__)

_NUMBER = re.compile(
    r"(?<![\w.])(?P<value>(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)"
    r"(?:\s*(?:%|percent(?:age)?|marks?|credits?|days?|weeks?|months?|years?|hours?|minutes?|points?|courses?|attempts?))?",
    re.IGNORECASE,
)
_NUMBERED_LIST_PREFIX = re.compile(r"(?m)^[ \t]*(?:[-*•][ \t]*)?\d{1,2}[.)][ \t]+")
_PAGE_NUMBER = r"(?:pages?|pp?)[ \t]*\.?[ \t]*\d{1,4}(?:[ \t]*[-–—][ \t]*(?:(?:pages?|pp?)[ \t]*\.?[ \t]*)?\d{1,4})?"
_PAGE_REFERENCE = re.compile(
    rf"(?i)(?:"
    rf"\([ \t]*{_PAGE_NUMBER}[ \t]*\)"
    rf"|\[[ \t]*{_PAGE_NUMBER}[ \t]*\]"
    # Unbracketed abbreviated locators are unambiguous citation notation.
    rf"|(?<!\w)pp?\.[ \t]*\d{{1,4}}(?:[ \t]*[-–—][ \t]*\d{{1,4}})?(?!\w)"
    # Spellings of 'page/pages' are stripped only when explicitly introduced
    # as a citation locator, never merely because the answer states a page count.
    rf"|\b(?:see|cite|citation|source)[ \t]+(?:at[ \t]+)?{_PAGE_NUMBER}(?!\w)"
    rf")"
)


class NumericalClaimCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim: str = Field(min_length=1, max_length=2000)
    verdict: Literal["SUPPORTED", "UNSUPPORTED", "AMBIGUOUS"]
    evidence_ids: list[str]


class NumericalReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    checks: list[NumericalClaimCheck]


NumericalClaimChecker = Callable[[str, str, list[dict[str, Any]]], dict[str, Any]]


class FactualConsistencyVerifier:
    """Validate numeric claims without trusting citation identity as semantic proof.

    The configured model evaluates quantity-to-subject/condition alignment. This
    wrapper deterministically requires complete numeric coverage and verifies
    that the model's supporting passage IDs are among the actual cited passages.
    Any incomplete, ambiguous, unsupported, or unavailable review is withheld.
    """

    def __init__(self, checker: NumericalClaimChecker | None) -> None:
        self.checker = checker

    def verify(
        self,
        question: str,
        answer: StructuredAnswer,
        retrieval: RetrievalResult,
    ) -> StructuredAnswer:
        # List ordinals and explicitly formatted citation locators are not
        # factual quantities. Bare factual statements such as "the PDF has 13
        # pages" remain in the numeric review.
        answer_numbers = _answer_claim_number_values(answer.answer)
        if not answer_numbers:
            return answer

        passage_map = {passage.id: passage for passage in retrieval.passages}
        cited_passages = [
            passage_map[item.passage_id]
            for item in answer.evidence
            if item.passage_id in passage_map
        ]
        if not cited_passages or self.checker is None:
            return _withheld(answer, "NUMERICAL_REVIEW_UNAVAILABLE", ambiguous=False)

        allowed_ids = {passage.id for passage in cited_passages}
        context = [
            {
                "passage_id": passage.id,
                "document": str(passage.metadata.get("document_name", "")),
                "page": passage.metadata.get("page_number"),
                "section": str(passage.metadata.get("section", "")),
                "verification_status": str(passage.metadata.get("verification_status", "unverified")),
                "text": passage.text,
            }
            for passage in cited_passages
        ]
        try:
            review = NumericalReview.model_validate(self.checker(question, answer.answer, context))
        except Exception as exc:
            logger.warning("Numerical claim review failed safely (exception_type=%s)", type(exc).__name__)
            return _withheld(answer, "NUMERICAL_REVIEW_UNAVAILABLE", ambiguous=False)

        if not review.checks:
            return _withheld(answer, "NUMERICAL_REVIEW_INCOMPLETE", ambiguous=False)

        reviewed_numbers: set[str] = set()
        ambiguous = False
        for check in review.checks:
            reviewed_numbers.update(_number_values(check.claim))
            if check.verdict != "SUPPORTED":
                ambiguous = ambiguous or check.verdict == "AMBIGUOUS"
                return _withheld(answer, "NUMERICAL_CLAIM_AMBIGUOUS" if ambiguous else "NUMERICAL_CLAIM_UNSUPPORTED", ambiguous=ambiguous)
            if not check.evidence_ids or not set(check.evidence_ids).issubset(allowed_ids):
                return _withheld(answer, "NUMERICAL_CLAIM_UNAVAILABLE_EVIDENCE", ambiguous=False)

        if not answer_numbers.issubset(reviewed_numbers):
            return _withheld(answer, "NUMERICAL_REVIEW_INCOMPLETE", ambiguous=False)
        return answer


def _number_values(text: str) -> set[str]:
    values = set()
    for match in _NUMBER.finditer(text):
        try:
            value = format(Decimal(match.group("value").replace(",", "")).normalize(), "f")
        except (InvalidOperation, ValueError):
            continue
        values.add(value)
    return values


def _answer_claim_number_values(text: str) -> set[str]:
    without_list_ordinals = _NUMBERED_LIST_PREFIX.sub("", text)
    without_citation_locators = _PAGE_REFERENCE.sub("", without_list_ordinals)
    return _number_values(without_citation_locators)


def _withheld(answer: StructuredAnswer, issue: str, *, ambiguous: bool) -> StructuredAnswer:
    message = (
        "The retrieved evidence contains multiple plausible numerical interpretations, so I can't safely choose one."
        if ambiguous
        else "I couldn't verify the numerical claims against the cited evidence, so I can't provide a reliable numerical answer."
    )
    previous = answer.validation
    validation = CitationValidationSummary(
        citation_status=previous.citation_status if previous else "NOT_APPLICABLE",
        semantic_faithfulness="NOT_VERIFIED",
        unsupported_claims_flagged=True,
        issues=list(dict.fromkeys([*(previous.issues if previous else []), issue])),
    )
    return answer.model_copy(update={"answer": message, "status": AnswerStatus.NOT_FOUND, "validation": validation})
