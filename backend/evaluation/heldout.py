"""Provenance and annotation validation for the real-world held-out split."""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import unicodedata
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

import pymupdf
from pydantic import ValidationError

from evaluation.schemas.dataset import DatasetValidationError, load_dataset
from evaluation.schemas.held_out import HeldOutDocumentRegistry, HeldOutQuestion


class HeldOutValidationError(ValueError):
    pass


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text).casefold()).strip()


def load_registry(registry_path: str | Path) -> HeldOutDocumentRegistry:
    path = Path(registry_path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        registry = HeldOutDocumentRegistry.model_validate(raw)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        raise HeldOutValidationError(f"Invalid document registry {path}: {exc}") from exc
    ids = [doc.document_id for doc in registry.documents]
    if len(ids) != len(set(ids)):
        raise HeldOutValidationError("Duplicate document_id in held-out document registry.")
    checksums = [doc.sha256 for doc in registry.documents]
    if len(checksums) != len(set(checksums)):
        raise HeldOutValidationError("Duplicate document checksum in held-out registry; exact duplicate files are not imported twice.")
    known_ids = set(ids)
    for document in registry.documents:
        if not re.fullmatch(r"[0-9a-f]{64}", document.sha256):
            raise HeldOutValidationError(f"{document.document_id}: invalid SHA-256 checksum format.")
        if any(parent not in known_ids for parent in document.supersedes_document_ids):
            raise HeldOutValidationError(f"{document.document_id}: superseded document is not in the registry.")
        source = _contained_path(path.parent, document.relative_path)
        if not source.is_file():
            raise HeldOutValidationError(f"{document.document_id}: imported source file is missing.")
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        if digest != document.sha256:
            raise HeldOutValidationError(f"{document.document_id}: source SHA-256 mismatch.")
        if source.suffix.casefold() != ".pdf":
            raise HeldOutValidationError(f"{document.document_id}: held-out source must be an original PDF.")
        try:
            with pymupdf.open(source) as pdf:
                if pdf.page_count != document.page_count:
                    raise HeldOutValidationError(f"{document.document_id}: page count does not match the source PDF.")
        except HeldOutValidationError:
            raise
        except Exception as exc:
            raise HeldOutValidationError(f"{document.document_id}: source is not a readable PDF.") from exc
    return registry


def _contained_path(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise HeldOutValidationError("Held-out source path escapes its dataset directory.") from exc
    return candidate


def validate_heldout_dataset(
    dataset_path: str | Path,
    registry_path: str | Path,
    development_dataset_path: str | Path | None = None,
    source_inventory_path: str | Path | None = None,
) -> dict[str, Any]:
    dataset_file = Path(dataset_path)
    registry_file = Path(registry_path)
    registry = load_registry(registry_file)
    doc_map = {doc.document_id: doc for doc in registry.documents}
    try:
        lines = dataset_file.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise HeldOutValidationError(f"Cannot read held-out JSONL {dataset_file}: {exc}") from exc
    questions: list[HeldOutQuestion] = []
    errors: list[str] = []
    dataset_version: str | None = None
    for line_number, raw in enumerate(lines, 1):
        if not raw.strip():
            continue
        try:
            question = HeldOutQuestion.model_validate_json(raw)
            if dataset_version is None:
                dataset_version = question.dataset_version
            elif question.dataset_version != dataset_version:
                raise ValueError("all records must use the same dataset_version")
            questions.append(question)
        except (ValidationError, ValueError) as exc:
            errors.append(f"{dataset_file}:{line_number}: {exc}")
    if errors:
        raise HeldOutValidationError("Held-out question validation failed:\n" + "\n".join(errors))

    question_ids = [q.question_id for q in questions]
    duplicate_ids = sorted({item for item in question_ids if question_ids.count(item) > 1})
    if duplicate_ids:
        raise HeldOutValidationError("Duplicate question_id: " + ", ".join(duplicate_ids))
    evidence_ids: dict[str, tuple[str, str, int, str, str]] = {}
    for question in questions:
        for ref in [*question.relevant_pages, *question.relevant_evidence]:
            document = doc_map.get(ref.document_id)
            if document is None:
                raise HeldOutValidationError(f"{question.question_id}: missing document provenance for {ref.document_id!r}.")
            if ref.page_number > document.page_count:
                raise HeldOutValidationError(f"{question.question_id}: page {ref.page_number} exceeds {ref.document_id} page count.")
        for evidence in question.relevant_evidence:
            doc = doc_map[evidence.document_id]
            if evidence.document_version != doc.version:
                raise HeldOutValidationError(
                    f"{question.question_id}: unsupported document version {evidence.document_version!r} "
                    f"for {doc.document_id}; registry version is {doc.version!r}."
                )
            pdf_path = _contained_path(registry_file.parent, doc.relative_path)
            try:
                with pymupdf.open(pdf_path) as pdf:
                    page_text = _normalize(pdf[evidence.page_number - 1].get_text())
            except Exception as exc:
                raise HeldOutValidationError(f"{question.question_id}: could not extract evidence source page.") from exc
            if _normalize(evidence.text) not in page_text:
                raise HeldOutValidationError(
                    f"{question.question_id}: evidence {evidence.evidence_id!r} is absent from the declared source page."
                )
            mapping = (doc.document_id, doc.version, evidence.page_number, evidence.section.casefold(), _normalize(evidence.text))
            old_mapping = evidence_ids.get(evidence.evidence_id)
            if old_mapping is not None and old_mapping != mapping:
                raise HeldOutValidationError(f"Evidence ID {evidence.evidence_id!r} maps to conflicting source passages.")
            evidence_ids[evidence.evidence_id] = mapping
        if question.category == "version_sensitive" and any(not doc_map[d].version for d in question.relevant_document_ids):
            raise HeldOutValidationError(f"{question.question_id}: version-sensitive evidence lacks a document version.")
        if question.expected_status == "CONFLICTING_SOURCES" or question.category == "conflicting_policy":
            docs = [doc_map[d] for d in question.relevant_document_ids if d in doc_map]
            if len({doc.version for doc in docs}) < 2:
                raise HeldOutValidationError(f"{question.question_id}: conflict evidence must identify at least two document versions.")
        if question.annotation_status in {"approved", "APPROVED"}:
            used_docs = [doc_map[d] for d in question.relevant_document_ids]
            if any(doc.authority_status != "official" or doc.authority_review_status != "verified" for doc in used_docs):
                raise HeldOutValidationError(
                    f"{question.question_id}: approved regulatory annotations require independently verified official sources."
                )

    development_file = Path(development_dataset_path) if development_dataset_path else (
        registry_file.parent.parent / "development" / "raara_synthetic_starter_v0.1.0.jsonl"
    )
    if development_file.is_file():
        try:
            development_questions = load_dataset(development_file)
        except DatasetValidationError as exc:
            raise HeldOutValidationError(f"Cannot verify held-out/development separation: {exc}") from exc
        dev_ids = {q.question_id.casefold() for q in development_questions}
        dev_text = {_normalize(q.question) for q in development_questions}
        overlapping_ids = sorted(q.question_id for q in questions if q.question_id.casefold() in dev_ids)
        overlapping_text = sorted(q.question_id for q in questions if _normalize(q.question) in dev_text)
        if overlapping_ids or overlapping_text:
            raise HeldOutValidationError(
                f"Held-out/development overlap detected (IDs={overlapping_ids}, normalized questions={overlapping_text})."
            )

    annotated = [q for q in questions if q.annotator_id and q.annotated_at]
    approved = [q for q in questions if q.annotation_status in {"approved", "APPROVED"}]
    incomplete = [q for q in questions if q.annotation_status not in {"approved", "APPROVED"}]
    official_verified = [d for d in registry.documents if d.authority_status == "official" and d.authority_review_status == "verified"]
    category_counts = dict(sorted(Counter(q.category for q in questions).items()))
    summary = {
        "dataset_version": dataset_version or "held_out-1.0",
        "dataset_split": "held_out",
        "genuine_documents_imported": len(registry.documents),
        "official_documents_verified": len(official_verified),
        "unofficial_reference_documents": sum(d.authority_status == "unofficial_reference" for d in registry.documents),
        "valid_questions": len(questions),
        "annotated_questions": len(annotated),
        "approved_questions": len(approved),
        "incomplete_annotations": len(incomplete),
        "category_counts": category_counts,
        "target_question_range": [40, 60],
        "ready_for_phase_8b": bool(official_verified),
        "ready_for_phase_8c": len(approved) >= 40 and all(q in approved for q in questions),
        "dataset_readiness": "EMPTY" if not questions and not registry.documents else "INCOMPLETE",
        "status_note": "Exact normalized text and ID overlap are checked. Human review is still required to catch semantically reworded development leakage.",
    }
    if source_inventory_path is not None and Path(source_inventory_path).is_file():
        try:
            inventory = json.loads(Path(source_inventory_path).read_text(encoding="utf-8"))
            sources = inventory["sources"]
            acquisition = inventory["acquisition_summary"]
            if not isinstance(sources, list) or not isinstance(acquisition, dict):
                raise ValueError("sources must be a list and acquisition_summary must be an object")
            summary.update({
                "total_discovered_sources": len(sources),
                "official_verified_sources": sum(source.get("classification") == "OFFICIAL_VERIFIED" for source in sources),
                "official_unverified_sources": sum(source.get("classification") == "OFFICIAL_UNVERIFIED" for source in sources),
                "wrong_institution_sources": sum(source.get("classification") == "WRONG_INSTITUTION" for source in sources),
                "third_party_reference_sources": sum(source.get("classification") == "THIRD_PARTY_REFERENCE" for source in sources),
                "rejected_sources": sum(source.get("classification") in {"WRONG_INSTITUTION", "DUPLICATE", "THIRD_PARTY_REFERENCE"} for source in sources),
                **acquisition,
            })
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise HeldOutValidationError(f"Invalid source acquisition inventory {source_inventory_path}: {exc}") from exc
    return summary


def import_pdf_document(
    source_path: str | Path,
    registry_path: str | Path,
    *,
    document_id: str,
    document_title: str,
    version: str,
    authority_status: str,
    provenance: dict[str, Any],
    publication_date: str | None = None,
    effective_date: str | None = None,
    supersedes_document_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Copy a permitted PDF byte-for-byte and register it without altering the source."""
    source = Path(source_path).resolve()
    registry_file = Path(registry_path)
    registry = load_registry(registry_file)
    if not source.is_file() or source.suffix.casefold() != ".pdf":
        raise HeldOutValidationError("The supplied source must be an existing PDF file.")
    if any(doc.document_id == document_id for doc in registry.documents):
        raise HeldOutValidationError(f"Document ID {document_id!r} is already registered.")
    raw = source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if any(doc.sha256 == digest for doc in registry.documents):
        raise HeldOutValidationError("Exact duplicate document bytes already exist in the registry.")
    try:
        with pymupdf.open(stream=raw, filetype="pdf") as pdf:
            page_count = pdf.page_count
            if page_count < 1:
                raise HeldOutValidationError("The PDF contains no pages.")
    except HeldOutValidationError:
        raise
    except Exception as exc:
        raise HeldOutValidationError("The supplied file is not a readable PDF.") from exc
    filename = f"{document_id}__{source.name}"
    relative_path = f"sources/{filename}"
    target = _contained_path(registry_file.parent, relative_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise HeldOutValidationError("Refusing to overwrite an existing imported source file.")
    record = {
        "document_id": document_id,
        "document_title": document_title,
        "original_filename": source.name,
        "version": version,
        "publication_date": publication_date,
        "effective_date": effective_date,
        "authority_status": authority_status,
        "authority_review_status": "pending" if authority_status == "official" else "not_official",
        "authority_reviewer_id": None,
        "authority_reviewed_at": None,
        "relative_path": relative_path,
        "page_count": page_count,
        "sha256": digest,
        "provenance": provenance,
        "supersedes_document_ids": supersedes_document_ids or [],
    }
    try:
        from evaluation.schemas.held_out import HeldOutDocument
        parsed = HeldOutDocument.model_validate(record)
        missing_supersedes = set(parsed.supersedes_document_ids) - {doc.document_id for doc in registry.documents}
        if missing_supersedes:
            raise HeldOutValidationError("Superseded document IDs must already exist in the registry.")
        with target.open("xb") as stream:
            stream.write(raw)
        updated = registry.model_copy(update={"documents": [*registry.documents, parsed]})
        registry_file.write_text(updated.model_dump_json(indent=2) + "\n", encoding="utf-8")
    except Exception:
        if target.exists():
            target.unlink()
        raise
    return parsed.model_dump(mode="json")


def append_heldout_question(
    question: HeldOutQuestion,
    dataset_path: str | Path,
    registry_path: str | Path,
    development_dataset_path: str | Path | None = None,
) -> dict[str, Any]:
    """Validate a draft against source PDFs and dev split before atomically appending it."""
    target = Path(dataset_path)
    current = target.read_text(encoding="utf-8") if target.exists() else ""
    candidate_text = current + ("" if not current or current.endswith("\n") else "\n") + question.model_dump_json() + "\n"
    fd, temp_name = tempfile.mkstemp(prefix="heldout-validation-", suffix=".jsonl", dir=target.parent)
    os.close(fd)
    validation_file = Path(temp_name)
    try:
        validation_file.write_text(candidate_text, encoding="utf-8")
        summary = validate_heldout_dataset(validation_file, registry_path, development_dataset_path)
        # Validation completes before any write; existing records remain in candidate_text.
        target.write_text(candidate_text, encoding="utf-8")
        return summary
    finally:
        validation_file.unlink(missing_ok=True)


def update_annotation_review(
    question_id: str,
    status: str,
    reviewer_id: str,
    dataset_path: str | Path,
    registry_path: str | Path,
    development_dataset_path: str | Path | None = None,
    reviewed_at: str | None = None,
) -> dict[str, Any]:
    """Record an independent review transition only after validating the full proposed split."""
    if status not in {"reviewed", "approved", "APPROVED", "REJECTED", "NEEDS_CORRECTION"}:
        raise HeldOutValidationError("Review status must be reviewed, APPROVED, REJECTED, or NEEDS_CORRECTION.")
    target = Path(dataset_path)
    try:
        old_text = target.read_text(encoding="utf-8")
        records = [json.loads(line) for line in old_text.splitlines() if line.strip()]
    except (OSError, json.JSONDecodeError) as exc:
        raise HeldOutValidationError(f"Cannot read held-out annotation file: {exc}") from exc
    matches = [index for index, item in enumerate(records) if item.get("question_id") == question_id]
    if len(matches) != 1:
        raise HeldOutValidationError(f"Expected exactly one annotation for {question_id!r}; found {len(matches)}.")
    item = dict(records[matches[0]])
    if item.get("annotation_status") in {"approved", "APPROVED"}:
        raise HeldOutValidationError("Approved annotations are immutable through this workflow; create a new version to amend them.")
    item["annotation_status"] = status
    item["reviewer_id"] = reviewer_id
    item["reviewed_at"] = reviewed_at or date.today().isoformat()
    try:
        records[matches[0]] = json.loads(HeldOutQuestion.model_validate(item).model_dump_json())
    except ValidationError as exc:
        raise HeldOutValidationError(f"Review transition is incomplete or invalid: {exc}") from exc
    candidate_text = "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records)
    fd, temp_name = tempfile.mkstemp(prefix="heldout-review-", suffix=".jsonl", dir=target.parent)
    os.close(fd)
    validation_file = Path(temp_name)
    try:
        validation_file.write_text(candidate_text, encoding="utf-8")
        summary = validate_heldout_dataset(validation_file, registry_path, development_dataset_path)
        target.write_text(candidate_text, encoding="utf-8")
        return summary
    finally:
        validation_file.unlink(missing_ok=True)
