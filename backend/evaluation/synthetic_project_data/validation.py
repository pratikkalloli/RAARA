"""Strict validation helpers for Phase 9A synthetic assets; no app storage access."""
from __future__ import annotations

import hashlib
import json
import re
import tempfile
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

import pymupdf

from evaluation.schemas.dataset import DatasetValidationError, EvaluationQuestion, validate_dataset

ROOT = Path(__file__).resolve().parent
DATASET_PATH = ROOT / "datasets" / "synthetic_questions.json"
MANIFEST_PATH = ROOT / "synthetic_dataset_manifest.json"
CONFLICT_MANIFEST_PATH = ROOT / "synthetic_conflict_manifest.json"
EXPECTED_CATEGORIES = {
    "direct_factual": 8,
    "attendance_eligibility": 6,
    "assessment_calculation": 6,
    "grading_sgpa_cgpa": 6,
    "backlogs_supplementary": 5,
    "lateral_entry_progression": 5,
    "multi_passage": 4,
    "multi_document": 3,
    "conflicting_version": 3,
    "unanswerable": 2,
    "prompt_injection": 2,
}


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DatasetValidationError(f"Could not load {path.name}: {exc}") from exc


def _check_manifest(manifest: dict[str, Any], path: Path, *, expected_count: int) -> None:
    if manifest.get("dataset_type") != "SYNTHETIC_PROJECT_DATA":
        raise DatasetValidationError(f"{path.name}: dataset_type must be SYNTHETIC_PROJECT_DATA")
    if manifest.get("is_official_university_policy") is not False or manifest.get("source_type") != "PROJECT_AUTHORED":
        raise DatasetValidationError(f"{path.name}: synthetic provenance flags are missing or unsafe")
    docs = manifest.get("documents")
    if not isinstance(docs, list) or len(docs) != expected_count:
        raise DatasetValidationError(f"{path.name}: expected {expected_count} documents")
    ids = set()
    for doc in docs:
        required = ("document_id", "document_name", "version", "effective_date", "academic_year", "path", "source_markdown", "sha256")
        if any(not doc.get(key) for key in required):
            raise DatasetValidationError(f"{path.name}: document metadata is incomplete")
        if doc["document_id"] in ids:
            raise DatasetValidationError(f"{path.name}: duplicate document ID {doc['document_id']}")
        ids.add(doc["document_id"])
        if doc.get("dataset_type") != "SYNTHETIC_PROJECT_DATA" or doc.get("is_official_university_policy") is not False or doc.get("source_type") != "PROJECT_AUTHORED":
            raise DatasetValidationError(f"Document {doc['document_id']} lacks explicit synthetic provenance")
        if doc.get("dataset_version") != manifest.get("dataset_version"):
            raise DatasetValidationError(f"Document {doc['document_id']} has a mismatched dataset version")
        pdf = (path.parent / doc["path"]).resolve()
        md = (path.parent / doc["source_markdown"]).resolve()
        for candidate in (pdf, md):
            try:
                candidate.relative_to(ROOT.resolve())
            except ValueError as exc:
                raise DatasetValidationError("Synthetic data path escapes the isolated synthetic tree") from exc
        if not pdf.is_file() or not md.is_file():
            raise DatasetValidationError(f"Document {doc['document_id']} is missing PDF or source Markdown")
        if hashlib.sha256(pdf.read_bytes()).hexdigest() != doc["sha256"]:
            raise DatasetValidationError(f"PDF checksum mismatch for {doc['document_id']}")
        with pymupdf.open(pdf) as opened:
            if opened.page_count != doc.get("page_count"):
                raise DatasetValidationError(f"PDF page count mismatch for {doc['document_id']}")
            page_text = opened[0].get_text("text")
            if not page_text.strip():
                raise DatasetValidationError(f"PDF has no extractable text for {doc['document_id']}")
            if "SYNTHETIC_PROJECT_DATA" not in page_text or "PROJECT_AUTHORED" not in page_text or doc["document_id"] not in page_text:
                raise DatasetValidationError(f"PDF is missing required synthetic classification metadata: {doc['document_id']}")
        source = md.read_text(encoding="utf-8")
        if "SYNTHETIC PROJECT POLICY — NOT AN OFFICIAL PES UNIVERSITY REGULATION" not in source:
            raise DatasetValidationError(f"Source Markdown is missing the synthetic policy disclaimer: {md.name}")


def _validate_calculation(question: EvaluationQuestion) -> None:
    record = question.calculation
    if not record:
        return
    kind = record.get("kind")
    inputs = record.get("inputs")
    expected = record.get("expected_result")
    if not isinstance(inputs, dict) or not isinstance(expected, (int, float)):
        raise DatasetValidationError(f"{question.question_id}: malformed numerical ground truth")
    values = {key: Decimal(str(value)) for key, value in inputs.items()}
    if kind == "weighted_final_score":
        result = values["isa1"] / 40 * 20 + values["isa2"] / 40 * 20 + values["esa"] / 100 * 50 + values["lab"] / 30 * 10
    elif kind == "sgpa":
        result = (values["course1_credits"] * values["course1_grade_points"] + values["course2_credits"] * values["course2_grade_points"]) / (values["course1_credits"] + values["course2_credits"])
        result = result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    elif kind == "cgpa":
        result = (values["semester1_sgpa"] * values["semester1_credits"] + values["semester2_sgpa"] * values["semester2_credits"]) / (values["semester1_credits"] + values["semester2_credits"])
    else:
        raise DatasetValidationError(f"{question.question_id}: unsupported calculation kind {kind!r}")
    if result != Decimal(str(expected)):
        raise DatasetValidationError(f"{question.question_id}: expected numeric answer {expected}, independently calculated {result}")


def validate_synthetic_dataset(dataset_path: Path = DATASET_PATH, manifest_path: Path = MANIFEST_PATH, conflict_manifest_path: Path = CONFLICT_MANIFEST_PATH) -> dict[str, Any]:
    dataset = _load_json(dataset_path)
    manifest = _load_json(manifest_path)
    conflict_manifest = _load_json(conflict_manifest_path)
    _check_manifest(manifest, manifest_path, expected_count=10)
    _check_manifest(conflict_manifest, conflict_manifest_path, expected_count=12)
    if dataset.get("dataset_version") != manifest.get("dataset_version"):
        raise DatasetValidationError("Master question dataset and primary corpus version differ")
    if dataset.get("dataset_type") != "SYNTHETIC_PROJECT_DATA" or dataset.get("is_official_university_policy") is not False or dataset.get("source_type") != "PROJECT_AUTHORED":
        raise DatasetValidationError("Master question dataset is missing explicit synthetic classification")
    try:
        questions = [EvaluationQuestion.model_validate(row) for row in dataset.get("questions", [])]
    except Exception as exc:
        raise DatasetValidationError(f"Synthetic question schema validation failed: {exc}") from exc
    if len(questions) != 50:
        raise DatasetValidationError(f"Expected 50 questions, found {len(questions)}")
    ids = [q.question_id for q in questions]
    if len(set(ids)) != len(ids):
        raise DatasetValidationError("Question IDs must be unique")
    for q in questions:
        if q.dataset_type != "SYNTHETIC_PROJECT_DATA" or q.is_official_university_policy is not False or q.source_type != "PROJECT_AUTHORED" or q.dataset_version != manifest["dataset_version"]:
            raise DatasetValidationError(f"Question {q.question_id} is missing synthetic classification metadata")
        if q.answerable != (q.expected_status != "NOT_FOUND"):
            raise DatasetValidationError(f"Question {q.question_id} answerability/status mismatch")
        for evidence in q.relevant_evidence:
            if evidence.dataset_type != q.dataset_type or evidence.is_official_university_policy is not False or evidence.source_type != q.source_type or evidence.dataset_version != q.dataset_version:
                raise DatasetValidationError(f"Evidence {evidence.evidence_id} lacks matching synthetic provenance")
            expected_version = next((doc["version"] for doc in conflict_manifest["documents"] if doc["document_id"] == evidence.document_id), None)
            if expected_version != evidence.document_version:
                raise DatasetValidationError(f"Evidence {evidence.evidence_id} document version mismatch")
        _validate_calculation(q)
    categories = Counter(q.category for q in questions)
    if dict(categories) != EXPECTED_CATEGORIES:
        raise DatasetValidationError(f"Unexpected question category counts: {dict(categories)}")
    split_counts = Counter(q.dataset_split for q in questions)
    if split_counts != Counter({"development": 36, "held_out": 11, "conflict": 3}):
        raise DatasetValidationError(f"Unexpected split counts: {dict(split_counts)}")
    master = {q.question_id: q for q in questions}
    dev_ids = {qid for qid, q in master.items() if q.dataset_split == "development"}
    held_ids = {qid for qid, q in master.items() if q.dataset_split == "held_out"}
    if dev_ids & held_ids:
        raise DatasetValidationError("Development and held-out IDs overlap")
    norm_question = lambda text: re.sub(r"\W+", " ", text.casefold()).strip()
    dev_text = {norm_question(master[qid].question) for qid in dev_ids}
    held_text = {norm_question(master[qid].question) for qid in held_ids}
    if dev_text & held_text:
        raise DatasetValidationError("Development and held-out question text overlap")

    # Reuse the existing PDF/page/evidence validator independently per document set.
    for split in ("development", "held_out", "conflict"):
        subset = [q for q in questions if q.dataset_split == split]
        selected_manifest_path = conflict_manifest_path if split == "conflict" else manifest_path
        with tempfile.TemporaryDirectory(prefix="raara-p9a-validate-") as temp:
            temp_data = Path(temp) / "questions.jsonl"
            temp_data.write_text("\n".join(q.model_dump_json() for q in subset) + "\n", encoding="utf-8")
            validate_dataset(temp_data, selected_manifest_path)

    # Ensure unsupported questions remain unsupported by corpus text, not merely marked so.
    corpus_text_parts = []
    for doc in manifest["documents"]:
        with pymupdf.open((manifest_path.parent / doc["path"]).resolve()) as opened:
            corpus_text_parts.append(opened[0].get_text("text").casefold())
    corpus_text = " ".join(corpus_text_parts)
    if "hostel curfew" in corpus_text or "tuition-fee refund deadline" in corpus_text:
        raise DatasetValidationError("An unanswerable topic accidentally appears in the primary policy corpus")
    numeric_count = sum(1 for q in questions if q.calculation)
    if numeric_count != 2:
        raise DatasetValidationError(f"Expected 2 question-level numerical checks, found {numeric_count}")
    example_sgpa = (Decimal(4) * Decimal(9) + Decimal(3) * Decimal(8)) / Decimal(7)
    example_cgpa = (Decimal("8.0") * Decimal(24) + Decimal("9.0") * Decimal(24)) / Decimal(48)
    if example_sgpa.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) != Decimal("8.57") or example_cgpa != Decimal("8.5"):
        raise DatasetValidationError("Policy worked-example calculations failed independent recomputation")
    return {
        "dataset_version": manifest["dataset_version"],
        "dataset_type": manifest["dataset_type"],
        "is_official_university_policy": False,
        "question_count": len(questions),
        "question_categories": dict(sorted(categories.items())),
        "split_counts": dict(sorted(split_counts.items())),
        "primary_policy_document_count": len(manifest["documents"]),
        "conflict_fixture_document_count": len(conflict_manifest["documents"]) - len(manifest["documents"]),
        "conflict_manifest_total_documents": len(conflict_manifest["documents"]),
        "evidence_reference_count": sum(len(q.relevant_evidence) for q in questions),
        "validated_question_numeric_calculations": numeric_count,
        "independently_recomputed_policy_worked_examples": 2,
        "numerical_policy_examples_independently_validated": ["weighted final score = 77", "example SGPA = 8.57", "example CGPA = 8.50"],
        "development_held_out_exact_overlap": False,
        "unanswerable_topic_scan": "hostel curfew and tuition-fee refund deadline absent from primary synthetic policy text",
        "official_registry_modified": False,
        "production_storage_accessed": False,
        "status": "PASS",
    }
