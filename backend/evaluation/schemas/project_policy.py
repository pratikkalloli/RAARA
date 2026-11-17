"""Schemas for deliberately nonofficial project-authored policy demonstrations."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


ProjectPolicyCategory = Literal[
    "attendance", "assessment", "passing", "grading", "sgpa", "cgpa",
    "backlogs", "revaluation", "course_registration", "credits",
    "academic_progression", "academic_calendar",
]
ProjectQuestionStatus = Literal["SUPPORTED", "PARTIALLY_SUPPORTED", "NOT_FOUND", "CONFLICTING_SOURCES", "NEEDS_CLARIFICATION"]
ProjectQuestionCategory = Literal[
    "direct_factual", "numerical_calculation", "multi_policy", "unanswerable",
    "clarification", "conflicting_policy",
]


class ProjectPolicyRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_id: str = Field(pattern=r"^GAP-[A-Z]+-[0-9]{3}$")
    evidence_id: str = Field(pattern=r"^GAP-E-[A-Z]+-[0-9]{3}$")
    title: str = Field(min_length=5)
    category: ProjectPolicyCategory
    exact_text: str = Field(min_length=20)
    provenance: Literal["PROJECT_AUTHORED"]
    source_type: Literal["GENERIC_PROJECT_POLICY"]
    is_official_university_policy: Literal[False]
    authority_status: Literal["NOT_OFFICIAL"]
    review_status: Literal["PROJECT_APPROVED"]
    version: str = Field(min_length=1)
    effective_date: None = None
    applicability: Literal["RAARA project demonstration only; not institution- or batch-specific."]
    created_by: Literal["RAARA project team"]
    limitations: list[str] = Field(min_length=1)
    calculation_details: dict[str, Any] | None = None


class ProjectDemoQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str = Field(pattern=r"^GAP-Q-[0-9]{3}$")
    question: str = Field(min_length=5)
    is_project_demonstration_question: Literal[True]
    category: ProjectQuestionCategory
    expected_status: ProjectQuestionStatus
    expected_answer: str | None = None
    relevant_policy_ids: list[str] = Field(default_factory=list)
    relevant_evidence_ids: list[str] = Field(default_factory=list)
    calculation: dict[str, Any] | None = None
    evaluation_notes: str = Field(min_length=5)

    @model_validator(mode="after")
    def enforce_answerability(self) -> "ProjectDemoQuestion":
        if self.expected_status == "NOT_FOUND":
            if self.expected_answer or self.relevant_policy_ids or self.relevant_evidence_ids:
                raise ValueError("NOT_FOUND questions cannot contain fabricated answers or supporting evidence.")
        elif self.expected_status == "NEEDS_CLARIFICATION":
            if self.expected_answer or self.relevant_policy_ids or self.relevant_evidence_ids:
                raise ValueError("Clarification questions cannot claim an answer before the missing scope is supplied.")
        else:
            if not self.expected_answer or not self.relevant_policy_ids or not self.relevant_evidence_ids:
                raise ValueError("Answerable/conflict questions require an expected answer and linked evidence.")
        if self.category == "unanswerable" and self.expected_status != "NOT_FOUND":
            raise ValueError("Unanswerable demonstration questions must use NOT_FOUND status.")
        if self.category == "clarification" and self.expected_status != "NEEDS_CLARIFICATION":
            raise ValueError("Clarification questions must use NEEDS_CLARIFICATION status.")
        if self.expected_status == "CONFLICTING_SOURCES" and self.category != "conflicting_policy":
            raise ValueError("Conflicting-source answers must be labeled conflicting_policy.")
        return self


class ProjectPolicyDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_id: Literal["RAARA-GENERIC-ACADEMIC-POLICY"]
    dataset_version: str = Field(min_length=1)
    dataset_type: Literal["PROJECT_AUTHORED_GENERIC_POLICY"]
    is_official_university_policy: Literal[False]
    provenance: Literal["PROJECT_AUTHORED"]
    source_type: Literal["GENERIC_PROJECT_POLICY"]
    purpose: str = Field(min_length=20)
    policies: list[ProjectPolicyRecord] = Field(min_length=20, max_length=30)
    questions: list[ProjectDemoQuestion] = Field(min_length=25, max_length=30)

    @model_validator(mode="after")
    def validate_links_and_ids(self) -> "ProjectPolicyDataset":
        policy_ids = [p.policy_id for p in self.policies]
        evidence_ids = [p.evidence_id for p in self.policies]
        question_ids = [q.question_id for q in self.questions]
        for label, ids in (("policy_id", policy_ids), ("evidence_id", evidence_ids), ("question_id", question_ids)):
            if len(ids) != len(set(ids)):
                raise ValueError(f"Duplicate {label} in project-authored dataset.")
        by_policy = {p.policy_id: p for p in self.policies}
        by_evidence = {p.evidence_id: p for p in self.policies}
        for question in self.questions:
            if not set(question.relevant_policy_ids).issubset(by_policy):
                raise ValueError(f"{question.question_id} refers to an unknown policy.")
            if not set(question.relevant_evidence_ids).issubset(by_evidence):
                raise ValueError(f"{question.question_id} refers to unknown evidence.")
            linked = {by_evidence[e].policy_id for e in question.relevant_evidence_ids}
            if not linked.issubset(set(question.relevant_policy_ids)):
                raise ValueError(f"{question.question_id} evidence does not match its policy references.")
        return self
