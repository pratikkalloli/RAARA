from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pymupdf
import pytest

from evaluation.policy_evidence_review import (
    EvidenceReviewValidationError,
    authoritative_reviewed_evidence,
    inspect_evidence_candidate,
    load_evidence_review_events,
    record_evidence_review,
    reviewed_policy_evidence,
)


def _fixture(tmp_path: Path, *, authority: str = "VERIFIED_AUTHORITATIVE", supersession: str = "CURRENT") -> dict:
    """Test-only synthetic fixture; never an actual university policy source."""
    root = tmp_path / "held_out"
    (root / "documents").mkdir(parents=True)
    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_text((45, 45), "SYNTHETIC TEST DOCUMENT — NOT OFFICIAL REGULATION")
    page.insert_text((45, 90), "Synthetic-only statement used to test human evidence review.")
    source_bytes = pdf.tobytes()
    pdf.close()
    (root / "documents" / "TEST-ONLY.pdf").write_bytes(source_bytes)
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    source = {
        "source_id": "SRC-901",
        "title": "SYNTHETIC TEST DOCUMENT — NOT OFFICIAL REGULATION",
        "document_title": "SYNTHETIC TEST DOCUMENT — NOT OFFICIAL REGULATION",
        "url": "https://example.invalid/test-only.pdf",
        "relative_path": "documents/TEST-ONLY.pdf",
        "sha256": source_hash,
        "phase8c_document_classification": authority,
        "issuing_authority": "TEST FIXTURE ONLY; no actual issuer",
        "publication_date": None,
        "programme": "synthetic test only",
        "campus": "synthetic test only",
        "admission_batch": "synthetic test only",
    }
    inventory_path = root / "source_inventory.json"
    inventory_path.write_text(json.dumps({"sources": [source]}), encoding="utf-8")
    evidence = {
        "evidence_id": "TEST-EVIDENCE-1",
        "document_id": "SRC-901",
        "exact_text": "Synthetic-only statement used to test human evidence review.",
        "page_number": 1,
        "section_heading": "Test page",
        "subsection": "",
        "document_version": "fixture-v1",
        "effective_date": None,
        "applicability": "Synthetic test fixture only; not university policy.",
        "authority_status": authority,
        "extraction_method": "pymupdf_text",
        "extraction_confidence": "HIGH",
        "reviewer_status": "NOT_REVIEWED",
        "source_url": source["url"],
        "source_sha256": source_hash,
        "source_relative_path": source["relative_path"],
        "supersession_status": supersession,
        "ocr_uncertainty_notes": "Test fixture only.",
    }
    evidence_path = root / "evidence_candidates.jsonl"
    evidence_path.write_text(json.dumps(evidence) + "\n", encoding="utf-8")
    return {
        "root": root,
        "inventory": inventory_path,
        "evidence": evidence_path,
        "log": root / "evidence_reviews.jsonl",
        "row": evidence,
    }


def test_inspection_displays_verbatim_passage_and_original_page_text(tmp_path):
    fixture = _fixture(tmp_path)
    view = inspect_evidence_candidate(
        "TEST-EVIDENCE-1", evidence_path=fixture["evidence"], inventory_path=fixture["inventory"], files_root=fixture["root"]
    )
    assert view["record"].exact_text in view["page_text"]
    assert "SYNTHETIC TEST DOCUMENT" in view["page_text"]
    assert "NOT OFFICIAL REGULATION" in view["page_text"]
    assert view["source"]["issuing_authority"].startswith("TEST FIXTURE ONLY")


def test_explicit_approval_is_audited_and_selects_only_valid_authoritative_evidence(tmp_path):
    fixture = _fixture(tmp_path)
    original_bytes = fixture["evidence"].read_bytes()
    event = record_evidence_review(
        "TEST-EVIDENCE-1", decision="APPROVE", reviewer_id="human-reviewer-1",
        rationale="Test-only approval path exercise.", evidence_path=fixture["evidence"],
        inventory_path=fixture["inventory"], review_log_path=fixture["log"], files_root=fixture["root"],
        reviewed_at=datetime(2026, 11, 13, tzinfo=timezone.utc),
    )
    assert event.decision == "APPROVE"
    assert fixture["evidence"].read_bytes() == original_bytes  # source evidence was not edited
    records = [fixture["row"]]
    effective = reviewed_policy_evidence(
        records, inventory_path=fixture["inventory"], review_log_path=fixture["log"], files_root=fixture["root"]
    )
    assert effective[0].reviewer_status == "HUMAN_APPROVED"
    assert effective[0].reviewer_id == "human-reviewer-1"
    assert effective[0].review_event_id == event.event_id
    assert authoritative_reviewed_evidence(
        records, inventory_path=fixture["inventory"], review_log_path=fixture["log"], files_root=fixture["root"]
    ) == effective


def test_pending_authority_cannot_be_approved(tmp_path):
    fixture = _fixture(tmp_path, authority="PENDING_HUMAN_AUTHORITY_REVIEW")
    with pytest.raises(EvidenceReviewValidationError, match="VERIFIED_AUTHORITATIVE"):
        record_evidence_review(
            "TEST-EVIDENCE-1", decision="APPROVE", reviewer_id="human-reviewer-1",
            rationale="Should be rejected by authority gate.", evidence_path=fixture["evidence"],
            inventory_path=fixture["inventory"], review_log_path=fixture["log"], files_root=fixture["root"],
        )
    assert not fixture["log"].exists()


def test_stale_or_wrong_source_page_cannot_be_approved(tmp_path):
    fixture = _fixture(tmp_path)
    row = dict(fixture["row"], exact_text="Text not present on source page.")
    fixture["evidence"].write_text(json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(EvidenceReviewValidationError, match="absent from the declared PDF page"):
        record_evidence_review(
            "TEST-EVIDENCE-1", decision="APPROVE", reviewer_id="human-reviewer-1",
            rationale="Should fail exact page validation.", evidence_path=fixture["evidence"],
            inventory_path=fixture["inventory"], review_log_path=fixture["log"], files_root=fixture["root"],
        )
    assert not fixture["log"].exists()


def test_rejection_records_human_identity_and_rationale_without_candidate_mutation(tmp_path):
    fixture = _fixture(tmp_path, authority="VERIFIED_OFFICIAL_CONTEXT_ONLY", supersession="NOT_ASSESSED")
    original_bytes = fixture["evidence"].read_bytes()
    record_evidence_review(
        "TEST-EVIDENCE-1", decision="REJECT", reviewer_id="reviewer@example.test",
        rationale="Not an applicable regulation.", evidence_path=fixture["evidence"],
        inventory_path=fixture["inventory"], review_log_path=fixture["log"], files_root=fixture["root"],
    )
    effective = reviewed_policy_evidence(
        [fixture["row"]], inventory_path=fixture["inventory"], review_log_path=fixture["log"], files_root=fixture["root"]
    )
    assert effective[0].reviewer_status == "HUMAN_REJECTED"
    assert effective[0].review_rationale == "Not an applicable regulation."
    assert authoritative_reviewed_evidence(
        [fixture["row"]], inventory_path=fixture["inventory"], review_log_path=fixture["log"], files_root=fixture["root"]
    ) == []
    assert fixture["evidence"].read_bytes() == original_bytes


def test_decision_is_final_and_duplicate_review_is_rejected(tmp_path):
    fixture = _fixture(tmp_path)
    kwargs = dict(
        evidence_path=fixture["evidence"], inventory_path=fixture["inventory"],
        review_log_path=fixture["log"], files_root=fixture["root"],
    )
    record_evidence_review(
        "TEST-EVIDENCE-1", decision="APPROVE", reviewer_id="reviewer-1", rationale="Test-only decision.", **kwargs
    )
    with pytest.raises(EvidenceReviewValidationError, match="already has a final decision"):
        record_evidence_review(
            "TEST-EVIDENCE-1", decision="REJECT", reviewer_id="reviewer-2", rationale="Second decision.", **kwargs
        )
    assert len(load_evidence_review_events(fixture["log"])) == 1


def test_review_ledger_detects_tampering(tmp_path):
    fixture = _fixture(tmp_path)
    record_evidence_review(
        "TEST-EVIDENCE-1", decision="APPROVE", reviewer_id="reviewer-1", rationale="Test-only decision.",
        evidence_path=fixture["evidence"], inventory_path=fixture["inventory"],
        review_log_path=fixture["log"], files_root=fixture["root"],
    )
    event = json.loads(fixture["log"].read_text(encoding="utf-8"))
    event["rationale"] = "Edited after the fact."
    fixture["log"].write_text(json.dumps(event) + "\n", encoding="utf-8")
    with pytest.raises(EvidenceReviewValidationError, match="hash mismatch"):
        load_evidence_review_events(fixture["log"])


def test_changed_source_pdf_after_review_fails_closed(tmp_path):
    fixture = _fixture(tmp_path)
    record_evidence_review(
        "TEST-EVIDENCE-1", decision="APPROVE", reviewer_id="reviewer-1", rationale="Test-only decision.",
        evidence_path=fixture["evidence"], inventory_path=fixture["inventory"],
        review_log_path=fixture["log"], files_root=fixture["root"],
    )
    pdf_path = fixture["root"] / "documents" / "TEST-ONLY.pdf"
    pdf_path.write_bytes(pdf_path.read_bytes() + b"tampered")
    with pytest.raises(EvidenceReviewValidationError):
        authoritative_reviewed_evidence(
            [fixture["row"]], inventory_path=fixture["inventory"], review_log_path=fixture["log"], files_root=fixture["root"]
        )


def test_reviewed_candidate_cannot_be_changed_after_review(tmp_path):
    fixture = _fixture(tmp_path)
    record_evidence_review(
        "TEST-EVIDENCE-1", decision="APPROVE", reviewer_id="reviewer-1", rationale="Test-only decision.",
        evidence_path=fixture["evidence"], inventory_path=fixture["inventory"],
        review_log_path=fixture["log"], files_root=fixture["root"],
    )
    altered = dict(fixture["row"], exact_text="Different text after review.")
    with pytest.raises(EvidenceReviewValidationError):
        authoritative_reviewed_evidence(
            [altered], inventory_path=fixture["inventory"], review_log_path=fixture["log"], files_root=fixture["root"]
        )
