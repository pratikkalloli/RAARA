"""Model-directed request interpretation and evidence-grounded chat orchestration."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from app.prompting.system_prompt import PromptType
from app.services.citation_verifier import CitationVerifier
from app.services.document_summarizer import DocumentSummarizer
from app.services.factual_verifier import FactualConsistencyVerifier
from app.services.generator import (
    AnswerStatus,
    CitationValidationSummary,
    StructuredAnswer,
)
from app.services.request_interpreter import RequestInterpretation
from app.services.retriever import Retriever


class AcademicChatService:
    def __init__(
        self,
        retriever: Retriever,
        generator: Any,
        verifier: CitationVerifier | None = None,
        document_summarizer: DocumentSummarizer | None = None,
        factual_verifier: FactualConsistencyVerifier | None = None,
    ) -> None:
        self.retriever = retriever
        self.generator = generator
        self.verifier = verifier or CitationVerifier()
        self.document_summarizer = document_summarizer
        self.factual_verifier = factual_verifier

    def answer(
        self,
        question: str,
        *,
        top_k: int | None = None,
        metadata_filters: dict[str, str | int | float | bool] | None = None,
        prompt_type: PromptType | str = PromptType.C,
        conversation_history: tuple[dict[str, str], ...] | list[dict[str, str]] = (),
        document_id: int | str | None = None,
        available_documents: tuple[dict[str, str], ...] | list[dict[str, str]] = (),
    ) -> StructuredAnswer:
        """Interpret via the configured model, then select the bounded workflow."""
        selected_document_id = _authorized_target_document(document_id, None, available_documents)
        if selected_document_id is _INVALID_TARGET:
            return _clarification_answer(
                "I could not match the requested document to one available in your account. Please select an accessible document."
            )

        interpretation: RequestInterpretation = self.generator.interpret_request(
            question,
            conversation_history=conversation_history,
            available_documents=available_documents,
            selected_document_id=selected_document_id,
        )

        selected_whole_document_scope = (
            selected_document_id is not None and interpretation.analysis_scope == "whole_document"
        )
        if interpretation.request_mode == "clarification" and not selected_whole_document_scope:
            return _clarification_answer(interpretation.clarification_question)

        if interpretation.request_mode == "conversation" and not selected_whole_document_scope:
            return self.generator.generate_conversational(
                question,
                conversation_history=conversation_history,
            )

        # The discriminated model route is authoritative. The legacy evidence
        # boolean remains schema-validated for consistency, but never decides
        # the workflow by itself.

        selected_document_id = _authorized_target_document(
            selected_document_id,
            interpretation.target_document_id,
            available_documents,
        )
        if selected_document_id is _INVALID_TARGET:
            return _clarification_answer(
                "I could not match the requested document to one available in your account. Please select an accessible document."
            )

        if interpretation.analysis_scope == "whole_document":
            if selected_document_id is None:
                return _clarification_answer(
                    interpretation.clarification_question
                    or "Which uploaded document should I analyze? Please select it from your document library."
                )
            if self.document_summarizer is None:
                return StructuredAnswer(
                    answer="Full-document analysis is unavailable because the document analysis service is not configured.",
                    evidence=[], sources=[], status=AnswerStatus.NOT_FOUND,
                    validation=CitationValidationSummary(citation_status="NOT_APPLICABLE"),
                    coverage="The document-wide workflow was unavailable for this request.",
                )
            return self.document_summarizer.summarize(
                selected_document_id,
                question,
                requested_points=interpretation.requested_items,
                prompt_type=prompt_type,
            )

        retrieval_query = interpretation.retrieval_query.strip()
        if not retrieval_query:
            return _clarification_answer(
                interpretation.clarification_question
                or "Could you rephrase the document question so I can identify what evidence to look for?"
            )

        filters = dict(metadata_filters or {})
        if interpretation.page_number is not None:
            filters["page_number"] = interpretation.page_number
        if selected_document_id is not None:
            filters["document_id"] = str(selected_document_id)

        retrieval = self.retriever.retrieve(
            retrieval_query,
            top_k=top_k if top_k is not None else interpretation.retrieval_limit,
            metadata_filters=filters or None,
            allow_multiple_documents=interpretation.retrieval_strategy == "comparison",
        )
        # Retrieval uses the model's semantic query, while the answering model and
        # persisted history receive the exact user message.
        retrieval = replace(retrieval, question=question)
        if not retrieval.passages:
            generated = self._generate_abstention(
                question, retrieval, available_documents, selected_document_id, conversation_history
            )
        else:
            generated = self.generator.generate(
                retrieval,
                prompt_type=prompt_type,
                conversation_history=conversation_history,
                response_format=interpretation.response_format,
            )
            if generated.status == AnswerStatus.NOT_FOUND and not generated.evidence:
                generated = self._generate_abstention(
                    question, retrieval, available_documents, selected_document_id, conversation_history
                )

        answer = self.verifier.verify(generated, retrieval).answer
        if self.factual_verifier is not None:
            answer = self.factual_verifier.verify(question, answer, retrieval)
        return answer

    def _generate_abstention(self, question, retrieval, available_documents, selected_document_id, history):
        explain = getattr(self.generator, "generate_abstention", None)
        if not callable(explain):
            return StructuredAnswer(
                answer="The available retrieval did not provide evidence sufficient to answer this question.",
                evidence=[],
                sources=[],
                status=AnswerStatus.NOT_FOUND,
                validation=CitationValidationSummary(
                    citation_status="NOT_APPLICABLE",
                    unsupported_claims_flagged=True,
                    issues=["INSUFFICIENT_RETRIEVED_EVIDENCE"],
                ),
            )
        return explain(
            question,
            retrieval=retrieval,
            available_documents=available_documents,
            selected_document_id=selected_document_id if selected_document_id is not _INVALID_TARGET else None,
            conversation_history=history,
        )


_INVALID_TARGET = object()


def _authorized_target_document(
    requested_document_id: int | str | None,
    interpreted_document_id: str | None,
    available_documents: tuple[dict[str, str], ...] | list[dict[str, str]],
) -> str | None | object:
    allowed_ids = {str(item.get("document_id", "")) for item in available_documents}
    if requested_document_id is not None:
        chosen = str(requested_document_id)
        if chosen not in allowed_ids:
            return _INVALID_TARGET
        return chosen
    if interpreted_document_id is None:
        return None
    chosen = str(interpreted_document_id)
    if chosen not in allowed_ids:
        return _INVALID_TARGET
    return chosen


def _clarification_answer(message: str | None) -> StructuredAnswer:
    return StructuredAnswer(
        answer=(message or "Could you clarify which document or information you mean?"),
        evidence=[],
        sources=[],
        status=AnswerStatus.NOT_FOUND,
        validation=CitationValidationSummary(citation_status="NOT_APPLICABLE"),
    )
