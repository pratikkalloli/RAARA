from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Literal

import pymupdf
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

QuestionCategory = Literal[
    "direct_factual",
    "attendance_eligibility",
    "assessment_calculation",
    "grading_sgpa_cgpa",
    "backlogs_supplementary",
    "lateral_entry_progression",
    "multi_passage",
    "multi_document",
    "unanswerable",
    "conflicting_version",
    "prompt_injection",
]
ExpectedStatus = Literal["SUPPORTED", "PARTIALLY_SUPPORTED", "NOT_FOUND", "CONFLICTING_SOURCES"]
SourceType = Literal["synthetic_controlled", "permitted_source", "PROJECT_AUTHORED"]


class PageReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(min_length=1)
    page_number: int = Field(ge=1)
    section: str = ""


class EvidenceReference(PageReference):
    evidence_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    document_version: str | None = None
    dataset_type: Literal["SYNTHETIC_PROJECT_DATA"] | None = None
    is_official_university_policy: Literal[False] | None = None
    source_type: SourceType | None = None
    dataset_version: str | None = None

    @field_validator("text")
    @classmethod
    def evidence_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Evidence text must not be blank.")
        return value.strip()


class EvaluationQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str = Field(min_length=1, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    question: str = Field(min_length=1, max_length=4000)
    category: QuestionCategory
    expected_status: ExpectedStatus
    reference_answer: str | None = None
    relevant_document_ids: list[str] = Field(default_factory=list)
    relevant_pages: list[PageReference] = Field(default_factory=list)
    relevant_evidence: list[EvidenceReference] = Field(default_factory=list)
    expected_claims: list[str] = Field(default_factory=list)
    evaluation_notes: str | None = None
    dataset_version: str = Field(min_length=1)
    source_type: SourceType
    attack_surface: Literal["none", "question", "retrieved_document", "both"] = "none"
    # Optional fields keep Phase 7A–7E datasets backwards compatible. Synthetic
    # Phase 9A records populate them explicitly and are checked by its validator.
    answerable: bool | None = None
    expected_citations: list[EvidenceReference] = Field(default_factory=list)
    evaluation_rationale: str | None = None
    difficulty: Literal["easy", "medium", "hard"] | None = None
    dataset_type: Literal["SYNTHETIC_PROJECT_DATA"] | None = None
    is_official_university_policy: Literal[False] | None = None
    dataset_split: Literal["development", "held_out", "conflict"] | None = None
    calculation: dict[str, Any] | None = None

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Question must not be blank.")
        return value.strip()

    @field_validator("reference_answer")
    @classmethod
    def normalize_reference_answer(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @field_validator("expected_claims")
    @classmethod
    def claims_must_be_nonblank(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("Expected claims must not contain blank strings.")
        return normalized

    @model_validator(mode="after")
    def validate_evidence_contract(self) -> "EvaluationQuestion":
        if self.answerable is not None and self.answerable != (self.expected_status != "NOT_FOUND"):
            raise ValueError("answerable must agree with expected_status.")
        if len(set(self.relevant_document_ids)) != len(self.relevant_document_ids):
            raise ValueError("relevant_document_ids must not contain duplicates.")
        evidence_ids = [item.evidence_id for item in self.relevant_evidence]
        if len(set(evidence_ids)) != len(evidence_ids):
            raise ValueError("relevant_evidence evidence_id values must not contain duplicates.")
        page_keys = {(item.document_id, item.page_number, item.section) for item in self.relevant_pages}
        evidence_page_keys = {
            (item.document_id, item.page_number, item.section) for item in self.relevant_evidence
        }
        if not evidence_page_keys.issubset(page_keys):
            raise ValueError("Every evidence reference must also appear in relevant_pages.")
        referenced_documents = {
            item.document_id for item in self.relevant_pages
        } | {item.document_id for item in self.relevant_evidence}
        if not referenced_documents.issubset(set(self.relevant_document_ids)):
            raise ValueError("Every referenced document must appear in relevant_document_ids.")

        if self.expected_status == "NOT_FOUND":
            if self.reference_answer is not None:
                raise ValueError("Unanswerable questions must not have a fabricated reference_answer.")
            if self.relevant_document_ids or self.relevant_pages or self.relevant_evidence or self.expected_claims:
                raise ValueError("Unanswerable questions must not declare relevant evidence or expected claims.")
        else:
            if not self.reference_answer:
                raise ValueError("Answerable questions require a reference_answer.")
            if not self.relevant_document_ids or not self.relevant_evidence:
                raise ValueError("Answerable questions require relevant documents and evidence.")
            if not self.expected_claims:
                raise ValueError("Answerable questions require at least one expected_claim.")
        if self.expected_citations and [item.model_dump() for item in self.expected_citations] != [
            item.model_dump() for item in self.relevant_evidence
        ]:
            raise ValueError("expected_citations must reference the exact relevant evidence records.")
        if self.category == "unanswerable" and self.expected_status != "NOT_FOUND":
            raise ValueError("The unanswerable category requires expected_status NOT_FOUND.")
        if self.category == "multi_document" and len(self.relevant_document_ids) < 2:
            raise ValueError("Multi-document questions must reference at least two documents.")
        if self.category == "multi_passage" and len(self.relevant_evidence) < 2:
            raise ValueError("Multi-passage questions must reference at least two evidence passages.")
        if self.category == "conflicting_version" and self.expected_status == "CONFLICTING_SOURCES":
            document_ids = {item.document_id for item in self.relevant_evidence}
            if len(document_ids) < 2:
                raise ValueError("Conflicting-version answers require evidence from at least two documents/versions.")
        if self.category == "prompt_injection" and self.attack_surface == "none":
            raise ValueError("Prompt-injection questions must identify an adversarial surface.")
        return self


class EvaluationDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_version: str = Field(min_length=1)
    questions: list[EvaluationQuestion]


class DatasetValidationError(ValueError):
    pass


def load_dataset(path: str | Path) -> list[EvaluationQuestion]:
    dataset_path = Path(path)
    records: list[EvaluationQuestion] = []
    errors: list[str] = []
    try:
        lines = dataset_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise DatasetValidationError(f"Cannot read dataset {dataset_path}: {exc}") from exc
    for line_number, raw_line in enumerate(lines, start=1):
        if not raw_line.strip():
            continue
        try:
            records.append(EvaluationQuestion.model_validate_json(raw_line))
        except (ValidationError, ValueError) as exc:
            errors.append(f"{dataset_path}:{line_number}: {exc}")
    if errors:
        raise DatasetValidationError("Dataset record validation failed:\n" + "\n".join(errors))
    if not records:
        raise DatasetValidationError(f"Dataset contains no question records: {dataset_path}")
    return records


def validate_dataset(dataset_path: str | Path, manifest_path: str | Path) -> EvaluationDataset:
    dataset_file = Path(dataset_path)
    manifest_file = Path(manifest_path)
    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DatasetValidationError(f"Cannot read dataset manifest {manifest_file}: {exc}") from exc

    records = load_dataset(dataset_file)
    version = manifest.get("dataset_version")
    if not isinstance(version, str) or not version:
        raise DatasetValidationError("Manifest must declare a non-empty dataset_version.")
    question_ids = [record.question_id for record in records]
    duplicates = sorted({item for item in question_ids if question_ids.count(item) > 1})
    if duplicates:
        raise DatasetValidationError("Duplicate question_id value(s): " + ", ".join(duplicates))
    mismatched_versions = [record.question_id for record in records if record.dataset_version != version]
    if mismatched_versions:
        raise DatasetValidationError(
            f"Dataset version mismatch: manifest={version!r}; question(s)=" + ", ".join(mismatched_versions)
        )

    documents = manifest.get("documents")
    if not isinstance(documents, list):
        raise DatasetValidationError("Manifest must include a documents list.")
    document_map: dict[str, dict] = {}
    for item in documents:
        document_id = item.get("document_id") if isinstance(item, dict) else None
        if not isinstance(document_id, str) or not document_id:
            raise DatasetValidationError("Each manifest document must have a non-empty document_id.")
        if document_id in document_map:
            raise DatasetValidationError(f"Duplicate manifest document_id {document_id!r}.")
        document_map[document_id] = item
        relative_path = item.get("path")
        if not isinstance(relative_path, str) or not relative_path:
            raise DatasetValidationError(f"Manifest document {document_id!r} has no source path.")
        source_path = (manifest_file.parent / relative_path).resolve()
        try:
            source_path.relative_to(manifest_file.parent.resolve())
        except ValueError as exc:
            raise DatasetValidationError(f"Source path for {document_id!r} escapes the evaluation dataset directory.") from exc
        if not source_path.is_file():
            raise DatasetValidationError(f"Source document for {document_id!r} does not exist: {relative_path}")
        expected_hash = item.get("sha256")
        if expected_hash:
            actual_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
            if actual_hash != expected_hash:
                raise DatasetValidationError(f"Source hash mismatch for {document_id!r}.")
        page_count = item.get("page_count")
        if not isinstance(page_count, int) or page_count < 1:
            raise DatasetValidationError(f"Manifest document {document_id!r} has an invalid page_count.")

    for record in records:
        referenced_types = {document_map[document_id].get("source_type") for document_id in record.relevant_document_ids if document_id in document_map}
        if referenced_types and record.source_type not in referenced_types:
            raise DatasetValidationError(f"{record.question_id}: source_type does not match its referenced documents.")
        if not referenced_types and record.source_type != manifest.get("source_type"):
            raise DatasetValidationError(f"{record.question_id}: source_type does not match the corpus manifest.")
        if record.category == "conflicting_version" and record.expected_status == "CONFLICTING_SOURCES":
            versions = {document_map[document_id].get("version") for document_id in record.relevant_document_ids if document_id in document_map}
            if len(versions) < 2:
                raise DatasetValidationError(f"{record.question_id}: conflicting sources must use distinct manifest versions.")
        refs = [*record.relevant_pages, *record.relevant_evidence]
        for reference in refs:
            doc = document_map.get(reference.document_id)
            if doc is None:
                raise DatasetValidationError(
                    f"{record.question_id}: unknown relevant document_id {reference.document_id!r}."
                )
            if reference.page_number > doc["page_count"]:
                raise DatasetValidationError(
                    f"{record.question_id}: page {reference.page_number} exceeds {reference.document_id} page_count."
                )
            _validate_evidence_in_source(record.question_id, reference, doc, manifest_file.parent)
    return EvaluationDataset(dataset_version=version, questions=records)


def _validate_evidence_in_source(question_id: str, evidence: PageReference, document: dict, base: Path) -> None:
    if not isinstance(evidence, EvidenceReference):
        return
    source_path = (base / document["path"]).resolve()
    if source_path.suffix.casefold() != ".pdf":
        return
    try:
        with pymupdf.open(source_path) as pdf:
            page_text = pdf[evidence.page_number - 1].get_text()
    except Exception as exc:
        raise DatasetValidationError(f"{question_id}: could not extract evidence source {source_path.name}.") from exc
    normalize = lambda text: re.sub(r"\s+", " ", text).strip().casefold()
    if normalize(evidence.text) not in normalize(page_text):
        raise DatasetValidationError(
            f"{question_id}: evidence {evidence.evidence_id!r} is not present on declared PDF page "
            f"{evidence.page_number} of {document['document_id']}."
        )
