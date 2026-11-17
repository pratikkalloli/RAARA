"""End-to-end isolated generic academic-policy demonstration pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from evaluation.generic_policy_demo.answerer import DemoAnswer, DemoCitation, DeterministicPolicyAnswerer
from evaluation.generic_policy_demo.retriever import (
    DEFAULT_DATASET_PATH,
    DEFAULT_MIN_RELEVANCE,
    DEFAULT_TOP_K,
    GenericPolicyRetriever,
    RetrievedPolicy,
)
from evaluation.project_authored_policies import load_project_policy_dataset
from evaluation.schemas.project_policy import ProjectPolicyDataset


@dataclass(frozen=True)
class DemoRun:
    question: str
    retrieved: tuple[RetrievedPolicy, ...]
    answer: DemoAnswer
    citations_validated: bool


class GenericPolicyDemo:
    def __init__(
        self,
        *,
        dataset_path: str | Path = DEFAULT_DATASET_PATH,
        min_relevance: float = DEFAULT_MIN_RELEVANCE,
        top_k: int = DEFAULT_TOP_K,
        dataset: ProjectPolicyDataset | None = None,
    ) -> None:
        self.dataset = dataset or load_project_policy_dataset(dataset_path)
        self.retriever = GenericPolicyRetriever(
            self.dataset, min_relevance=min_relevance, top_k=top_k,
        )
        self.answerer = DeterministicPolicyAnswerer(self.dataset)

    def ask(self, question: str) -> DemoRun:
        retrieved = tuple(self.retriever.retrieve(question))
        answer = self.answerer.answer(question, list(retrieved))
        evidence_by_id = {row.evidence_id: row for row in retrieved}
        valid = all(
            citation.evidence_id in evidence_by_id
            and citation.policy_id == evidence_by_id[citation.evidence_id].policy_id
            and citation.title == evidence_by_id[citation.evidence_id].title
            and citation.version == evidence_by_id[citation.evidence_id].version
            and citation.provenance == "PROJECT_AUTHORED"
            and citation.source_type == "GENERIC_PROJECT_POLICY"
            and citation.authority_status == "NOT_OFFICIAL"
            and citation.is_official_university_policy is False
            and citation.context_label == "PROJECT_AUTHORED_GENERIC_POLICY"
            for citation in answer.citations
        )
        if not valid:
            abstention = DemoAnswer(
                question=question,
                answer="Citation validation failed; the demo is abstaining rather than substituting a different source.",
                status="NOT_FOUND",
                citations=(),
            )
            return DemoRun(question, retrieved, abstention, False)
        return DemoRun(question, retrieved, answer, True)
