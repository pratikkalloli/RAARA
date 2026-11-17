from __future__ import annotations

import json
from pathlib import Path

import pymupdf
import pytest

from evaluation.policy_evidence import (
    PolicyEvidenceValidationError,
    authoritative_policy_evidence,
    validate_policy_evidence,
)
from evaluation.schemas.policy_evidence import PolicyEvidenceRecord


ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "held_out/source_inventory.json"
EVIDENCE = ROOT / "held_out/evidence_candidates.jsonl"


def _records() -> list[dict]:
    return [json.loads(line) for line in EVIDENCE.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_candidate_evidence_matches_original_pdf_hash_page_and_text():
    records = validate_policy_evidence(_records(), INVENTORY)
    assert len(records) == 4
    assert {record.page_number for record in records} == {1, 3, 17}
    assert all(record.reviewer_status == "NOT_REVIEWED" for record in records)


def test_modified_hash_is_rejected():
    records = _records()
    records[0]["source_sha256"] = "0" * 64
    with pytest.raises(PolicyEvidenceValidationError, match="checksum"):
        validate_policy_evidence(records[:1], INVENTORY)


def test_invalid_page_is_rejected():
    records = _records()
    records[0]["page_number"] = 999
    with pytest.raises(PolicyEvidenceValidationError, match="exceeds PDF page count"):
        validate_policy_evidence(records[:1], INVENTORY)


def test_nonverbatim_text_is_rejected():
    records = _records()
    records[0]["exact_text"] = "Attendance shall be 100 percent."
    with pytest.raises(PolicyEvidenceValidationError, match="absent from the declared PDF page"):
        validate_policy_evidence(records[:1], INVENTORY)


def test_duplicate_evidence_id_is_rejected():
    record = _records()[0]
    with pytest.raises(PolicyEvidenceValidationError, match="Duplicate evidence_id"):
        validate_policy_evidence([record, record], INVENTORY)


def test_context_and_pending_sources_never_enter_authoritative_evidence():
    records = validate_policy_evidence(_records(), INVENTORY)
    assert authoritative_policy_evidence(
        records,
        inventory_path=INVENTORY,
        review_log_path=ROOT / "held_out/evidence_reviews.jsonl",
    ) == []


def test_in_memory_status_edit_cannot_create_human_approval():
    records = validate_policy_evidence(_records(), INVENTORY)
    # A caller cannot bypass the append-only review ledger with a model_copy.
    forged = records[0].model_dump(mode="json")
    forged.update({
        "authority_status": "VERIFIED_AUTHORITATIVE",
        "reviewer_status": "HUMAN_APPROVED",
        "supersession_status": "CURRENT",
    })
    with pytest.raises(ValueError, match="final human evidence decision"):
        PolicyEvidenceRecord.model_validate(forged)


def test_missing_applicability_is_invalid():
    raw = _records()[0]
    raw["applicability"] = ""
    with pytest.raises(ValueError):
        PolicyEvidenceRecord.model_validate(raw)


def test_ocr_evidence_without_reviewed_artifact_is_rejected():
    raw = _records()[0]
    raw["extraction_method"] = "ocr"
    with pytest.raises(PolicyEvidenceValidationError, match="OCR-derived evidence"):
        validate_policy_evidence([raw], INVENTORY)


def test_synthetic_pdf_fixture_is_explicitly_nonofficial(tmp_path: Path):
    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_text((50, 50), "SYNTHETIC TEST DOCUMENT — NOT OFFICIAL POLICY")
    path = tmp_path / "synthetic-test-only.pdf"
    pdf.save(path)
    pdf.close()
    with pymupdf.open(path) as opened:
        assert "NOT OFFICIAL POLICY" in opened[0].get_text()
