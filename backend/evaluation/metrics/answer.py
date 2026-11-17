from __future__ import annotations

import unicodedata
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


def normalize_answer(value: str) -> str:
    """Unicode-normalized, case-folded whitespace and punctuation normalization (not semantic)."""
    normalized = unicodedata.normalize("NFKC", value).casefold()
    characters = [" " if unicodedata.category(char).startswith("P") else char for char in normalized]
    return " ".join("".join(characters).split())


def normalized_exact_match(predicted: str, reference: str) -> float:
    """Binary lexical match after normalize_answer; it does not assess paraphrases or entailment."""
    return float(normalize_answer(predicted) == normalize_answer(reference))


class SemanticAssessment(BaseModel):
    """A storage contract for external human/judge scores; no evaluator is invoked here."""

    model_config = ConfigDict(extra="forbid")

    assessor: Literal["human", "llm_judge", "not_assessed"] = "not_assessed"
    claim_correctness: float | None = Field(default=None, ge=0, le=1)
    faithfulness: float | None = Field(default=None, ge=0, le=1)
    answer_relevance: float | None = Field(default=None, ge=0, le=1)
    notes: str | None = None

    @model_validator(mode="after")
    def require_assessor_for_scores(self) -> "SemanticAssessment":
        scores = (self.claim_correctness, self.faithfulness, self.answer_relevance)
        if self.assessor == "not_assessed" and any(score is not None for score in scores):
            raise ValueError("Semantic scores require an explicit human or llm_judge assessor.")
        return self
