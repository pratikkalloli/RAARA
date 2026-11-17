"""Human review ledger for source-bound academic-policy evidence candidates.

The candidate JSONL remains the immutable extraction input. Human decisions are
stored in a separate hash-chained JSONL ledger and overlaid only after source,
page, checksum, and evidence-payload validation succeeds.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Literal

import pymupdf
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, ValidationError, field_validator

from evaluation.policy_evidence import (
    PolicyEvidenceValidationError,
    _eligible_authoritative_policy_evidence,
    validate_policy_evidence,
)
from evaluation.schemas.policy_evidence import PolicyEvidenceRecord


class EvidenceReviewValidationError(ValueError):
    """Raised when an evidence review cannot be safely recorded or used."""


class EvidenceReviewEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sequence: int = Field(ge=1)
    event_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    previous_event_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_id: str = Field(min_length=1)
    evidence_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_pdf_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authority_status: str
    supersession_status: str
    decision: Literal["APPROVE", "REJECT"]
    reviewer_id: str = Field(min_length=1, max_length=200)
    reviewed_at: datetime
    rationale: str = Field(min_length=5, max_length=4000)

    @field_validator("reviewed_at")
    @classmethod
    def timestamp_must_be_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Review timestamp must include a timezone.")
        return value


_ZERO_HASH = "0" * 64
_REVIEW_FIELDS = {"reviewer_status", "reviewer_id", "reviewed_at", "review_rationale", "review_event_id"}


def _canonical_hash(payload: dict) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _evidence_payload(record: PolicyEvidenceRecord | dict) -> dict:
    values = record.model_dump(mode="json") if isinstance(record, PolicyEvidenceRecord) else dict(record)
    return {key: value for key, value in values.items() if key not in _REVIEW_FIELDS}


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    try:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if line.strip():
                rows.append(json.loads(line))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceReviewValidationError(f"Cannot read JSONL file {path}: {exc}") from exc
    return rows


def _read_evidence_rows(path: Path) -> list[dict]:
    try:
        return _read_jsonl(path)
    except EvidenceReviewValidationError as exc:
        raise EvidenceReviewValidationError(f"Invalid evidence candidate file: {exc}") from exc


def _load_verified_records(
    evidence_path: Path,
    inventory_path: Path,
    files_root: Path,
) -> tuple[list[PolicyEvidenceRecord], dict[str, dict]]:
    rows = _read_evidence_rows(evidence_path)
    try:
        records = [PolicyEvidenceRecord.model_validate(row) for row in rows]
        validated = validate_policy_evidence(records, inventory_path, files_root=files_root)
    except (ValidationError, PolicyEvidenceValidationError) as exc:
        raise EvidenceReviewValidationError(f"Evidence provenance/page validation failed: {exc}") from exc
    try:
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        sources = {row["source_id"]: row for row in inventory["sources"]}
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise EvidenceReviewValidationError(f"Cannot load source inventory: {exc}") from exc
    return validated, sources


def inspect_evidence_candidate(
    evidence_id: str,
    *,
    evidence_path: str | Path,
    inventory_path: str | Path,
    files_root: str | Path | None = None,
) -> dict:
    """Return the validated source metadata, exact span, and original page text."""
    evidence_path = Path(evidence_path)
    inventory_path = Path(inventory_path)
    root = Path(files_root) if files_root else inventory_path.parent
    records, sources = _load_verified_records(evidence_path, inventory_path, root)
    matches = [record for record in records if record.evidence_id == evidence_id]
    if len(matches) != 1:
        raise EvidenceReviewValidationError(f"Expected exactly one evidence record for {evidence_id!r}; found {len(matches)}.")
    record = matches[0]
    source = sources[record.document_id]
    pdf_path = (root / record.source_relative_path).resolve()
    try:
        pdf_path.relative_to(root.resolve())
    except ValueError as exc:
        raise EvidenceReviewValidationError("Evidence source path escapes the held-out source root.") from exc
    try:
        document = pymupdf.open(pdf_path)
        page_text = document[record.page_number - 1].get_text()
        document.close()
    except (OSError, ValueError, IndexError) as exc:
        raise EvidenceReviewValidationError(f"Cannot display original evidence page: {exc}") from exc
    return {
        "record": record,
        "source": source,
        "page_text": page_text,
        "pdf_path": pdf_path,
        "source_pdf_sha256": hashlib.sha256(pdf_path.read_bytes()).hexdigest(),
    }


def load_evidence_review_events(review_log_path: str | Path) -> list[EvidenceReviewEvent]:
    """Load and verify the sequence/hash chain of append-only human review events."""
    path = Path(review_log_path)
    rows = _read_jsonl(path)
    events: list[EvidenceReviewEvent] = []
    previous_hash = _ZERO_HASH
    seen_ids: set[str] = set()
    for sequence, row in enumerate(rows, start=1):
        try:
            event = EvidenceReviewEvent.model_validate(row)
        except ValidationError as exc:
            raise EvidenceReviewValidationError(f"Invalid review event at line {sequence}: {exc}") from exc
        if event.sequence != sequence or event.previous_event_sha256 != previous_hash:
            raise EvidenceReviewValidationError(f"Broken review audit chain at sequence {sequence}.")
        payload = event.model_dump(mode="json", exclude={"event_id"})
        if _canonical_hash(payload) != event.event_id:
            raise EvidenceReviewValidationError(f"Review event hash mismatch at sequence {sequence}.")
        if event.evidence_id in seen_ids:
            raise EvidenceReviewValidationError(f"Evidence {event.evidence_id!r} has multiple final review decisions.")
        seen_ids.add(event.evidence_id)
        previous_hash = event.event_id
        events.append(event)
    return events


def record_evidence_review(
    evidence_id: str,
    *,
    decision: Literal["APPROVE", "REJECT"],
    reviewer_id: str,
    rationale: str,
    evidence_path: str | Path,
    inventory_path: str | Path,
    review_log_path: str | Path,
    files_root: str | Path | None = None,
    reviewed_at: datetime | None = None,
) -> EvidenceReviewEvent:
    """Append a human's explicit final decision after revalidating source evidence."""
    reviewer_id = reviewer_id.strip()
    rationale = rationale.strip()
    if not reviewer_id:
        raise EvidenceReviewValidationError("Reviewer identity is required.")
    if len(rationale) < 5:
        raise EvidenceReviewValidationError("Decision rationale must contain at least 5 characters.")
    if decision not in {"APPROVE", "REJECT"}:
        raise EvidenceReviewValidationError("Decision must be APPROVE or REJECT.")

    context = inspect_evidence_candidate(
        evidence_id,
        evidence_path=evidence_path,
        inventory_path=inventory_path,
        files_root=files_root,
    )
    record: PolicyEvidenceRecord = context["record"]
    if record.reviewer_status != "NOT_REVIEWED":
        raise EvidenceReviewValidationError("Candidate already contains a review status; refusing an untracked edit.")
    review_log_path = Path(review_log_path)
    events = load_evidence_review_events(review_log_path)
    if any(event.evidence_id == evidence_id for event in events):
        raise EvidenceReviewValidationError("This evidence already has a final decision in the audit ledger.")
    if decision == "APPROVE":
        if record.authority_status != "VERIFIED_AUTHORITATIVE":
            raise EvidenceReviewValidationError("Only human-classified VERIFIED_AUTHORITATIVE evidence may be approved.")
        if record.supersession_status != "CURRENT":
            raise EvidenceReviewValidationError("Only evidence explicitly classified CURRENT may be approved.")

    timestamp = reviewed_at or datetime.now(timezone.utc)
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise EvidenceReviewValidationError("Review timestamp must include a timezone.")
    previous_hash = events[-1].event_id if events else _ZERO_HASH
    payload = {
        "sequence": len(events) + 1,
        "previous_event_sha256": previous_hash,
        "evidence_id": record.evidence_id,
        "evidence_payload_sha256": _canonical_hash(_evidence_payload(record)),
        "source_pdf_sha256": context["source_pdf_sha256"],
        "authority_status": record.authority_status,
        "supersession_status": record.supersession_status,
        "decision": decision,
        "reviewer_id": reviewer_id,
        "reviewed_at": timestamp.astimezone(timezone.utc).isoformat(),
        "rationale": rationale,
    }
    event = EvidenceReviewEvent(event_id=_canonical_hash(payload), **payload)
    # Hash the schema-normalized serialized form that is persisted to JSONL.
    normalized_payload = event.model_dump(mode="json", exclude={"event_id"})
    event = event.model_copy(update={"event_id": _canonical_hash(normalized_payload)})
    try:
        review_log_path.parent.mkdir(parents=True, exist_ok=True)
        with review_log_path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(event.model_dump(mode="json"), ensure_ascii=False, sort_keys=True) + "\n")
            stream.flush()
    except OSError as exc:
        raise EvidenceReviewValidationError(f"Could not append review audit event: {exc}") from exc
    return event


def reviewed_policy_evidence(
    records: Iterable[PolicyEvidenceRecord | dict],
    *,
    inventory_path: str | Path,
    review_log_path: str | Path,
    files_root: str | Path | None = None,
) -> list[PolicyEvidenceRecord]:
    """Overlay only ledger-backed human decisions onto validated source records."""
    inventory_path = Path(inventory_path)
    root = Path(files_root) if files_root else inventory_path.parent
    normalized: list[PolicyEvidenceRecord] = []
    try:
        normalized = [item if isinstance(item, PolicyEvidenceRecord) else PolicyEvidenceRecord.model_validate(item) for item in records]
        validate_policy_evidence(normalized, inventory_path, files_root=root)
    except (ValidationError, PolicyEvidenceValidationError) as exc:
        raise EvidenceReviewValidationError(f"Evidence provenance/page validation failed: {exc}") from exc

    by_id = {record.evidence_id: record for record in normalized}
    if len(by_id) != len(normalized):
        raise EvidenceReviewValidationError("Duplicate evidence IDs prevent review overlay.")
    events = load_evidence_review_events(review_log_path)
    event_by_id = {event.evidence_id: event for event in events}
    effective: list[PolicyEvidenceRecord] = []
    for record in normalized:
        event = event_by_id.get(record.evidence_id)
        if event is None:
            if record.reviewer_status != "NOT_REVIEWED":
                raise EvidenceReviewValidationError(f"{record.evidence_id}: review status has no matching audit event.")
            effective.append(record)
            continue
        if record.reviewer_status != "NOT_REVIEWED":
            raise EvidenceReviewValidationError(f"{record.evidence_id}: source candidate was modified after review.")
        if event.evidence_payload_sha256 != _canonical_hash(_evidence_payload(record)):
            raise EvidenceReviewValidationError(f"{record.evidence_id}: evidence payload changed after human review.")
        source_path = (root / record.source_relative_path).resolve()
        current_source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
        if event.source_pdf_sha256 != current_source_hash:
            raise EvidenceReviewValidationError(f"{record.evidence_id}: source PDF changed after human review.")
        if event.authority_status != record.authority_status or event.supersession_status != record.supersession_status:
            raise EvidenceReviewValidationError(f"{record.evidence_id}: authority/supersession classification changed after review.")
        if event.decision == "APPROVE" and (
            event.authority_status != "VERIFIED_AUTHORITATIVE" or event.supersession_status != "CURRENT"
        ):
            raise EvidenceReviewValidationError(f"{record.evidence_id}: approval event does not meet authority/currentness gates.")
        effective.append(record.model_copy(update={
            "reviewer_status": "HUMAN_APPROVED" if event.decision == "APPROVE" else "HUMAN_REJECTED",
            "reviewer_id": event.reviewer_id,
            "reviewed_at": event.reviewed_at,
            "review_rationale": event.rationale,
            "review_event_id": event.event_id,
        }))
    unknown = set(event_by_id) - set(by_id)
    if unknown:
        raise EvidenceReviewValidationError(f"Audit ledger references missing evidence IDs: {sorted(unknown)}")
    return effective


def authoritative_reviewed_evidence(
    records: Iterable[PolicyEvidenceRecord | dict],
    *,
    inventory_path: str | Path,
    review_log_path: str | Path,
    files_root: str | Path | None = None,
) -> list[PolicyEvidenceRecord]:
    """Fail-closed selector for records with a verified human approval event."""
    reviewed = reviewed_policy_evidence(
        records,
        inventory_path=inventory_path,
        review_log_path=review_log_path,
        files_root=files_root,
    )
    return _eligible_authoritative_policy_evidence(reviewed)
