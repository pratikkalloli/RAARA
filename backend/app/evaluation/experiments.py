"""Controlled A/B/C prompt comparisons over one shared retrieval result."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict

from app.prompting.system_prompt import PromptType, get_prompt_configuration
from app.services.citation_verifier import CitationVerifier
from app.services.generator import GenerationError, GroqAnswerGenerator, StructuredAnswer
from app.services.retriever import RetrievalResult, Retriever


class PromptExperimentRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt_type: PromptType
    prompt_name: str
    system_instructions: str
    question: str
    retrieved_passage_ids: list[str]
    retrieved_context_hash: str
    model: str
    response: StructuredAnswer | None
    generation_latency_ms: float
    input_tokens: int | None = None
    output_tokens: int | None = None
    error: str | None = None


class ExperimentComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str
    retrieval_passage_ids: list[str]
    retrieval_context_hash: str
    retrieval_latency_ms: float
    model: str
    experiments: list[PromptExperimentRecord]


class PromptExperimentRunner:
    """Retrieve once, then run every prompt configuration with identical context/model."""

    def __init__(
        self,
        retriever: Retriever,
        generator: GroqAnswerGenerator,
        *,
        verifier: CitationVerifier | None = None,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self.retriever = retriever
        self.generator = generator
        self.verifier = verifier or CitationVerifier()
        self.clock = clock

    def run(
        self,
        question: str,
        *,
        top_k: int | None = None,
        metadata_filters: dict[str, str | int | float | bool] | None = None,
    ) -> ExperimentComparison:
        retrieval_start = self.clock()
        retrieval = self.retriever.retrieve(question, top_k=top_k, metadata_filters=metadata_filters)
        retrieval_latency_ms = _elapsed_ms(retrieval_start, self.clock())
        passage_ids = [passage.id for passage in retrieval.passages]
        context_hash = _context_hash(retrieval)
        experiment_records: list[PromptExperimentRecord] = []

        for prompt_type in PromptType:
            configuration = get_prompt_configuration(prompt_type)
            generation_start = self.clock()
            try:
                generated = self.generator.generate_with_usage(retrieval, prompt_type=prompt_type)
                verified = self.verifier.verify(generated.answer, retrieval)
                record = PromptExperimentRecord(
                    prompt_type=configuration.prompt_type,
                    prompt_name=configuration.name,
                    system_instructions=configuration.system_instructions,
                    question=retrieval.question,
                    retrieved_passage_ids=passage_ids,
                    retrieved_context_hash=context_hash,
                    model=generated.model,
                    response=verified.answer,
                    generation_latency_ms=_elapsed_ms(generation_start, self.clock()),
                    input_tokens=generated.input_tokens,
                    output_tokens=generated.output_tokens,
                )
            except GenerationError as exc:
                record = PromptExperimentRecord(
                    prompt_type=configuration.prompt_type,
                    prompt_name=configuration.name,
                    system_instructions=configuration.system_instructions,
                    question=retrieval.question,
                    retrieved_passage_ids=passage_ids,
                    retrieved_context_hash=context_hash,
                    model=self.generator.model,
                    response=None,
                    generation_latency_ms=_elapsed_ms(generation_start, self.clock()),
                    error=f"Generation failed ({type(exc).__name__}).",
                )
            experiment_records.append(record)

        return ExperimentComparison(
            question=retrieval.question,
            retrieval_passage_ids=passage_ids,
            retrieval_context_hash=context_hash,
            retrieval_latency_ms=retrieval_latency_ms,
            model=self.generator.model,
            experiments=experiment_records,
        )


def _context_hash(retrieval: RetrievalResult) -> str:
    context: dict[str, Any] = {
        "question": retrieval.question,
        "passages": [
            {"id": passage.id, "text": passage.text, "metadata": passage.metadata}
            for passage in retrieval.passages
        ],
    }
    serialized = json.dumps(context, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _elapsed_ms(start: float, end: float) -> float:
    return round(max(0.0, (end - start) * 1000), 3)
