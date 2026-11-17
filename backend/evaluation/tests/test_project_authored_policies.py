from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from evaluation.policy_evidence import authoritative_policy_evidence
from evaluation.project_authored_policies import (
    OFFICIAL_POLICY_ABSTENTION,
    PROJECT_ASSUMPTION_PREFIX,
    ProjectPolicyDatasetError,
    abstain_on_official_policy_question,
    format_project_policy_context,
    load_project_policy_dataset,
)
from evaluation.policy_evidence_review import EvidenceReviewValidationError
from evaluation.schemas.held_out import HeldOutDocumentRegistry
from evaluation.schemas.project_policy import ProjectPolicyRecord


BACKEND = Path(__file__).resolve().parents[2]
DATASET_PATH = BACKEND / "evaluation/datasets/project_authored_academic_policy/generic_academic_policy_dataset.json"
INVENTORY = BACKEND / "evaluation/held_out/source_inventory.json"
REVIEW_LOG = BACKEND / "evaluation/held_out/evidence_reviews.jsonl"


def _raw() -> dict:
    return json.loads(DATASET_PATH.read_text(encoding="utf-8"))


def _phase9a_fingerprint() -> str:
    root = BACKEND / "evaluation/synthetic_project_data"
    digest = hashlib.sha256()
    files = sorted(p for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc")
    for path in files:
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def test_dataset_has_unique_ids_and_only_project_nonofficial_provenance():
    dataset = load_project_policy_dataset(DATASET_PATH)
    assert len(dataset.policies) == 28
    assert len(dataset.questions) == 30
    assert len({p.policy_id for p in dataset.policies}) == len(dataset.policies)
    assert len({p.evidence_id for p in dataset.policies}) == len(dataset.policies)
    assert len({q.question_id for q in dataset.questions}) == len(dataset.questions)
    assert all(p.provenance == "PROJECT_AUTHORED" for p in dataset.policies)
    assert all(p.source_type == "GENERIC_PROJECT_POLICY" for p in dataset.policies)
    assert all(p.is_official_university_policy is False for p in dataset.policies)
    assert all(p.authority_status == "NOT_OFFICIAL" for p in dataset.policies)
    assert all(p.applicability == "RAARA project demonstration only; not institution- or batch-specific." for p in dataset.policies)


def test_dataset_covers_all_requested_categories_and_demo_question_types():
    dataset = load_project_policy_dataset(DATASET_PATH)
    expected = {
        "attendance", "assessment", "passing", "grading", "sgpa", "cgpa", "backlogs",
        "revaluation", "course_registration", "credits", "academic_progression", "academic_calendar",
    }
    assert expected.issubset({p.category for p in dataset.policies})
    assert {"direct_factual", "numerical_calculation", "multi_policy", "unanswerable", "clarification", "conflicting_policy"}.issubset({q.category for q in dataset.questions})
    assert any(q.expected_status == "CONFLICTING_SOURCES" for q in dataset.questions)


def test_numeric_defaults_and_all_worked_examples_recompute():
    dataset = load_project_policy_dataset(DATASET_PATH)
    by_id = {p.policy_id: p for p in dataset.policies}
    assert by_id["GAP-ATT-001"].calculation_details["minimum_attendance_percent"] == 75
    assert by_id["GAP-ASSESS-001"].calculation_details == {"internal_weight_percent": 40, "end_semester_weight_percent": 60}
    assert by_id["GAP-PASS-001"].calculation_details["overall_passing_score"] == 40
    assert by_id["GAP-PASS-001"].calculation_details["separate_exam_minimum_defined"] is False
    attendance = by_id["GAP-ATT-002"].calculation_details["example"]
    assert attendance["attended"] / attendance["held"] * 100 == attendance["expected_percentage"] == 80
    assert by_id["GAP-SGPA-002"].calculation_details["worked_example"]["expected_sgpa"] == 8.1
    assert by_id["GAP-CGPA-002"].calculation_details["worked_example"]["expected_cgpa"] == 7.7


def test_validator_rejects_incorrect_attendance_math(tmp_path: Path):
    raw = _raw()
    raw["policies"][1]["calculation_details"]["example"]["expected_percentage"] = 81
    path = tmp_path / "bad-dataset.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ProjectPolicyDatasetError, match="attendance example does not recompute"):
        load_project_policy_dataset(path)


def test_unanswerable_and_clarification_entries_have_no_fabricated_evidence():
    dataset = load_project_policy_dataset(DATASET_PATH)
    assert all(not q.expected_answer and not q.relevant_evidence_ids for q in dataset.questions if q.expected_status in {"NOT_FOUND", "NEEDS_CLARIFICATION"})
    by_id = {q.question_id: q for q in dataset.questions}
    for number in (16, 26, 27, 28):
        assert by_id[f"GAP-Q-{number:03d}"].expected_status == "NOT_FOUND"
    assert by_id["GAP-Q-026"].expected_answer is None
    assert by_id["GAP-Q-027"].expected_answer is None


def test_official_policy_queries_abstain_instead_of_using_generic_thresholds():
    dataset = load_project_policy_dataset(DATASET_PATH)
    for question in ("What is the official PES University attendance requirement?", "What is the PES attendance rule?", "Does this apply to 2025 AIML batch?"):
        assert abstain_on_official_policy_question(question) == OFFICIAL_POLICY_ABSTENTION
    assert abstain_on_official_policy_question("What is the project illustrative attendance value?") is None
    assert dataset.questions[25].expected_status == "NOT_FOUND"
    assert "official" in OFFICIAL_POLICY_ABSTENTION.casefold()


def test_generic_context_is_always_labeled_as_project_authored():
    policy = load_project_policy_dataset(DATASET_PATH).policies[0]
    context = format_project_policy_context(policy)
    assert context.startswith(PROJECT_ASSUMPTION_PREFIX)
    assert "NOT OFFICIAL UNIVERSITY POLICY" in context
    raw = policy.model_dump(mode="json")
    raw["is_official_university_policy"] = True
    with pytest.raises(ProjectPolicyDatasetError, match="Refusing unlabeled policy context"):
        format_project_policy_context(raw)


def test_generic_policy_cannot_pass_official_authority_gate():
    raw_policy = _raw()["policies"][0]
    with pytest.raises(EvidenceReviewValidationError, match="Evidence provenance/page validation failed"):
        authoritative_policy_evidence(
            [raw_policy], inventory_path=INVENTORY, review_log_path=REVIEW_LOG,
        )


def test_generic_policy_cannot_enter_official_heldout_registry():
    raw_policy = _raw()["policies"][0]
    with pytest.raises(ValidationError):
        HeldOutDocumentRegistry.model_validate({"registry_version": "1.0", "documents": [raw_policy]})
    registry = json.loads((BACKEND / "evaluation/datasets/held_out/documents.json").read_text(encoding="utf-8"))
    assert registry["documents"] == []


def test_phase9a_assets_remain_byte_for_byte_unchanged():
    assert _phase9a_fingerprint() == "e60703d320a2339b2fc1181a0ca1ce55e980744ce6fe87358eac9c6cecaab4fd"


def test_dataset_is_separate_from_heldout_and_phase9a_paths():
    generic = DATASET_PATH.resolve()
    held_out = (BACKEND / "evaluation/datasets/held_out").resolve()
    phase9a = (BACKEND / "evaluation/synthetic_project_data").resolve()
    assert held_out not in generic.parents
    assert phase9a not in generic.parents
    assert generic.parent.name == "project_authored_academic_policy"


def test_schema_does_not_allow_official_authority_or_unknown_provenance():
    raw = _raw()["policies"][0]
    raw["authority_status"] = "VERIFIED_AUTHORITATIVE"
    with pytest.raises(ValidationError):
        ProjectPolicyRecord.model_validate(raw)
    raw = _raw()["policies"][0]
    raw["provenance"] = "PES_OFFICIAL"
    with pytest.raises(ValidationError):
        ProjectPolicyRecord.model_validate(raw)
