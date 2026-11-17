"""Validation and fail-closed selection for extracted policy evidence candidates."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable

from pydantic import ValidationError

from app.services.document_processor import EmptyPDFError, extract_pdf_pages
from evaluation.schemas.policy_evidence import PolicyEvidenceRecord, normalize_evidence_text


class PolicyEvidenceValidationError(ValueError):
    pass


def validate_policy_evidence(
    records: Iterable[PolicyEvidenceRecord | dict],
    source_inventory_path: str | Path,
    *,
    files_root: str | Path | None = None,
) -> list[PolicyEvidenceRecord]:
    """Check candidate provenance, checksums, page bounds, and verbatim source text."""
    inventory_path = Path(source_inventory_path)
    root = Path(files_root) if files_root else inventory_path.parent
    try:
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        sources = {item["source_id"]: item for item in inventory["sources"]}
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise PolicyEvidenceValidationError(f"Cannot load source inventory: {exc}") from exc

    validated: list[PolicyEvidenceRecord] = []
    ids: set[str] = set()
    mappings: set[tuple[str, int, str]] = set()
    for raw in records:
        try:
            record = raw if isinstance(raw, PolicyEvidenceRecord) else PolicyEvidenceRecord.model_validate(raw)
        except ValidationError as exc:
            raise PolicyEvidenceValidationError(f"Invalid evidence record: {exc}") from exc
        if record.evidence_id in ids:
            raise PolicyEvidenceValidationError(f"Duplicate evidence_id {record.evidence_id!r}.")
        ids.add(record.evidence_id)

        source = sources.get(record.document_id)
        if source is None:
            raise PolicyEvidenceValidationError(f"Unknown source document {record.document_id!r}.")
        if source.get("phase8c_document_classification") != record.authority_status:
            raise PolicyEvidenceValidationError(f"{record.document_id}: authority classification does not match inventory.")
        if source.get("url") != str(record.source_url):
            raise PolicyEvidenceValidationError(f"{record.document_id}: source URL does not match inventory.")
        relative_path = source.get("relative_path")
        if not relative_path or relative_path != record.source_relative_path:
            raise PolicyEvidenceValidationError(f"{record.document_id}: source file path is missing or mismatched.")
        path = (root / relative_path).resolve()
        try:
            path.relative_to(root.resolve())
        except ValueError as exc:
            raise PolicyEvidenceValidationError(f"{record.document_id}: source path escapes the evidence root.") from exc
        if not path.is_file():
            raise PolicyEvidenceValidationError(f"{record.document_id}: source PDF is unavailable.")
        raw_pdf = path.read_bytes()
        digest = hashlib.sha256(raw_pdf).hexdigest()
        if digest != source.get("sha256") or digest != record.source_sha256:
            raise PolicyEvidenceValidationError(f"{record.document_id}: source PDF checksum mismatch.")
        if record.extraction_method != "pymupdf_text":
            raise PolicyEvidenceValidationError("OCR-derived evidence requires a separately reviewed OCR artifact; none is registered.")
        try:
            pages = extract_pdf_pages(raw_pdf)
        except EmptyPDFError as exc:
            raise PolicyEvidenceValidationError(f"{record.document_id}: source PDF has no extractable text.") from exc
        if record.page_number > len(pages):
            raise PolicyEvidenceValidationError(f"{record.document_id}: page {record.page_number} exceeds PDF page count {len(pages)}.")
        page = pages[record.page_number - 1]
        if normalize_evidence_text(record.exact_text) not in normalize_evidence_text(page.text):
            raise PolicyEvidenceValidationError(f"{record.evidence_id}: exact_text is absent from the declared PDF page.")
        mapping = (record.document_id, record.page_number, normalize_evidence_text(record.exact_text))
        if mapping in mappings:
            raise PolicyEvidenceValidationError(f"Duplicate evidence mapping for {record.document_id} page {record.page_number}.")
        mappings.add(mapping)
        validated.append(record)
    return validated


def _eligible_authoritative_policy_evidence(records: Iterable[PolicyEvidenceRecord]) -> list[PolicyEvidenceRecord]:
    """Apply status, human-review, and current-version gates to verified records."""
    return [
        record for record in records
        if record.authority_status == "VERIFIED_AUTHORITATIVE"
        and record.reviewer_status == "HUMAN_APPROVED"
        and record.supersession_status == "CURRENT"
    ]


def authoritative_policy_evidence(
    records: Iterable[PolicyEvidenceRecord | dict],
    *,
    inventory_path: str | Path,
    review_log_path: str | Path,
    files_root: str | Path | None = None,
) -> list[PolicyEvidenceRecord]:
    """Select evidence only through source validation and a ledger-backed human review."""
    # Local import avoids a module cycle while ensuring callers cannot promote a
    # record by changing status fields in memory.
    from evaluation.policy_evidence_review import reviewed_policy_evidence

    reviewed = reviewed_policy_evidence(
        records,
        inventory_path=inventory_path,
        review_log_path=review_log_path,
        files_root=files_root,
    )
    return _eligible_authoritative_policy_evidence(reviewed)
