"""Typed schemas for provenance-controlled real-world held-out evaluation data."""
from __future__ import annotations

import re
import unicodedata
from datetime import date
from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator, model_validator

from evaluation.schemas.dataset import ExpectedStatus, PageReference


HeldOutCategory = Literal[
    "direct_factual",
    "multi_passage",
    "multi_document",
    "unanswerable",
    "conflicting_policy",
    "version_sensitive",
    "academic_eligibility",
    "examination_assessment",
    "grading_academic_performance",
    "policy_interpretation",
    "prompt_injection",
]


class SourceProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    acquisition_method: Literal["authorized_public_source", "project_owner_supplied"]
    source_url: AnyHttpUrl | None = None
    source_description: str = Field(min_length=10, max_length=2000)
    retrieved_at: date
    permission_record: str = Field(min_length=5, max_length=2000)

    @model_validator(mode="after")
    def validate_public_source_url(self) -> "SourceProvenance":
        if self.acquisition_method == "authorized_public_source" and self.source_url is None:
            raise ValueError("Authorized public sources require their original source_url.")
        return self


class HeldOutDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(min_length=1, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    document_title: str = Field(min_length=1, max_length=500)
    original_filename: str = Field(min_length=1, max_length=255)
    version: str = Field(min_length=1, max_length=100)
    publication_date: date | None = None
    effective_date: date | None = None
    authority_status: Literal["official", "unofficial_reference"]
    authority_review_status: Literal["pending", "verified", "not_official"]
    authority_reviewer_id: str | None = None
    authority_reviewed_at: date | None = None
    relative_path: str = Field(min_length=1)
    page_count: int = Field(ge=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    provenance: SourceProvenance
    supersedes_document_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_authority_and_versions(self) -> "HeldOutDocument":
        if self.authority_status == "unofficial_reference" and self.authority_review_status != "not_official":
            raise ValueError("Unofficial reference documents must remain marked not_official.")
        if self.authority_status == "official" and self.authority_review_status == "not_official":
            raise ValueError("An official document cannot have not_official review status.")
        if self.authority_review_status == "verified" and not (self.authority_reviewer_id and self.authority_reviewed_at):
            raise ValueError("Verified official status requires an independent reviewer ID and review date.")
        if self.document_id in self.supersedes_document_ids:
            raise ValueError("A document cannot supersede itself.")
        if len(self.supersedes_document_ids) != len(set(self.supersedes_document_ids)):
            raise ValueError("Superseded document IDs must be unique.")
        return self


class HeldOutDocumentRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    registry_version: Literal["1.0"]
    documents: list[HeldOutDocument]


class HeldOutEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(min_length=1)
    document_version: str = Field(min_length=1)
    page_number: int = Field(ge=1)
    section: str = ""
    evidence_id: str = Field(min_length=1)
    text: str = Field(min_length=1)

    @field_validator("text")
    @classmethod
    def evidence_is_nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Evidence text cannot be blank.")
        return value.strip()


AnnotationStatus = Literal[
    "DRAFT", "PENDING_REVIEW", "APPROVED", "REJECTED", "NEEDS_CORRECTION",
    # Phase 8A values remain accepted for already-authored datasets.
    "pending", "reviewed", "approved",
]


class HeldOutQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str = Field(min_length=1, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    question: str = Field(min_length=1, max_length=4000)
    category: HeldOutCategory
    expected_status: ExpectedStatus
    answerable: bool
    expected_answer: str | None = None
    relevant_document_ids: list[str] = Field(default_factory=list)
    relevant_pages: list[PageReference] = Field(default_factory=list)
    relevant_evidence: list[HeldOutEvidence] = Field(default_factory=list)
    expected_claims: list[str] = Field(default_factory=list)
    annotation_notes: str = ""
    annotation_status: AnnotationStatus = "pending"
    annotator_id: str | None = None
    annotated_at: date | None = None
    reviewer_id: str | None = None
    reviewed_at: date | None = None
    attack_surface: Literal["none", "question", "retrieved_document", "both"] = "none"
    dataset_version: str = Field(min_length=1)

    @field_validator("question")
    @classmethod
    def question_is_nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Question cannot be blank.")
        return value.strip()

    @field_validator("expected_answer")
    @classmethod
    def normalize_expected_answer(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @model_validator(mode="after")
    def validate_annotation_content(self) -> "HeldOutQuestion":
        if self.expected_status == "NOT_FOUND":
            if self.answerable:
                raise ValueError("NOT_FOUND annotations must set answerable=false.")
            if self.expected_answer or self.relevant_document_ids or self.relevant_pages or self.relevant_evidence or self.expected_claims:
                raise ValueError("Unanswerable questions must not contain a fabricated answer or mandatory supporting evidence.")
        else:
            if not self.answerable:
                raise ValueError("Answerable statuses require answerable=true.")
            if not self.expected_answer:
                raise ValueError("Answerable questions require an expected_answer.")
            if not self.relevant_document_ids or not self.relevant_evidence:
                raise ValueError("Answerable questions require relevant documents and exact evidence.")
            if not self.expected_claims:
                raise ValueError("Answerable questions require at least one expected_claim.")

        ids = [item.evidence_id for item in self.relevant_evidence]
        if len(ids) != len(set(ids)):
            raise ValueError("Evidence IDs must be unique within a question.")
        mapping_keys = [
            (item.document_id, item.document_version, item.page_number, item.section.strip().casefold(), _norm(item.text))
            for item in self.relevant_evidence
        ]
        if len(mapping_keys) != len(set(mapping_keys)):
            raise ValueError("Duplicate evidence mapping within a question.")
        page_keys = {(item.document_id, item.page_number, item.section.strip().casefold()) for item in self.relevant_pages}
        evidence_pages = {(item.document_id, item.page_number, item.section.strip().casefold()) for item in self.relevant_evidence}
        if not evidence_pages.issubset(page_keys):
            raise ValueError("Every evidence span must have a matching page reference.")
        if len(set(self.relevant_document_ids)) != len(self.relevant_document_ids):
            raise ValueError("Relevant document IDs must be unique.")
        referenced_ids = {item.document_id for item in self.relevant_pages} | {item.document_id for item in self.relevant_evidence}
        if not referenced_ids.issubset(set(self.relevant_document_ids)):
            raise ValueError("Every evidence document must appear in relevant_document_ids.")
        if self.category == "unanswerable" and self.answerable:
            raise ValueError("The unanswerable category requires answerable=false.")
        if self.category == "multi_passage" and len(self.relevant_evidence) < 2:
            raise ValueError("Multi-passage questions require at least two exact evidence spans.")
        if self.category in {"multi_document", "conflicting_policy"} and len(set(self.relevant_document_ids)) < 2:
            raise ValueError(f"{self.category} questions require at least two distinct documents.")
        if self.category == "prompt_injection" and self.attack_surface == "none":
            raise ValueError("Prompt-injection questions must identify an attack surface.")
        if self.annotation_status in {"reviewed", "approved", "APPROVED", "REJECTED", "NEEDS_CORRECTION"}:
            if not self.annotator_id or not self.annotated_at or not self.reviewer_id or not self.reviewed_at:
                raise ValueError("Reviewed/approved annotations require annotator and independent reviewer IDs and dates.")
            if self.annotator_id.strip().casefold() == self.reviewer_id.strip().casefold():
                raise ValueError("The reviewer must be independent of the annotator.")
        return self


class HeldOutQuestionFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_version: str = Field(min_length=1)
    split: Literal["held_out"]
    questions: list[HeldOutQuestion]


def _norm(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"\s+", " ", value).strip()
