from __future__ import annotations

import hashlib
import json
from datetime import date
from io import BytesIO
from pathlib import Path

import pymupdf
import pytest
from pydantic import ValidationError

from evaluation.heldout import (
    HeldOutValidationError,
    append_heldout_question,
    import_pdf_document,
    load_registry,
    update_annotation_review,
    validate_heldout_dataset,
)
from evaluation.schemas.held_out import HeldOutDocument, HeldOutQuestion


ROOT = Path(__file__).resolve().parents[2]
DEV_DATA = ROOT / "evaluation/datasets/development/raara_synthetic_starter_v0.1.0.jsonl"


@pytest.fixture
def fixture_pdf_bytes() -> bytes:
    """Synthetic test-only PDF, explicitly not an official regulation."""
    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_text((50, 50), "SYNTHETIC TEST DOCUMENT — NOT OFFICIAL POLICY")
    page.insert_text((50, 90), "Section: Evidence Handling")
    page.insert_text((50, 120), "Synthetic fixture passage used only to test exact evidence validation.")
    buf = BytesIO()
    pdf.save(buf)
    pdf.close()
    return buf.getvalue()


@pytest.fixture
def heldout_files(tmp_path: Path, fixture_pdf_bytes: bytes) -> dict[str, Path]:
    base = tmp_path / "held_out"
    sources = base / "sources"
    sources.mkdir(parents=True)
    pdf_path = sources / "TEST-SOURCE.pdf"
    pdf_path.write_bytes(fixture_pdf_bytes)
    registry_path = base / "documents.json"
    registry_path.write_text(json.dumps({"registry_version": "1.0", "documents": [document_record(fixture_pdf_bytes)]}), encoding="utf-8")
    dataset_path = base / "questions.jsonl"
    dataset_path.write_text("", encoding="utf-8")
    return {"base": base, "pdf": pdf_path, "registry": registry_path, "dataset": dataset_path}


def document_record(pdf_bytes: bytes, **updates) -> dict:
    record = {
        "document_id": "TEST-DOC-V1",
        "document_title": "Synthetic test fixture — not a university policy",
        "original_filename": "SYNTHETIC_TEST_NOT_OFFICIAL.pdf",
        "version": "v1",
        "publication_date": None,
        "effective_date": None,
        "authority_status": "unofficial_reference",
        "authority_review_status": "not_official",
        "authority_reviewer_id": None,
        "authority_reviewed_at": None,
        "relative_path": "sources/TEST-SOURCE.pdf",
        "page_count": 1,
        "sha256": hashlib.sha256(pdf_bytes).hexdigest(),
        "provenance": {
            "acquisition_method": "project_owner_supplied",
            "source_url": None,
            "source_description": "Synthetic test fixture only; not a genuine academic policy source.",
            "retrieved_at": "2026-11-12",
            "permission_record": "Test-created fixture; not used as real policy evidence.",
        },
        "supersedes_document_ids": [],
    }
    record.update(updates)
    return record


def question_record(**updates) -> dict:
    record = {
        "question_id": "HOLDOUT-TEST-001",
        "question": "What text appears in the synthetic fixture section?",
        "category": "direct_factual",
        "expected_status": "SUPPORTED",
        "answerable": True,
        "expected_answer": "The fixture is used only for exact evidence validation.",
        "relevant_document_ids": ["TEST-DOC-V1"],
        "relevant_pages": [{"document_id": "TEST-DOC-V1", "page_number": 1, "section": "Evidence Handling"}],
        "relevant_evidence": [{
            "document_id": "TEST-DOC-V1", "document_version": "v1", "page_number": 1,
            "section": "Evidence Handling", "evidence_id": "TEST-EVIDENCE-1",
            "text": "Synthetic fixture passage used only to test exact evidence validation.",
        }],
        "expected_claims": ["The synthetic fixture supports validation tests only."],
        "annotation_notes": "Synthetic fixture annotation for validator tests only.",
        "annotation_status": "pending",
        "annotator_id": "annotator-test",
        "annotated_at": "2026-11-12",
        "reviewer_id": None,
        "reviewed_at": None,
        "attack_surface": "none",
        "dataset_version": "held_out-1.0",
    }
    record.update(updates)
    return record


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_synthetic_document_provenance_checksum_and_exact_page_evidence_validate(heldout_files):
    row = question_record()
    write_jsonl(heldout_files["dataset"], [row])
    summary = validate_heldout_dataset(heldout_files["dataset"], heldout_files["registry"], DEV_DATA)
    assert summary["valid_questions"] == 1
    assert summary["genuine_documents_imported"] == 1  # a test-only fixture in tmp_path, not a project dataset document
    assert summary["approved_questions"] == 0
    assert not summary["ready_for_phase_8b"]


def test_missing_question_id_is_rejected():
    row = question_record()
    del row["question_id"]
    with pytest.raises(ValidationError, match="question_id"):
        HeldOutQuestion.model_validate(row)


def test_duplicate_question_ids_are_rejected(heldout_files):
    write_jsonl(heldout_files["dataset"], [question_record(), question_record(question="A different question?")])
    with pytest.raises(HeldOutValidationError, match="Duplicate question_id"):
        validate_heldout_dataset(heldout_files["dataset"], heldout_files["registry"], DEV_DATA)


def test_answerable_annotation_requires_expected_answer(heldout_files):
    row = question_record(expected_answer=None)
    with pytest.raises(ValidationError, match="expected_answer"):
        HeldOutQuestion.model_validate(row)


def test_answerable_annotation_requires_exact_evidence(heldout_files):
    row = question_record(relevant_evidence=[])
    with pytest.raises(ValidationError, match="exact evidence"):
        HeldOutQuestion.model_validate(row)


def test_invalid_page_reference_is_rejected(heldout_files):
    row = question_record()
    row["relevant_pages"][0]["page_number"] = 2
    row["relevant_evidence"][0]["page_number"] = 2
    write_jsonl(heldout_files["dataset"], [row])
    with pytest.raises(HeldOutValidationError, match="exceeds.*page count"):
        validate_heldout_dataset(heldout_files["dataset"], heldout_files["registry"], DEV_DATA)


def test_missing_document_provenance_is_rejected(heldout_files):
    registry = json.loads(heldout_files["registry"].read_text(encoding="utf-8"))
    del registry["documents"][0]["provenance"]
    heldout_files["registry"].write_text(json.dumps(registry), encoding="utf-8")
    with pytest.raises(HeldOutValidationError, match="provenance"):
        load_registry(heldout_files["registry"])


def test_source_checksum_mismatch_is_rejected(heldout_files):
    registry = json.loads(heldout_files["registry"].read_text(encoding="utf-8"))
    registry["documents"][0]["sha256"] = "0" * 64
    heldout_files["registry"].write_text(json.dumps(registry), encoding="utf-8")
    with pytest.raises(HeldOutValidationError, match="SHA-256 mismatch"):
        load_registry(heldout_files["registry"])


def test_malformed_checksum_is_rejected_by_schema():
    record = document_record(b"pdf")
    record["sha256"] = "not-a-checksum"
    with pytest.raises(ValidationError, match="sha256"):
        HeldOutDocument.model_validate(record)


def test_duplicate_evidence_mapping_within_question_is_rejected():
    row = question_record(category="multi_passage")
    duplicate = dict(row["relevant_evidence"][0], evidence_id="TEST-EVIDENCE-2")
    row["relevant_evidence"].append(duplicate)
    with pytest.raises(ValidationError, match="Duplicate evidence mapping"):
        HeldOutQuestion.model_validate(row)


def test_unsupported_document_version_is_rejected(heldout_files):
    row = question_record()
    row["relevant_evidence"][0]["document_version"] = "v9"
    write_jsonl(heldout_files["dataset"], [row])
    with pytest.raises(HeldOutValidationError, match="unsupported document version"):
        validate_heldout_dataset(heldout_files["dataset"], heldout_files["registry"], DEV_DATA)


def test_exact_development_question_overlap_is_rejected(heldout_files):
    from evaluation.schemas.dataset import load_dataset

    row = question_record(question=load_dataset(DEV_DATA)[0].question)
    write_jsonl(heldout_files["dataset"], [row])
    with pytest.raises(HeldOutValidationError, match="overlap detected"):
        validate_heldout_dataset(heldout_files["dataset"], heldout_files["registry"], DEV_DATA)


def test_unanswerable_annotation_cannot_include_answer_or_evidence():
    row = question_record(expected_status="NOT_FOUND", answerable=False, expected_answer=None,
                         relevant_document_ids=[], relevant_pages=[], relevant_evidence=[], expected_claims=[])
    assert HeldOutQuestion.model_validate(row).answerable is False
    row["relevant_evidence"] = question_record()["relevant_evidence"]
    with pytest.raises(ValidationError, match="Unanswerable questions"):
        HeldOutQuestion.model_validate(row)


def test_approved_annotation_requires_complete_independent_review():
    row = question_record(annotation_status="approved", reviewer_id=None, reviewed_at=None)
    with pytest.raises(ValidationError, match="independent reviewer"):
        HeldOutQuestion.model_validate(row)
    row["reviewer_id"] = row["annotator_id"]
    row["reviewed_at"] = "2026-11-12"
    with pytest.raises(ValidationError, match="independent"):
        HeldOutQuestion.model_validate(row)


def test_approved_annotation_with_unofficial_source_is_rejected(heldout_files):
    row = question_record(annotation_status="approved", reviewer_id="independent-reviewer", reviewed_at="2026-11-12")
    write_jsonl(heldout_files["dataset"], [row])
    with pytest.raises(HeldOutValidationError, match="official sources"):
        validate_heldout_dataset(heldout_files["dataset"], heldout_files["registry"], DEV_DATA)


def test_interactive_workflow_append_then_independent_review(heldout_files):
    question = HeldOutQuestion.model_validate(question_record())
    result = append_heldout_question(question, heldout_files["dataset"], heldout_files["registry"], DEV_DATA)
    assert result["valid_questions"] == 1
    result = update_annotation_review("HOLDOUT-TEST-001", "reviewed", "reviewer-test", heldout_files["dataset"],
                                     heldout_files["registry"], DEV_DATA, "2026-11-12")
    assert result["approved_questions"] == 0
    saved = json.loads(heldout_files["dataset"].read_text(encoding="utf-8").strip())
    assert saved["annotation_status"] == "reviewed"
    assert saved["reviewer_id"] == "reviewer-test"


@pytest.mark.parametrize("status", ["REJECTED", "NEEDS_CORRECTION"])
def test_review_workflow_records_non_approval_outcomes(heldout_files, status):
    write_jsonl(heldout_files["dataset"], [question_record()])
    result = update_annotation_review("HOLDOUT-TEST-001", status, "reviewer-test", heldout_files["dataset"],
                                      heldout_files["registry"], DEV_DATA, "2026-11-12")
    saved = json.loads(heldout_files["dataset"].read_text(encoding="utf-8").strip())
    assert saved["annotation_status"] == status
    assert result["approved_questions"] == 0
    assert result["incomplete_annotations"] == 1


def test_pending_review_status_is_supported():
    question = HeldOutQuestion.model_validate(question_record(annotation_status="PENDING_REVIEW"))
    assert question.annotation_status == "PENDING_REVIEW"


def test_grading_academic_performance_category_is_supported():
    question = HeldOutQuestion.model_validate(question_record(category="grading_academic_performance"))
    assert question.category == "grading_academic_performance"


def test_readiness_includes_source_acquisition_counts(heldout_files, tmp_path):
    write_jsonl(heldout_files["dataset"], [])
    inventory = tmp_path / "source_inventory.json"
    inventory.write_text(json.dumps({
        "sources": [
            {"classification": "OFFICIAL_VERIFIED"},
            {"classification": "OFFICIAL_UNVERIFIED"},
            {"classification": "WRONG_INSTITUTION"},
            {"classification": "THIRD_PARTY_REFERENCE"},
        ],
        "acquisition_summary": {
            "downloaded_pdfs": 1, "official_verified_downloaded_pdfs": 1,
            "successfully_opened_pdfs": 1, "successfully_text_extracted_pdfs": 0,
            "documents_with_extraction_warnings": 1, "proposed_questions": 0,
            "completed_annotations": 0, "approved_annotations": 0,
            "rejected_annotations": 0, "pending_annotations": 0,
        },
    }), encoding="utf-8")
    summary = validate_heldout_dataset(heldout_files["dataset"], heldout_files["registry"], DEV_DATA, inventory)
    assert summary["total_discovered_sources"] == 4
    assert summary["official_verified_sources"] == 1
    assert summary["official_unverified_sources"] == 1
    assert summary["wrong_institution_sources"] == 1
    assert summary["third_party_reference_sources"] == 1
    assert summary["rejected_sources"] == 2
    assert summary["downloaded_pdfs"] == 1
    assert summary["documents_with_extraction_warnings"] == 1
    assert summary["dataset_readiness"] == "INCOMPLETE"
    assert not summary["ready_for_phase_8b"]


def test_pdf_import_preserves_original_bytes_and_rejects_duplicate(tmp_path, fixture_pdf_bytes):
    base = tmp_path / "held_out"
    base.mkdir()
    registry_path = base / "documents.json"
    registry_path.write_text('{"registry_version":"1.0","documents":[]}', encoding="utf-8")
    source_path = tmp_path / "SYNTHETIC_TEST_NOT_OFFICIAL.pdf"
    source_path.write_bytes(fixture_pdf_bytes)
    record = import_pdf_document(source_path, registry_path, document_id="FIXTURE-1", document_title="Synthetic fixture",
                                 version="fixture-v1", authority_status="unofficial_reference", provenance={
                                     "acquisition_method": "project_owner_supplied", "source_url": None,
                                     "source_description": "Synthetic test fixture only; not a university regulation.",
                                     "retrieved_at": "2026-11-12", "permission_record": "Test fixture only; no policy use."})
    imported = base / record["relative_path"]
    assert imported.read_bytes() == source_path.read_bytes() == fixture_pdf_bytes
    assert record["sha256"] == hashlib.sha256(fixture_pdf_bytes).hexdigest()
    with pytest.raises(HeldOutValidationError, match="duplicate document bytes"):
        import_pdf_document(source_path, registry_path, document_id="FIXTURE-2", document_title="Duplicate fixture",
                            version="fixture-v1", authority_status="unofficial_reference", provenance={
                                "acquisition_method": "project_owner_supplied", "source_url": None,
                                "source_description": "Synthetic test fixture only; not a university regulation.",
                                "retrieved_at": "2026-11-12", "permission_record": "Test fixture only; no policy use."})


def test_registry_rejects_path_escape(heldout_files):
    registry = json.loads(heldout_files["registry"].read_text(encoding="utf-8"))
    registry["documents"][0]["relative_path"] = "../../outside.pdf"
    heldout_files["registry"].write_text(json.dumps(registry), encoding="utf-8")
    with pytest.raises(HeldOutValidationError, match="escapes"):
        load_registry(heldout_files["registry"])
