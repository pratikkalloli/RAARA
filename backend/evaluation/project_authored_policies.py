"""Offline validation and display safeguards for generic project-only policies."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from evaluation.schemas.project_policy import ProjectPolicyDataset, ProjectPolicyRecord


class ProjectPolicyDatasetError(ValueError):
    pass


def load_project_policy_dataset(path: str | Path) -> ProjectPolicyDataset:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        dataset = ProjectPolicyDataset.model_validate(raw)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        raise ProjectPolicyDatasetError(f"Invalid project-authored policy dataset: {exc}") from exc
    validate_numerical_examples(dataset)
    return dataset


def validate_numerical_examples(dataset: ProjectPolicyDataset) -> None:
    """Recompute the explicitly published examples instead of trusting labels."""
    try:
        attendance_policy = next(
            p for p in dataset.policies
            if p.category == "attendance" and p.calculation_details
            and p.calculation_details.get("example", {}).get("expected_percentage") is not None
        )
        attendance = attendance_policy.calculation_details["example"]
        calculated_attendance = attendance["attended"] / attendance["held"] * 100
        if round(calculated_attendance, 2) != attendance["expected_percentage"]:
            raise ValueError("attendance example does not recompute")

        assessment_policy = next(p for p in dataset.policies if p.category == "assessment" and p.calculation_details and "worked_example" in p.calculation_details)
        assessment = assessment_policy.calculation_details["worked_example"]
        calculated_score = assessment["internal_score"] * 0.40 + assessment["end_semester_score"] * 0.60
        if round(calculated_score, 2) != assessment["expected_total"]:
            raise ValueError("assessment example does not recompute")

        sgpa_policy = next(p for p in dataset.policies if p.category == "sgpa" and p.calculation_details and "worked_example" in p.calculation_details)
        sgpa = sgpa_policy.calculation_details["worked_example"]
        numerator = sum(item["credits"] * item["grade_point"] for item in sgpa["courses"])
        denominator = sum(item["credits"] for item in sgpa["courses"])
        if round(numerator / denominator, 2) != sgpa["expected_sgpa"]:
            raise ValueError("SGPA example does not recompute")

        cgpa_policy = next(p for p in dataset.policies if p.category == "cgpa" and p.calculation_details and "worked_example" in p.calculation_details)
        cgpa = cgpa_policy.calculation_details["worked_example"]
        numerator = sum(item["credits"] * item["grade_point"] for item in cgpa["terms"])
        denominator = sum(item["credits"] for item in cgpa["terms"])
        if round(numerator / denominator, 2) != cgpa["expected_cgpa"]:
            raise ValueError("CGPA example does not recompute")

        grading_policy = next(p for p in dataset.policies if p.category == "grading" and p.calculation_details and "grade_bands" in p.calculation_details)
        grading = grading_policy.calculation_details["grade_bands"]
        if not grading or any(row["minimum"] > row["maximum"] for row in grading):
            raise ValueError("grade bands are invalid")
        ordered = sorted(grading, key=lambda row: row["minimum"])
        if ordered[0]["minimum"] != 0 or ordered[-1]["maximum"] != 100:
            raise ValueError("grade bands must cover the illustrative 0-100 score range")
        for lower, upper in zip(ordered, ordered[1:]):
            if lower["maximum"] + 1 != upper["minimum"]:
                raise ValueError("grade bands must be contiguous without overlap")

        for question in dataset.questions:
            example = question.calculation
            if not example:
                continue
            if {"attended", "held", "expected_percentage"}.issubset(example):
                value = example["attended"] / example["held"] * 100
                if round(value, 2) != example["expected_percentage"]:
                    raise ValueError(f"{question.question_id}: attendance calculation does not recompute")
            if {"attended", "held", "threshold", "shortfall_percentage_points"}.issubset(example):
                value = example["threshold"] - example["attended"] / example["held"] * 100
                if round(value, 2) != example["shortfall_percentage_points"]:
                    raise ValueError(f"{question.question_id}: attendance shortfall does not recompute")
            if {"internal", "end_semester", "expected_total"}.issubset(example):
                value = example["internal"] * 0.40 + example["end_semester"] * 0.60
                if round(value, 2) != example["expected_total"]:
                    raise ValueError(f"{question.question_id}: weighted score does not recompute")
            if {"courses", "expected_sgpa"}.issubset(example):
                credits = sum(item["credits"] for item in example["courses"])
                points = sum(item["credits"] * item["grade_point"] for item in example["courses"])
                if round(points / credits, 2) != example["expected_sgpa"]:
                    raise ValueError(f"{question.question_id}: SGPA does not recompute")
            if {"terms", "expected_cgpa"}.issubset(example):
                credits = sum(item["credits"] for item in example["terms"])
                points = sum(item["credits"] * item["grade_point"] for item in example["terms"])
                if round(points / credits, 2) != example["expected_cgpa"]:
                    raise ValueError(f"{question.question_id}: CGPA does not recompute")
    except (KeyError, TypeError, ZeroDivisionError, ValueError, StopIteration) as exc:
        raise ProjectPolicyDatasetError(f"Numerical policy validation failed: {exc}") from exc


PROJECT_ASSUMPTION_PREFIX = (
    "PROJECT-AUTHORED DEMONSTRATION ASSUMPTION — NOT OFFICIAL UNIVERSITY POLICY. "
)
OFFICIAL_POLICY_ABSTENTION = (
    "The project-authored demonstration dataset cannot establish an official university policy. "
    "A current, applicable, verified institutional source is required."
)


def format_project_policy_context(policy: ProjectPolicyRecord | dict[str, Any]) -> str:
    """Label a generic retrieved record before it is shown in a demo answer/context."""
    try:
        record = policy if isinstance(policy, ProjectPolicyRecord) else ProjectPolicyRecord.model_validate(policy)
    except ValidationError as exc:
        raise ProjectPolicyDatasetError(f"Refusing unlabeled policy context: {exc}") from exc
    return f"{PROJECT_ASSUMPTION_PREFIX}{record.title}: {record.exact_text}"


def abstain_on_official_policy_question(question: str) -> str | None:
    """Evaluation-only guard: generic assumptions cannot answer institutional-policy queries."""
    normalized = f" {' '.join(question.casefold().split())} "
    institutional_markers = (
        " official ", "officially", "pes university", "university attendance",
        "university policy", "actual university", "institution-specific", "admission batch",
        "my batch", "current cohort", "real cohort", "2025 aiml batch", "2025-29 batch",
    )
    is_pes_query = re.search(r"\bpes\b", normalized) is not None
    is_batch_query = re.search(r"\bbatch\b", normalized) is not None
    return OFFICIAL_POLICY_ABSTENTION if is_pes_query or is_batch_query or any(marker in normalized for marker in institutional_markers) else None
