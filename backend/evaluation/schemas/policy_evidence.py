"""Schemas for page-anchored policy evidence extracted from held-out candidates."""
from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator, model_validator


AuthorityClassification = Literal[
    "VERIFIED_AUTHORITATIVE",
    "VERIFIED_OFFICIAL_CONTEXT_ONLY",
    "PENDING_HUMAN_AUTHORITY_REVIEW",
    "SUPERSEDED",
    "WRONG_SCOPE",
    "WRONG_INSTITUTION",
    "EXTRACTION_BLOCKED",
    "REJECTED",
]


class PolicyEvidenceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(min_length=1, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    # Source-inventory ID, not a Phase 8A registry document_id.
    document_id: str = Field(min_length=1, pattern=r"^SRC-[0-9]{3}$")
    exact_text: str = Field(min_length=1)
    page_number: int = Field(ge=1)
    section_heading: str = ""
    subsection: str = ""
    document_version: str | None = None
    effective_date: date | None = None
    applicability: str = Field(min_length=5, max_length=2000)
    authority_status: AuthorityClassification
    extraction_method: Literal["pymupdf_text", "ocr"]
    extraction_confidence: Literal["HIGH", "MEDIUM", "LOW"]
    reviewer_status: Literal["NOT_REVIEWED", "PENDING_HUMAN_REVIEW", "HUMAN_APPROVED", "HUMAN_REJECTED"] = "NOT_REVIEWED"
    reviewer_id: str | None = None
    reviewed_at: datetime | None = None
    review_rationale: str | None = None
    review_event_id: str | None = None
    source_url: AnyHttpUrl
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_relative_path: str = Field(min_length=1)
    supersession_status: Literal["UNKNOWN", "CURRENT", "SUPERSEDED", "NOT_ASSESSED"] = "UNKNOWN"
    ocr_uncertainty_notes: str = ""

    @field_validator("exact_text")
    @classmethod
    def exact_text_is_nonblank(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def human_decision_has_audit_metadata(self) -> "PolicyEvidenceRecord":
        if self.reviewer_status in {"HUMAN_APPROVED", "HUMAN_REJECTED"}:
            if not (self.reviewer_id and self.reviewed_at and self.review_rationale and self.review_event_id):
                raise ValueError("A final human evidence decision requires reviewer, timestamp, rationale, and audit event ID.")
            if self.reviewed_at.tzinfo is None or self.reviewed_at.utcoffset() is None:
                raise ValueError("Evidence review timestamps must include a timezone.")
        return self


def normalize_evidence_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    return re.sub(r"\s+", " ", text).strip().casefold()
