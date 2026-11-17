"""Deterministic in-memory retrieval over project-authored policy records."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from evaluation.project_authored_policies import load_project_policy_dataset
from evaluation.retrieval.embeddings import DeterministicTfidfHashEmbedding
from evaluation.schemas.project_policy import ProjectPolicyDataset, ProjectPolicyRecord
from evaluation.generic_policy_demo.provenance import CONTEXT_LABEL, validate_policy_record


DEFAULT_MIN_RELEVANCE = 0.12
DEFAULT_TOP_K = 5
DEFAULT_DATASET_PATH = Path(__file__).resolve().parents[1] / "datasets/project_authored_academic_policy/generic_academic_policy_dataset.json"


@dataclass(frozen=True)
class RetrievedPolicy:
    policy_id: str
    evidence_id: str
    title: str
    category: str
    exact_text: str
    version: str
    provenance: str
    source_type: str
    authority_status: str
    is_official_university_policy: bool
    context_label: str
    score: float
    calculation_details: dict[str, Any] | None


class GenericPolicyRetriever:
    """Uses the existing offline TF/hash embedder; index lifetime is process-local."""

    def __init__(
        self,
        dataset: ProjectPolicyDataset | None = None,
        *,
        dataset_path: str | Path = DEFAULT_DATASET_PATH,
        min_relevance: float = DEFAULT_MIN_RELEVANCE,
        top_k: int = DEFAULT_TOP_K,
        embedder: DeterministicTfidfHashEmbedding | None = None,
    ) -> None:
        if not 0.0 <= min_relevance <= 1.0:
            raise ValueError("min_relevance must be between 0 and 1")
        if top_k < 1:
            raise ValueError("top_k must be at least 1")
        self.dataset = dataset or load_project_policy_dataset(dataset_path)
        self.records: list[ProjectPolicyRecord] = [validate_policy_record(row) for row in self.dataset.policies]
        self.min_relevance = float(min_relevance)
        self.top_k = int(top_k)
        self.embedder = embedder or DeterministicTfidfHashEmbedding()
        self.texts = [f"{record.title}. Category: {record.category}. Version: {record.version}. {record.exact_text}" for record in self.records]
        self.embedder.fit_documents(self.texts)
        self.vectors = self.embedder.embed_texts(self.texts)

    def retrieve(self, question: str, *, top_k: int | None = None) -> list[RetrievedPolicy]:
        if not question or not question.strip():
            raise ValueError("Question cannot be blank")
        limit = self.top_k if top_k is None else top_k
        if limit < 1:
            raise ValueError("top_k must be at least 1")
        query = question.strip()
        normalized = query.casefold()
        expansions: list[str] = []
        if any(token in normalized for token in ("attend", "class", "attendance")) and (
            "attended" in normalized or "out of" in normalized or "shortfall" in normalized
            or "below" in normalized or "percentage point" in normalized or "calculation" in normalized
        ):
            expansions.append("attendance classes attended held attendance percentage threshold")
            if "below" in normalized or "shortfall" in normalized or "percentage point" in normalized:
                expansions.append("attendance shortfall percentage points below minimum threshold attendance requirement")
        if any(token in normalized for token in ("sgpa", "cgpa", "grade point", "credit")):
            expansions.append("credit weighted grade point formula cumulative semester academic score")
        if "credit" in normalized and any(token in normalized for token in ("hour", "workload")):
            expansions.append("course credits workload contact hours equivalence not defined")
        if any(token in normalized for token in ("progression", "promotion", "year-back", "year back")):
            expansions.append("academic progression promotion criteria prerequisites minimum credits institution-specific not defined")
        if any(token in normalized for token in ("assessment", "internal", "end-semester", "exam score", "course score")):
            expansions.append("internal assessment end semester weighted total percentage course score")
        if ("version" in normalized or "conflict" in normalized) and "attend" in normalized:
            expansions.append("attendance minimum threshold project-authored policy version 0.9 version 1.0")
        if "supplementary" in normalized or "backlog" in normalized:
            expansions.append("backlog supplementary attempt examination attempts unspecified")
        query_text = " ".join((query, *expansions))
        query_vector = self.embedder.embed_texts([query_text])[0]
        ranked: list[tuple[float, ProjectPolicyRecord]] = []
        for record, vector in zip(self.records, self.vectors):
            # Recheck provenance on every retrieval; scores are relevance hints only.
            record = validate_policy_record(record)
            score = sum(a * b for a, b in zip(query_vector, vector))
            if score >= self.min_relevance:
                ranked.append((score, record))
        ranked.sort(key=lambda item: (-item[0], item[1].policy_id))
        output: list[RetrievedPolicy] = []
        seen: set[str] = set()
        for score, record in ranked:
            if record.evidence_id in seen:
                continue
            seen.add(record.evidence_id)
            output.append(RetrievedPolicy(
                policy_id=record.policy_id,
                evidence_id=record.evidence_id,
                title=record.title,
                category=record.category,
                exact_text=record.exact_text,
                version=record.version,
                provenance=record.provenance,
                source_type=record.source_type,
                authority_status=record.authority_status,
                is_official_university_policy=record.is_official_university_policy,
                context_label=CONTEXT_LABEL,
                score=round(float(score), 6),
                calculation_details=record.calculation_details,
            ))
            if len(output) >= limit:
                break
        return output
