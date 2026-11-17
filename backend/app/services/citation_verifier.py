"""Deterministically verify generated citations against one retrieval result.

This module verifies citation identity and metadata. It does not prove that a
natural-language claim is semantically entailed by the cited passage.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date
from typing import Any

from app.services.generator import (
    AnswerStatus,
    CitationValidationSummary,
    EvidenceItem,
    SourceItem,
    StructuredAnswer,
)
from app.services.retriever import RetrievalResult, RetrievedPassage

logger = logging.getLogger(__name__)
_NUMERIC_VERSION = re.compile(r"^\D*(\d+(?:\.\d+)*)$")


@dataclass(frozen=True)
class CitationVerificationResult:
    answer: StructuredAnswer
    valid_passage_ids: tuple[str, ...]
    issues: tuple[str, ...]
    semantic_faithfulness_verified: bool = False


class CitationVerifier:
    """Reject unmatched citation fields without substituting another passage."""

    def verify(
        self,
        answer: StructuredAnswer,
        retrieval: RetrievalResult,
    ) -> CitationVerificationResult:
        issues = list(answer.validation.issues if answer.validation else [])
        passage_map = {passage.id: passage for passage in retrieval.passages}
        valid_passages: list[RetrievedPassage] = []
        seen_ids: set[str] = set()

        if not retrieval.passages:
            if answer.status == AnswerStatus.NOT_FOUND and not answer.evidence and not answer.sources:
                validation = CitationValidationSummary(
                    citation_status="NOT_APPLICABLE",
                    semantic_faithfulness="NOT_VERIFIED",
                    unsupported_claims_flagged=(answer.validation.unsupported_claims_flagged if answer.validation else False),
                    issues=issues,
                )
                response = answer.model_copy(update={"validation": validation})
                return CitationVerificationResult(response, (), tuple(issues))
            if answer.status != AnswerStatus.NOT_FOUND or answer.evidence or answer.sources:
                _add_issue(issues, "NO_RETRIEVED_EVIDENCE")
            response = _abstain(answer, issues, citation_status="NOT_APPLICABLE")
            return CitationVerificationResult(response, (), tuple(issues))

        # A model-generated abstention carries no citations by design. There is
        # nothing to validate or replace, and rewriting its explanation here
        # would discard the evidence-state details supplied to the abstention
        # generator. Keep the safe NOT_FOUND response and mark citation review
        # as not applicable.
        if answer.status == AnswerStatus.NOT_FOUND and not answer.evidence and not answer.sources:
            validation = CitationValidationSummary(
                citation_status="NOT_APPLICABLE",
                semantic_faithfulness="NOT_VERIFIED",
                unsupported_claims_flagged=(answer.validation.unsupported_claims_flagged if answer.validation else False),
                issues=issues,
            )
            response = answer.model_copy(update={"validation": validation})
            return CitationVerificationResult(response, (), tuple(issues))

        for citation in answer.evidence:
            passage, issue = self._verify_evidence(citation, passage_map)
            if issue:
                _add_issue(issues, issue)
                continue
            if passage is None:
                _add_issue(issues, "INVALID_PASSAGE_REFERENCE")
                continue
            if passage.id in seen_ids:
                _add_issue(issues, "DUPLICATE_PASSAGE_REFERENCE")
                continue
            seen_ids.add(passage.id)
            valid_passages.append(passage)

        if answer.status != AnswerStatus.NOT_FOUND and not answer.evidence:
            _add_issue(issues, "MISSING_EVIDENCE_REFERENCES")

        canonical_sources = _canonical_sources(valid_passages)
        if valid_passages:
            source_issues = _verify_source_summaries(answer.sources, canonical_sources)
            for issue in source_issues:
                _add_issue(issues, issue)
        elif answer.sources:
            _add_issue(issues, "SOURCE_WITHOUT_VALID_EVIDENCE")

        outdated_ids = _possibly_superseded_ids(valid_passages, retrieval.passages)
        if outdated_ids:
            _add_issue(issues, "POSSIBLY_SUPERSEDED_VERSION")

        if not valid_passages:
            citation_status = "FAILED" if issues else "NOT_APPLICABLE"
            response = _abstain(answer, issues, citation_status=citation_status)
            return CitationVerificationResult(response, (), tuple(issues))

        unverified = any(_is_unverified(passage.metadata) for passage in valid_passages)
        citation_issues = [issue for issue in issues if issue not in {"POSSIBLY_SUPERSEDED_VERSION"}]
        original_status = answer.status
        final_status = original_status
        if original_status == AnswerStatus.NOT_FOUND:
            final_status = AnswerStatus.NOT_FOUND
        elif original_status == AnswerStatus.CONFLICTING_SOURCES:
            distinct_sources = {
                (
                    str(passage.metadata.get("document_id", "")),
                    str(passage.metadata.get("document_name", "")),
                    str(passage.metadata.get("version", "")),
                )
                for passage in valid_passages
            }
            if len(distinct_sources) < 2 or citation_issues:
                final_status = AnswerStatus.PARTIALLY_SUPPORTED if len(distinct_sources) >= 1 else AnswerStatus.NOT_FOUND
        elif citation_issues or unverified or outdated_ids:
            final_status = AnswerStatus.PARTIALLY_SUPPORTED

        answer_text = answer.answer
        if citation_issues:
            answer_text = _prepend_once(
                answer_text,
                "Some generated source references failed citation checks; only validated evidence is listed. Treat unsupported details as unconfirmed. ",
            )
        if unverified:
            answer_text = _prepend_once(
                answer_text,
                "Evidence includes unverified documents and is not confirmed as official policy. ",
            )
        if any(str(passage.metadata.get("verification_status", "")).casefold() == "verified" for passage in valid_passages):
            answer_text = _prepend_once(
                answer_text,
                "Administrator verification indicates internal review only; university issuance has not been independently established. ",
            )
        if outdated_ids:
            answer_text = _prepend_once(
                answer_text,
                "A newer retrieved version may supersede some cited material; no replacement source was assumed. ",
            )

        citation_status = "PARTIAL" if issues else "VERIFIED"
        unsupported_flag = any(
            issue in issues
            for issue in (
                "MISSING_EVIDENCE_REFERENCES",
                "INVALID_PASSAGE_REFERENCE",
                "UNAVAILABLE_PASSAGE_REFERENCE",
                "MISSING_SOURCE_METADATA",
                "DOCUMENT_ID_MISMATCH",
                "DOCUMENT_NAME_MISMATCH",
                "PAGE_NUMBER_MISMATCH",
                "SECTION_MISMATCH",
                "EVIDENCE_TEXT_MISMATCH",
                "INVALID_SOURCE_SUMMARY",
            )
        )
        response = answer.model_copy(
            update={
                "answer": answer_text,
                "evidence": [_canonical_evidence(passage) for passage in valid_passages],
                "sources": canonical_sources,
                "status": final_status,
                "validation": CitationValidationSummary(
                    citation_status=citation_status,
                    semantic_faithfulness="NOT_VERIFIED",
                    unsupported_claims_flagged=unsupported_flag,
                    issues=issues,
                ),
            }
        )
        return CitationVerificationResult(
            response,
            tuple(passage.id for passage in valid_passages),
            tuple(issues),
        )

    @staticmethod
    def _verify_evidence(
        citation: EvidenceItem,
        passages: dict[str, RetrievedPassage],
    ) -> tuple[RetrievedPassage | None, str | None]:
        if not citation.passage_id:
            return None, "MISSING_PASSAGE_ID"
        passage = passages.get(citation.passage_id)
        if passage is None:
            return None, "INVALID_PASSAGE_REFERENCE"

        metadata = passage.metadata
        required = ("document_id", "document_name", "page_number", "verification_status")
        if any(metadata.get(field) in (None, "") for field in required):
            return None, "MISSING_SOURCE_METADATA"
        try:
            page_number = int(metadata["page_number"])
        except (TypeError, ValueError):
            return None, "MISSING_SOURCE_METADATA"

        checks = (
            (str(citation.document_id) == str(metadata["document_id"]), "DOCUMENT_ID_MISMATCH"),
            (citation.document == str(metadata["document_name"]), "DOCUMENT_NAME_MISMATCH"),
            (citation.page == page_number, "PAGE_NUMBER_MISMATCH"),
            (citation.section == str(metadata.get("section") or ""), "SECTION_MISMATCH"),
            (citation.text == passage.text, "EVIDENCE_TEXT_MISMATCH"),
            (
                citation.verification_status == str(metadata["verification_status"]),
                "VERIFICATION_STATUS_MISMATCH",
            ),
            (citation.version == str(metadata.get("version") or ""), "VERSION_MISMATCH"),
        )
        for matches, issue in checks:
            if not matches:
                return None, issue
        return passage, None


def _canonical_evidence(passage: RetrievedPassage) -> EvidenceItem:
    metadata = passage.metadata
    return EvidenceItem(
        text=passage.text,
        document=str(metadata["document_name"]),
        page=int(metadata["page_number"]),
        section=str(metadata.get("section") or ""),
        passage_id=passage.id,
        document_id=str(metadata["document_id"]),
        version=str(metadata.get("version") or ""),
        effective_date=str(metadata.get("effective_date") or ""),
        academic_year=str(metadata.get("academic_year") or ""),
        verification_status=str(metadata["verification_status"]),
    )


def _canonical_sources(passages: list[RetrievedPassage]) -> list[SourceItem]:
    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for passage in passages:
        metadata = passage.metadata
        key = (
            str(metadata["document_id"]),
            str(metadata["document_name"]),
            str(metadata.get("version") or ""),
        )
        source = grouped.setdefault(
            key,
            {
                "document": str(metadata["document_name"]),
                "document_id": str(metadata["document_id"]),
                "document_type": str(metadata.get("document_type") or ""),
                "pages": [],
                "sections": [],
                "academic_year": str(metadata.get("academic_year") or ""),
                "version": str(metadata.get("version") or ""),
                "effective_date": str(metadata.get("effective_date") or ""),
                "source_type": str(metadata.get("source_type") or ""),
                "verification_status": str(metadata["verification_status"]),
            },
        )
        page = int(metadata["page_number"])
        section = str(metadata.get("section") or "")
        if page not in source["pages"]:
            source["pages"].append(page)
        if section and section not in source["sections"]:
            source["sections"].append(section)
    return [SourceItem(**source) for source in grouped.values()]


def _verify_source_summaries(
    supplied: list[SourceItem],
    canonical: list[SourceItem],
) -> list[str]:
    issues: list[str] = []
    if len(supplied) != len(canonical):
        issues.append("INVALID_SOURCE_SUMMARY")
    expected = {
        (source.document_id, source.document, source.version): source
        for source in canonical
    }
    for source in supplied:
        key = (source.document_id, source.document, source.version)
        actual = expected.get(key)
        if actual is None:
            issues.append("INVALID_SOURCE_SUMMARY")
            continue
        fields = (
            "document_type",
            "academic_year",
            "effective_date",
            "source_type",
            "verification_status",
        )
        if any(getattr(source, field) != getattr(actual, field) for field in fields):
            issues.append("INVALID_SOURCE_SUMMARY")
        if set(source.pages) != set(actual.pages) or set(source.sections) != set(actual.sections):
            issues.append("INVALID_SOURCE_SUMMARY")
    return list(dict.fromkeys(issues))


def _possibly_superseded_ids(
    cited: list[RetrievedPassage],
    retrieved: tuple[RetrievedPassage, ...],
) -> set[str]:
    cited_ids = {passage.id for passage in cited}
    outdated: set[str] = set()
    for passage in cited:
        metadata = passage.metadata
        identity = (
            str(metadata.get("document_name", "")).casefold(),
            str(metadata.get("document_type", "")).casefold(),
            str(metadata.get("academic_year", "")),
        )
        for possible_newer in retrieved:
            if possible_newer.id in cited_ids:
                continue
            newer_metadata = possible_newer.metadata
            newer_identity = (
                str(newer_metadata.get("document_name", "")).casefold(),
                str(newer_metadata.get("document_type", "")).casefold(),
                str(newer_metadata.get("academic_year", "")),
            )
            if identity == newer_identity and _is_newer(newer_metadata, metadata):
                outdated.add(passage.id)
                break
    return outdated


def _is_newer(candidate: dict[str, Any], baseline: dict[str, Any]) -> bool:
    candidate_date = _parse_date(candidate.get("effective_date"))
    baseline_date = _parse_date(baseline.get("effective_date"))
    if candidate_date and baseline_date and candidate_date != baseline_date:
        return candidate_date > baseline_date
    candidate_version = _version_key(candidate.get("version"))
    baseline_version = _version_key(baseline.get("version"))
    return bool(candidate_version and baseline_version and candidate_version > baseline_version)


def _parse_date(value: Any) -> date | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _version_key(value: Any) -> tuple[int, ...] | None:
    if not isinstance(value, str):
        return None
    match = _NUMERIC_VERSION.fullmatch(value.strip())
    if not match:
        return None
    return tuple(int(part) for part in match.group(1).split("."))


def _is_unverified(metadata: dict[str, Any]) -> bool:
    return str(metadata.get("verification_status", "unverified")).casefold() != "verified"


def _abstain(
    answer: StructuredAnswer,
    issues: list[str],
    *,
    citation_status: str,
) -> StructuredAnswer:
    return answer.model_copy(
        update={
            "answer": "I couldn't provide a sufficiently supported answer from the available retrieved documents.",
            "evidence": [],
            "sources": [],
            "status": AnswerStatus.NOT_FOUND,
            "validation": CitationValidationSummary(
                citation_status=citation_status,
                semantic_faithfulness="NOT_VERIFIED",
                unsupported_claims_flagged=bool(issues),
                issues=issues,
            ),
        }
    )


def _add_issue(issues: list[str], issue: str) -> None:
    if issue not in issues:
        issues.append(issue)


def _prepend_once(answer: str, warning: str) -> str:
    if warning.casefold().strip() in answer.casefold():
        return answer
    return warning + answer
