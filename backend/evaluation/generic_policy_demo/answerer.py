"""Deterministic template/calculation answerer; this module is not an LLM."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from evaluation.generic_policy_demo.provenance import (
    CONTEXT_LABEL,
    GenericPolicyProvenanceError,
    validate_policy_record,
)
from evaluation.generic_policy_demo.retriever import RetrievedPolicy
from evaluation.project_authored_policies import abstain_on_official_policy_question
from evaluation.schemas.project_policy import ProjectPolicyDataset


DISCLAIMER = "Illustrative project assumption only; not verified PES University policy or a universal academic rule."


@dataclass(frozen=True)
class DemoCitation:
    policy_id: str
    evidence_id: str
    title: str
    category: str
    version: str
    provenance: str = "PROJECT_AUTHORED"
    source_type: str = "GENERIC_PROJECT_POLICY"
    authority_status: str = "NOT_OFFICIAL"
    is_official_university_policy: bool = False
    context_label: str = CONTEXT_LABEL


@dataclass(frozen=True)
class DemoAnswer:
    question: str
    answer: str
    status: str
    citations: tuple[DemoCitation, ...]
    disclaimer: str = DISCLAIMER


def calculate_attendance(attended: int, held: int) -> tuple[float, str]:
    if isinstance(attended, bool) or isinstance(held, bool) or not isinstance(attended, int) or not isinstance(held, int):
        raise ValueError("Class counts must be whole numbers")
    if held <= 0:
        raise ValueError("Total classes must be greater than zero")
    if attended < 0 or attended > held:
        raise ValueError("Attended classes must be between zero and total classes")
    value = round(attended / held * 100, 2)
    return value, f"({attended} / {held}) x 100 = {value:.2f}%"


def _illustrative_weights(dataset: ProjectPolicyDataset) -> tuple[float, float, str]:
    record = next(p for p in dataset.policies if p.policy_id == "GAP-ASSESS-001")
    validate_policy_record(record)
    details = record.calculation_details or {}
    internal = float(details["internal_weight_percent"]) / 100
    exam = float(details["end_semester_weight_percent"]) / 100
    if internal < 0 or exam < 0 or round(internal + exam, 8) != 1:
        raise ValueError("Assessment weights in the dataset must be nonnegative and sum to 100%")
    return internal, exam, record.evidence_id


def calculate_course_total(internal_score: float, exam_score: float, dataset: ProjectPolicyDataset) -> tuple[float, str, str]:
    for name, value in (("Internal", internal_score), ("End-semester", exam_score)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 100:
            raise ValueError(f"{name} score must be between 0 and 100")
    internal_weight, exam_weight, evidence_id = _illustrative_weights(dataset)
    total = round(float(internal_score) * internal_weight + float(exam_score) * exam_weight, 2)
    steps = f"({internal_score:g} x {internal_weight:g}) + ({exam_score:g} x {exam_weight:g}) = {total:.2f}/100"
    return total, steps, evidence_id


def _grade_point_max(dataset: ProjectPolicyDataset) -> float:
    record = next(p for p in dataset.policies if p.policy_id == "GAP-GRADE-001")
    validate_policy_record(record)
    return float((record.calculation_details or {})["scale_max"])


def calculate_sgpa(courses: Iterable[tuple[float, float]], dataset: ProjectPolicyDataset) -> tuple[float, str, str]:
    return _calculate_credit_weighted(courses, dataset, category="sgpa")


def calculate_cgpa(courses: Iterable[tuple[float, float]], dataset: ProjectPolicyDataset) -> tuple[float, str, str]:
    return _calculate_credit_weighted(courses, dataset, category="cgpa")


def _calculate_credit_weighted(courses: Iterable[tuple[float, float]], dataset: ProjectPolicyDataset, *, category: str) -> tuple[float, str, str]:
    items = list(courses)
    if not items:
        raise ValueError("At least one course/term is required")
    max_point = _grade_point_max(dataset)
    numerator = 0.0
    credits_total = 0.0
    rendered: list[str] = []
    for credits, grade_point in items:
        if isinstance(credits, bool) or isinstance(grade_point, bool):
            raise ValueError("Credits and grade points must be numeric")
        if not isinstance(credits, (int, float)) or credits <= 0:
            raise ValueError("Every course credit value must be greater than zero")
        if not isinstance(grade_point, (int, float)) or not 0 <= grade_point <= max_point:
            raise ValueError(f"Grade points must be between zero and {max_point:g}")
        credits_total += credits
        numerator += credits * grade_point
        rendered.append(f"{credits:g}x{grade_point:g}")
    if credits_total <= 0:
        raise ValueError("Total credits must be greater than zero")
    value = round(numerator / credits_total, 2)
    record = next(p for p in dataset.policies if p.category == category and p.calculation_details and "formula" in p.calculation_details)
    validate_policy_record(record)
    steps = f"({' + '.join(rendered)}) / {credits_total:g} credits = {value:.2f}"
    return value, steps, record.evidence_id


def _citations(evidence: Iterable[RetrievedPolicy]) -> tuple[DemoCitation, ...]:
    seen: set[str] = set()
    citations: list[DemoCitation] = []
    for row in evidence:
        if row.evidence_id in seen:
            continue
        seen.add(row.evidence_id)
        citations.append(DemoCitation(
            policy_id=row.policy_id,
            evidence_id=row.evidence_id,
            title=row.title,
            category=row.category,
            version=row.version,
            provenance=row.provenance,
            source_type=row.source_type,
            authority_status=row.authority_status,
            is_official_university_policy=row.is_official_university_policy,
            context_label=row.context_label,
        ))
    return tuple(citations)


def _as_answer(question: str, text: str, status: str, refs: Iterable[RetrievedPolicy] = ()) -> DemoAnswer:
    citations = _citations(refs)
    if status in {"SUPPORTED", "CONFLICTING_SOURCES"} and not citations:
        return DemoAnswer(question, "No validated project evidence was available to support an answer.", "NOT_FOUND", (), DISCLAIMER)
    return DemoAnswer(question, text, status, citations, DISCLAIMER)


class DeterministicPolicyAnswerer:
    """Builds fixed, evidence-linked responses and arithmetic without an LLM."""

    def __init__(self, dataset: ProjectPolicyDataset):
        self.dataset = dataset
        self.policy_by_id = {p.policy_id: validate_policy_record(p) for p in dataset.policies}

    @staticmethod
    def _is_ambiguous(question: str) -> bool:
        text = " ".join(question.casefold().split())
        return (
            len(text.split()) <= 3
            or text in {"is it enough?", "what about that?", "will i qualify?", "what about eligibility?"}
            or ("particular student" in text and "eligible" in text)
        )

    def answer(self, question: str, evidence: list[RetrievedPolicy]) -> DemoAnswer:
        if not question or not question.strip():
            raise ValueError("Question cannot be blank")
        question = question.strip()
        # Validate retrieval payload independently of the retriever.
        known = {p.evidence_id: p for p in self.policy_by_id.values()}
        for row in evidence:
            original = known.get(row.evidence_id)
            if (
                original is None
                or row.policy_id != original.policy_id
                or row.title != original.title
                or row.category != original.category
                or row.version != original.version
                or row.exact_text != original.exact_text
                or row.provenance != "PROJECT_AUTHORED"
                or row.source_type != "GENERIC_PROJECT_POLICY"
                or row.authority_status != "NOT_OFFICIAL"
                or row.is_official_university_policy is not False
                or row.context_label != CONTEXT_LABEL
            ):
                raise GenericPolicyProvenanceError("Retrieved evidence does not match the validated dataset.")
            validate_policy_record(original)
        official_abstention = abstain_on_official_policy_question(question)
        if official_abstention:
            return _as_answer(question, official_abstention, "NOT_FOUND")
        if self._is_ambiguous(question):
            return _as_answer(question, "Please clarify the policy area, calculation inputs, or student context you mean.", "NEEDS_CLARIFICATION")
        if not evidence:
            return _as_answer(question, "The generic project-policy corpus has no sufficiently relevant evidence for this question.", "NOT_FOUND")

        text = question.casefold()

        # Deliberately authored contradictory versions must be reported side by side.
        if "version" in text or "conflict" in text:
            conflict_rows = [row for row in evidence if row.policy_id in {"GAP-ATT-001", "GAP-ATT-029"}]
            if len(conflict_rows) == 2:
                conflict_rows.sort(key=lambda row: row.version)
                answer = "The two project-authored versions conflict: " + "; ".join(
                    f"version {row.version}: {row.exact_text}" for row in conflict_rows
                ) + " This is a demonstration conflict, not a university amendment."
                return _as_answer(question, answer, "CONFLICTING_SOURCES", conflict_rows)

        # Numerical input patterns are handled only when the corresponding formula evidence was retrieved.
        attendance_match = re.search(r"attended\s+(\d+)\s+(?:classes?\s+)?(?:out of|of)\s+(\d+)", text)
        if attendance_match:
            attended, held = map(int, attendance_match.groups())
            refs = [row for row in evidence if row.policy_id in {"GAP-ATT-002", "GAP-ATT-003"}]
            if not any(row.policy_id == "GAP-ATT-002" for row in refs):
                return _as_answer(question, "Attendance calculation evidence was not retrieved.", "NOT_FOUND")
            value, steps = calculate_attendance(attended, held)
            if "shortfall" in text or "below" in text:
                threshold_policy = next((row for row in refs if row.policy_id == "GAP-ATT-003"), None)
                if threshold_policy:
                    threshold = float((threshold_policy.calculation_details or {})["example"]["threshold_percent"])
                    return _as_answer(question, f"Illustrative attendance is {steps}. Relative to the example's {threshold:g}% threshold, the shortfall is {max(0.0, round(threshold - value, 2)):.2f} percentage points.", "SUPPORTED", refs)
                return _as_answer(question, "The attendance shortfall threshold evidence was not retrieved, so the demo cannot calculate the requested comparison.", "NOT_FOUND")
            return _as_answer(question, f"Illustrative attendance is {steps}. This calculation alone does not establish institutional eligibility.", "SUPPORTED", refs[:1])

        internal_match = re.search(r"internal(?: assessment)? score(?: is| of|\s+)?\s*(\d+(?:\.\d+)?)\s*(?:/\s*100)?", text)
        exam_match = re.search(r"(?:end[ -]semester|exam(?:ination)?) score(?: is| of|\s+)?\s*(\d+(?:\.\d+)?)", text)
        if internal_match and exam_match:
            refs = [row for row in evidence if row.policy_id in {"GAP-ASSESS-001", "GAP-ASSESS-002", "GAP-ASSESS-003"}]
            if not any(row.policy_id == "GAP-ASSESS-001" for row in refs):
                return _as_answer(question, "Assessment-weight evidence was not retrieved.", "NOT_FOUND")
            value, steps, _ = calculate_course_total(float(internal_match.group(1)), float(exam_match.group(1)), self.dataset)
            return _as_answer(question, f"Illustrative weighted course total: {steps}.", "SUPPORTED", refs)

        pairs = [(float(c), float(g)) for c, g in re.findall(r"(\d+(?:\.\d+)?)\s*credits?\s*(?:at|,\s*(?:grade\s*point\s*)?)\s*(\d+(?:\.\d+)?)", text)]
        if pairs and "sgpa" in text:
            refs = [row for row in evidence if row.category == "sgpa"]
            value, steps, _ = calculate_sgpa(pairs, self.dataset)
            if refs:
                return _as_answer(question, f"Illustrative SGPA = {steps}.", "SUPPORTED", refs)
        if pairs and "cgpa" in text:
            refs = [row for row in evidence if row.category == "cgpa"]
            value, steps, _ = calculate_cgpa(pairs, self.dataset)
            if refs:
                return _as_answer(question, f"Illustrative CGPA = {steps}.", "SUPPORTED", refs)

        pass_match = re.search(r"(?:score|total)(?:\s+of|\s+is|\s*=)?\s*(\d+(?:\.\d+)?)", text)
        if pass_match and any(term in text for term in ("pass", "passing", "meet the requirement")):
            policy = self.policy_by_id["GAP-PASS-001"]
            threshold = float((policy.calculation_details or {})["overall_passing_score"])
            refs = [row for row in evidence if row.policy_id == policy.policy_id]
            if refs:
                score = float(pass_match.group(1))
                result = "meets" if score >= threshold else "does not meet"
                return _as_answer(question, f"The score {score:g}/100 {result} the illustrative overall threshold of {threshold:g}/100. No separate examination minimum is defined in this project policy.", "SUPPORTED", refs)

        grade_match = re.search(r"(?:score of|score is|score\s*=)\s*(\d+(?:\.\d+)?)", text)
        if grade_match and any(term in text for term in ("grade point", "grade-point", "map to")):
            policy = self.policy_by_id["GAP-GRADE-002"]
            refs = [row for row in evidence if row.policy_id == policy.policy_id]
            if refs:
                score = float(grade_match.group(1))
                band = next((band for band in (policy.calculation_details or {})["grade_bands"] if band["minimum"] <= score <= band["maximum"]), None)
                if band is None:
                    return _as_answer(question, "The sample grade table covers scores from 0 through 100; this score is outside that range.", "NOT_FOUND")
                return _as_answer(question, f"In the project-only sample, a score of {score:g} maps to {band['grade_point']} grade points.", "SUPPORTED", refs)

        # If a retrieved rule itself states the requested detail is not defined, cite that exact caveat.
        missing_terms = (
            "maximum", "deadline", "due date", "actual date", "medical", "exemption", "special relaxation",
            "contact hour", "hours per credit", "hours associated", "hours are associated", "promotion eligible", "promotion criteria", "promotion threshold",
            "year-back", "year back", "eligibility criteria", "minimum credits", "how many credits",
            "credits needed", "credits required", "credits to progress", "minimum exam", "minimum examination",
        )
        if any(term in text for term in missing_terms):
            missing = [row for row in evidence if any(term in row.exact_text.casefold() for term in ("does not specify", "not defined", "no fixed", "unspecified", "does not define", "no actual"))]
            if missing:
                return _as_answer(question, "The project-authored corpus does not specify the requested institution-specific value or exception. Consult the applicable current institutional rule.", "NOT_FOUND", missing[:2])

        # Simple intent-to-category choice prevents the top lexical hit alone determining all answers.
        desired = self._desired_category(text)
        preferred = self._preferred_policy_id(text)
        selected = next((row for row in evidence if row.policy_id == preferred), None) if preferred else None
        selected = selected or next((row for row in evidence if row.category in desired), evidence[0])
        if selected.score < 0:
            return _as_answer(question, "The generic project-policy corpus has no sufficiently relevant evidence for this question.", "NOT_FOUND")
        answer = selected.exact_text
        return _as_answer(question, answer, "SUPPORTED", [selected])

    @staticmethod
    def _desired_category(question: str) -> set[str]:
        mapping = {
            "attendance": {"attendance"}, "class": {"attendance"},
            "assessment": {"assessment"}, "internal": {"assessment"}, "end-semester": {"assessment"}, "exam score": {"assessment"},
            "pass": {"passing", "assessment"}, "grade": {"grading"}, "sgpa": {"sgpa"}, "cgpa": {"cgpa"},
            "backlog": {"backlogs"}, "supplementary": {"backlogs"}, "revaluation": {"revaluation"},
            "registration": {"course_registration"}, "add/drop": {"course_registration"}, "credit": {"credits"},
            "progression": {"academic_progression"}, "promotion": {"academic_progression"}, "calendar": {"academic_calendar"}, "semester": {"academic_calendar"},
        }
        return {category for token, categories in mapping.items() if token in question for category in categories}

    @staticmethod
    def _preferred_policy_id(question: str) -> str | None:
        if "attendance" in question and any(term in question for term in ("minimum", "threshold")):
            return "GAP-ATT-001"
        if "attendance" in question and "shortfall" in question:
            return "GAP-ATT-003"
        if "attendance" in question and any(term in question for term in ("formula", "calculate", "calculation")):
            return "GAP-ATT-002"
        if "assessment" in question and any(term in question for term in ("split", "weight")):
            return "GAP-ASSESS-001"
        if "backlog" in question and not any(term in question for term in ("supplementary", "attempt", "maximum")):
            return "GAP-BACKLOG-001"
        if "clear" in question and "course" in question:
            return "GAP-BACKLOG-002"
        if "sgpa" in question and "formula" in question:
            return "GAP-SGPA-001"
        if "cgpa" in question and "formula" in question:
            return "GAP-CGPA-001"
        return None
