from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest
from pydantic import ValidationError

from evaluation.schemas.dataset import DatasetValidationError, EvaluationQuestion, load_dataset, validate_dataset

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "datasets" / "development" / "raara_synthetic_starter_v0.1.0.jsonl"
MANIFEST = ROOT / "datasets" / "development" / "manifest.json"


def test_versioned_starter_dataset_and_source_evidence_validate() -> None:
    result = validate_dataset(DATASET, MANIFEST)
    assert result.dataset_version == "0.1.0"
    assert len(result.questions) == 12
    assert Counter(question.category for question in result.questions) == {
        "direct_factual": 3,
        "multi_passage": 2,
        "multi_document": 1,
        "unanswerable": 2,
        "conflicting_version": 2,
        "prompt_injection": 2,
    }


def test_dataset_loader_rejects_malformed_jsonl_with_line_number(tmp_path: Path) -> None:
    path = tmp_path / "bad.jsonl"
    path.write_text('{"question_id":\n', encoding="utf-8")
    with pytest.raises(DatasetValidationError, match=r"bad\.jsonl:1"):
        load_dataset(path)


def test_empty_dataset_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "empty.jsonl"
    path.write_text("\n", encoding="utf-8")
    with pytest.raises(DatasetValidationError, match="contains no question records"):
        load_dataset(path)


def test_duplicate_question_ids_are_rejected(tmp_path: Path) -> None:
    first = load_dataset(DATASET)[0].model_dump_json()
    path = tmp_path / "duplicates.jsonl"
    path.write_text(first + "\n" + first + "\n", encoding="utf-8")
    with pytest.raises(DatasetValidationError, match="Duplicate question_id"):
        validate_dataset(path, MANIFEST)


def test_dataset_version_must_match_manifest(tmp_path: Path) -> None:
    row = load_dataset(DATASET)[0].model_dump()
    row["dataset_version"] = "9.9.9"
    path = tmp_path / "version.jsonl"
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(DatasetValidationError, match="Dataset version mismatch"):
        validate_dataset(path, MANIFEST)


def test_out_of_range_page_reference_is_rejected(tmp_path: Path) -> None:
    row = load_dataset(DATASET)[0].model_dump()
    row["relevant_pages"][0]["page_number"] = 99
    row["relevant_evidence"][0]["page_number"] = 99
    path = tmp_path / "bad-page.jsonl"
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(DatasetValidationError, match="exceeds.*page_count"):
        validate_dataset(path, MANIFEST)


def test_evidence_text_must_exist_on_declared_pdf_page(tmp_path: Path) -> None:
    row = load_dataset(DATASET)[0].model_dump()
    row["relevant_evidence"][0]["text"] = "A fabricated rule not printed in the source PDF."
    path = tmp_path / "fabricated-evidence.jsonl"
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(DatasetValidationError, match="not present on declared PDF page"):
        validate_dataset(path, MANIFEST)


def test_unanswerable_questions_cannot_contain_reference_answers() -> None:
    row = load_dataset(DATASET)[6].model_dump()
    row["reference_answer"] = "A fabricated hostel curfew is 10 p.m."
    with pytest.raises(ValidationError, match="fabricated reference_answer"):
        EvaluationQuestion.model_validate(row)


def test_supported_question_requires_reference_answer_and_evidence() -> None:
    row = load_dataset(DATASET)[0].model_dump()
    row["reference_answer"] = None
    with pytest.raises(ValidationError, match="require a reference_answer"):
        EvaluationQuestion.model_validate(row)


def test_blank_question_and_unknown_category_are_rejected() -> None:
    row = load_dataset(DATASET)[0].model_dump()
    row["question"] = " \t "
    with pytest.raises(ValidationError, match="Question must not be blank"):
        EvaluationQuestion.model_validate(row)
    row["question"] = "A nonempty question"
    row["category"] = "invented_category"
    with pytest.raises(ValidationError, match="category"):
        EvaluationQuestion.model_validate(row)


def test_duplicate_evidence_labels_are_rejected() -> None:
    row = load_dataset(DATASET)[3].model_dump()
    row["relevant_evidence"][1]["evidence_id"] = row["relevant_evidence"][0]["evidence_id"]
    with pytest.raises(ValidationError, match="evidence_id values must not contain duplicates"):
        EvaluationQuestion.model_validate(row)


def test_unknown_document_reference_is_rejected(tmp_path: Path) -> None:
    row = load_dataset(DATASET)[0].model_dump()
    row["relevant_document_ids"] = ["UNKNOWN-DOC"]
    row["relevant_pages"][0]["document_id"] = "UNKNOWN-DOC"
    row["relevant_evidence"][0]["document_id"] = "UNKNOWN-DOC"
    path = tmp_path / "unknown-document.jsonl"
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(DatasetValidationError, match="unknown relevant document_id"):
        validate_dataset(path, MANIFEST)
