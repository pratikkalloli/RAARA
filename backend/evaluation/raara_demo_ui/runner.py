"""Reproducible evaluation runner over the existing project-authored questions."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from evaluation.generic_policy_demo.pipeline import GenericPolicyDemo
from evaluation.generic_policy_demo.retriever import DEFAULT_DATASET_PATH
from evaluation.project_authored_policies import load_project_policy_dataset


@dataclass(frozen=True)
class QuestionEvaluation:
    question_id: str
    question: str
    category: str
    expected_answerability: str
    actual_status: str
    retrieved_evidence_ids: list[str]
    cited_evidence_ids: list[str]
    citation_validity: bool
    abstention_correctness: bool | None
    expected_evidence_retrieved: bool | None
    passed: bool


def run_dataset_evaluation(demo: GenericPolicyDemo | None = None) -> dict[str, Any]:
    """Run the unchanged 30-question dataset through one shared demo instance."""
    active_demo = demo or GenericPolicyDemo()
    dataset = active_demo.dataset
    rows: list[QuestionEvaluation] = []

    for item in dataset.questions:
        run = active_demo.ask(item.question)
        retrieved_ids = [row.evidence_id for row in run.retrieved]
        cited_ids = [row.evidence_id for row in run.answer.citations]
        expected_answerable = item.expected_status in {"SUPPORTED", "PARTIALLY_SUPPORTED", "CONFLICTING_SOURCES"}
        is_abstention = item.expected_status in {"NOT_FOUND", "NEEDS_CLARIFICATION"}
        status_matches = run.answer.status == item.expected_status
        evidence_retrieved = (
            set(item.relevant_evidence_ids).issubset(retrieved_ids)
            if expected_answerable
            else None
        )
        citation_valid = bool(run.citations_validated) and set(cited_ids).issubset(retrieved_ids)
        abstention_correct = status_matches if is_abstention else None
        passed = status_matches and citation_valid and (evidence_retrieved is not False)
        rows.append(QuestionEvaluation(
            question_id=item.question_id,
            question=item.question,
            category=item.category,
            expected_answerability=item.expected_status,
            actual_status=run.answer.status,
            retrieved_evidence_ids=retrieved_ids,
            cited_evidence_ids=cited_ids,
            citation_validity=citation_valid,
            abstention_correctness=abstention_correct,
            expected_evidence_retrieved=evidence_retrieved,
            passed=passed,
        ))

    expected_abstentions = [row for row in rows if row.abstention_correctness is not None]
    expected_answerable = [row for row in rows if row.expected_evidence_retrieved is not None]
    numerical = [row for row in rows if row.category == "numerical_calculation"]
    return {
        "dataset_id": dataset.dataset_id,
        "dataset_version": dataset.dataset_version,
        "policy_count": len(dataset.policies),
        "question_count": len(dataset.questions),
        "summary": {
            "passed_questions": sum(row.passed for row in rows),
            "failed_questions": sum(not row.passed for row in rows),
            "status_matches": sum(row.actual_status == row.expected_answerability for row in rows),
            "citation_validations_passed": sum(row.citation_validity for row in rows),
            "abstentions_expected": len(expected_abstentions),
            "abstentions_correct": sum(bool(row.abstention_correctness) for row in expected_abstentions),
            "answerable_questions": len(expected_answerable),
            "answerable_questions_with_all_expected_evidence_retrieved": sum(bool(row.expected_evidence_retrieved) for row in expected_answerable),
            "numerical_calculation_questions": len(numerical),
            "numerical_calculation_status_matches": sum(row.actual_status == row.expected_answerability for row in numerical),
        },
        "results": [asdict(row) for row in rows],
        "method_note": (
            "Diagnostic run over project-authored demonstration questions, not an official-policy benchmark. "
            "A citation-validity pass confirms ID and metadata consistency with retrieved corpus rows; "
            "it does not prove semantic faithfulness."
        ),
    }


def run_five_case_demo(demo: GenericPolicyDemo | None = None) -> list[dict[str, Any]]:
    """Run the five requested examiner cases, using corpus wording where specified."""
    active_demo = demo or GenericPolicyDemo()
    dataset = active_demo.dataset
    corpus_question = {item.question_id: item.question for item in dataset.questions}
    cases = [
        ("1", "Direct factual question", "What is the illustrative minimum attendance?", "SUPPORTED"),
        ("2", "Numerical attendance calculation", "A student attended 72 out of 90 classes. Calculate attendance.", "SUPPORTED"),
        ("3", "Multiple-policy attendance calculation", corpus_question["GAP-Q-003"], "SUPPORTED"),
        ("4", "Official PES policy question", "What is the official PES University attendance requirement?", "NOT_FOUND"),
        ("5", "Unanswerable question", corpus_question["GAP-Q-015"], "NOT_FOUND"),
    ]
    output = []
    for case_id, title, question, expected in cases:
        run = active_demo.ask(question)
        output.append({
            "case_id": case_id,
            "title": title,
            "question": question,
            "expected_status": expected,
            "actual_status": run.answer.status,
            "status_match": run.answer.status == expected,
            "answer": run.answer.answer,
            "retrieved_evidence_ids": [row.evidence_id for row in run.retrieved],
            "citations": [asdict(row) for row in run.answer.citations],
            "citations_validated": run.citations_validated,
            "disclaimer": run.answer.disclaimer,
            "evidence": [asdict(row) for row in run.retrieved],
        })
    return output


def grouped_questions(demo: GenericPolicyDemo | None = None) -> dict[str, list[dict[str, str]]]:
    """Group actual dataset question text without synthesizing examples."""
    active_demo = demo or GenericPolicyDemo()
    groups: dict[str, list[dict[str, str]]] = {
        key: [] for key in (
            "Attendance", "Assessment", "SGPA and CGPA", "Backlogs", "Revaluation",
            "Credits", "Official-policy questions", "Unanswerable questions",
        )
    }
    for item in active_demo.dataset.questions:
        text = item.question.casefold()
        if any(marker in text for marker in ("official", "pes university", "admission batch", "2025 b.tech aiml")):
            group = "Official-policy questions"
        elif item.category == "unanswerable":
            group = "Unanswerable questions"
        elif item.category == "clarification":
            group = "Unanswerable questions"
        elif item.category == "conflicting_policy":
            group = "Attendance"
        elif item.category == "numerical_calculation" and any(marker in text for marker in ("sgpa", "cgpa")):
            group = "SGPA and CGPA"
        elif "attendance" in text or "classes" in text or "threshold" in text:
            group = "Attendance"
        elif "sgpa" in text or "cgpa" in text or "grade point" in text or "grade table" in text:
            group = "SGPA and CGPA"
        elif "backlog" in text or "supplementary" in text:
            group = "Backlogs"
        elif "revaluation" in text:
            group = "Revaluation"
        elif "credit" in text:
            group = "Credits"
        else:
            group = "Assessment"
        groups[group].append({"question_id": item.question_id, "question": item.question})
    return groups


def calculation_evidence(demo: GenericPolicyDemo, evidence_id: str) -> dict[str, Any]:
    record = next((item for item in demo.dataset.policies if item.evidence_id == evidence_id), None)
    if record is None:
        raise ValueError("Calculation evidence is not present in the project-authored dataset.")
    return {
        "policy_id": record.policy_id,
        "evidence_id": record.evidence_id,
        "title": record.title,
        "category": record.category,
        "exact_text": record.exact_text,
        "provenance": record.provenance,
        "source_type": record.source_type,
        "authority_status": record.authority_status,
        "is_official_university_policy": record.is_official_university_policy,
    }
