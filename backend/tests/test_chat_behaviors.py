from __future__ import annotations

import pytest

from app.services.chat import AcademicChatService
from app.services.generator import AnswerStatus, StructuredAnswer
from app.services.generator import CitationValidationSummary, EvidenceItem, SourceItem
from app.services.factual_verifier import FactualConsistencyVerifier
from app.services.request_interpreter import RequestInterpretation
from app.services.retriever import RetrievalResult, RetrievedPassage


def interpretation(**overrides):
    values = {
        "request_mode": "document_evidence",
        "intent": "academic_question",
        "requires_document_evidence": True,
        "target_document_id": None,
        "retrieval_query": "model-rewritten semantic query",
        "retrieval_strategy": "focused",
        "retrieval_limit": 5,
        "requested_items": None,
        "response_format": "concise explanation",
        "analysis_scope": "retrieved_passages",
        "clarification_needed": False,
        "clarification_question": None,
        "page_number": None,
    }
    values.update(overrides)
    if "request_mode" not in overrides:
        if values["clarification_needed"]:
            values["request_mode"] = "clarification"
        elif not values["requires_document_evidence"]:
            values["request_mode"] = "conversation"
    return RequestInterpretation(**values)


class RecordingRetriever:
    def __init__(self, passages=()):
        self.calls = []
        self.passages = tuple(passages)

    def retrieve(self, question, **kwargs):
        self.calls.append((question, kwargs))
        return RetrievalResult(question, self.passages, kwargs.get("top_k", 5), 0.35)


def retrieval_passage():
    return RetrievedPassage(
        "synthetic-passage", "Synthetic test evidence for retrieval routing.",
        {"document_id": "7", "document_name": "Synthetic fixture.pdf", "document_type": "synthetic_test",
         "page_number": 1, "section": "Synthetic section", "academic_year": "", "version": "1",
         "effective_date": "", "source_type": "synthetic_test", "verification_status": "unverified"},
        0.1, 0.9,
    )


class ModelMock:
    def __init__(self, interpretation_result=None):
        self.interpretation_result = interpretation_result or interpretation()
        self.interpretation_calls = []
        self.conversation_calls = []
        self.generation_calls = []

    def interpret_request(self, question, **kwargs):
        self.interpretation_calls.append((question, kwargs))
        return self.interpretation_result

    def generate_conversational(self, question, **kwargs):
        self.conversation_calls.append((question, kwargs))
        return StructuredAnswer(
            answer="A natural mocked assistant response.", evidence=[], sources=[], status=AnswerStatus.CONVERSATIONAL
        )

    def generate(self, retrieval, **kwargs):
        self.generation_calls.append((retrieval, kwargs))
        return StructuredAnswer(
            answer="No support in the synthetic test passages.", evidence=[], sources=[], status=AnswerStatus.NOT_FOUND
        )


class RecordingSummarizer:
    def __init__(self):
        self.calls = []

    def summarize(self, document_id, question, **kwargs):
        self.calls.append((str(document_id), question, kwargs))
        return StructuredAnswer(
            answer="Synthetic summary only.", evidence=[], sources=[], status=AnswerStatus.PARTIALLY_SUPPORTED
        )


def test_conversation_uses_model_classification_and_response_without_retrieval():
    for message in (
        "Hello, nice to meet you.",
        "Hey, how are things?",
        "Can you help me understand how to use this?",
        "Thank you for explaining that topic.",
    ):
        retriever = RecordingRetriever()
        model = ModelMock(interpretation(request_mode="conversation", requires_document_evidence=False, retrieval_query="", retrieval_strategy="none", analysis_scope="none", intent="conversation"))
        answer = AcademicChatService(retriever, model).answer(message)

        assert answer.status == AnswerStatus.CONVERSATIONAL
        assert answer.evidence == [] and answer.sources == []
        assert retriever.calls == []
        assert model.interpretation_calls[0][0] == message
        assert model.conversation_calls[0][0] == message


def test_academic_request_uses_model_retrieval_query_and_original_question_for_answer():
    original = "In my own words, what conditions must be met before I can sit the exam?"
    retriever = RecordingRetriever([retrieval_passage()])
    model = ModelMock(interpretation(retrieval_query="examination eligibility conditions and prerequisites"))

    AcademicChatService(retriever, model).answer(original)

    assert retriever.calls[0][0] == "examination eligibility conditions and prerequisites"
    retrieval, options = model.generation_calls[0]
    assert retrieval.question == original
    assert options["response_format"] == "concise explanation"


def test_interpreter_history_and_authorized_document_list_are_supplied():
    retriever, model = RecordingRetriever(), ModelMock()
    history = [{"role": "user", "content": "Earlier question"}, {"role": "assistant", "content": "Earlier answer"}]
    docs = [{"document_id": "7", "document_name": "Owned synthetic fixture.pdf"}]

    AcademicChatService(retriever, model).answer("Follow up on that", conversation_history=history, available_documents=docs)

    assert model.interpretation_calls[0][1]["conversation_history"] == history
    assert model.interpretation_calls[0][1]["available_documents"] == docs
    assert model.interpretation_calls[0][1]["selected_document_id"] is None


def test_meaningful_prior_answer_followup_can_remain_conversational_without_retrieval():
    history = [
        {"role": "user", "content": "What does the synthetic attendance workbook say about totals?"},
        {"role": "assistant", "content": "It describes a fictional total and says it is not an official rule.",
         "answer_status": "PARTIALLY_SUPPORTED", "evidence_count": 1},
    ]
    retriever = RecordingRetriever()
    model = ModelMock(interpretation(
        request_mode="conversation", requires_document_evidence=False, retrieval_query="",
        retrieval_strategy="none", analysis_scope="none", intent="conversation",
    ))

    answer = AcademicChatService(retriever, model).answer(
        "Can you explain that further?", conversation_history=history
    )

    assert answer.status == AnswerStatus.CONVERSATIONAL
    assert model.conversation_calls[0][1]["conversation_history"] == history
    assert retriever.calls == []


def test_not_found_prior_answer_is_context_not_factual_evidence_for_vague_followup():
    history = [
        {"role": "user", "content": "What does ISA mean in this discussion?"},
        {"role": "assistant", "content": "I could not support an answer from the available documents.",
         "answer_status": "NOT_FOUND", "evidence_count": 0},
    ]
    retriever = RecordingRetriever()
    model = ModelMock(interpretation(
        request_mode="conversation", requires_document_evidence=False, retrieval_query="",
        retrieval_strategy="none", analysis_scope="none", intent="conversation",
    ))
    def generate_conversational(question, **kwargs):
        model.conversation_calls.append((question, kwargs))
        return StructuredAnswer(
            answer="The prior reply only stated that there was insufficient support; it did not define the term.",
            evidence=[], sources=[], status=AnswerStatus.CONVERSATIONAL,
        )

    model.generate_conversational = generate_conversational

    answer = AcademicChatService(retriever, model).answer(
        "Can you explain that further?", conversation_history=history
    )

    assert "did not define the term" in answer.answer
    assert "ISA" not in answer.answer
    assert model.interpretation_calls[0][1]["conversation_history"] == history
    assert retriever.calls == []
    assert len(model.conversation_calls) == 1


def test_followup_with_multiple_plausible_referents_clarifies_without_retrieval():
    history = [
        {"role": "user", "content": "Compare two synthetic sections."},
        {"role": "assistant", "content": "Section A describes attendance; Section B describes grading."},
    ]
    retriever = RecordingRetriever()
    model = ModelMock(interpretation(
        request_mode="clarification", requires_document_evidence=False,
        clarification_needed=True, clarification_question="Which section would you like me to explain?",
        retrieval_query="", retrieval_strategy="none", analysis_scope="none",
    ))

    answer = AcademicChatService(retriever, model).answer(
        "Can you explain that further?", conversation_history=history
    )

    assert answer.status == AnswerStatus.NOT_FOUND
    assert answer.answer == "Which section would you like me to explain?"
    assert retriever.calls == []
    assert model.generation_calls == []


def test_academic_followup_uses_all_recent_turns_for_semantic_retrieval_query():
    history = [
        {"role": "user", "content": "What does the fictional assessment section say?"},
        {"role": "assistant", "content": "It describes a synthetic ISA and ESA example."},
        {"role": "user", "content": "Which part is the final assessment?"},
        {"role": "assistant", "content": "The example distinguishes ISA from ESA."},
    ]
    retriever, model = RecordingRetriever([retrieval_passage()]), ModelMock(interpretation(
        retrieval_query="synthetic assessment section; identify the ESA component",
        target_document_id=None,
    ))
    question = "What about its marks?"

    AcademicChatService(retriever, model).answer(question, conversation_history=history)

    assert model.interpretation_calls[0][1]["conversation_history"] == history
    assert retriever.calls[0][0] == "synthetic assessment section; identify the ESA component"
    assert model.generation_calls[0][0].question == question


def test_missing_history_is_explicitly_empty_and_does_not_invent_a_referent():
    retriever, model = RecordingRetriever(), ModelMock(interpretation(
        request_mode="clarification", requires_document_evidence=False,
        clarification_needed=True, clarification_question="What would you like me to explain?",
        retrieval_query="", retrieval_strategy="none", analysis_scope="none",
    ))
    answer = AcademicChatService(retriever, model).answer("Can you explain that further?")

    assert model.interpretation_calls[0][1]["conversation_history"] == ()
    assert answer.answer == "What would you like me to explain?"
    assert retriever.calls == []


def test_no_retrieved_evidence_uses_model_explanation_with_available_document_state():
    class AbstentionModel(ModelMock):
        def __init__(self):
            super().__init__()
            self.abstention_calls = []

        def generate_abstention(self, question, **kwargs):
            self.abstention_calls.append((question, kwargs))
            return StructuredAnswer(
                answer="The only available source is synthetic and unverified, so it cannot establish an official requirement.",
                evidence=[], sources=[], status=AnswerStatus.NOT_FOUND,
            )

    retriever, model = RecordingRetriever(), AbstentionModel()
    docs = [{"document_id": "7", "document_name": "Synthetic example.pdf",
             "verification_status": "unverified", "source_type": "synthetic_test"}]
    answer = AcademicChatService(retriever, model).answer(
        "What is the official requirement?", available_documents=docs
    )

    assert answer.status == AnswerStatus.NOT_FOUND
    assert "synthetic and unverified" in answer.answer
    assert model.abstention_calls[0][1]["available_documents"] == docs
    assert model.abstention_calls[0][1]["retrieval"].passages == ()
    assert model.generation_calls == []


def test_relevant_unverified_abstention_explanation_survives_citation_verifier():
    passage = retrieval_passage()

    class RelevantRetriever:
        def retrieve(self, question, **kwargs):
            return RetrievalResult(question, (passage,), kwargs.get("top_k", 5), 0.35)

    class SpecificAbstentionModel(ModelMock):
        def generate_abstention(self, question, **kwargs):
            return StructuredAnswer(
                answer="The retrieved passage is synthetic and unverified, so it cannot establish an official university rule.",
                evidence=[], sources=[], status=AnswerStatus.NOT_FOUND,
                validation=CitationValidationSummary(
                    citation_status="NOT_APPLICABLE", unsupported_claims_flagged=True,
                    issues=["INSUFFICIENT_RETRIEVED_EVIDENCE"],
                ),
            )

    answer = AcademicChatService(RelevantRetriever(), SpecificAbstentionModel()).answer(
        "What is the official requirement?"
    )

    assert answer.status == AnswerStatus.NOT_FOUND
    assert "synthetic and unverified" in answer.answer
    assert answer.evidence == [] and answer.sources == []
    assert answer.validation.citation_status == "NOT_APPLICABLE"


def test_chat_citation_validation_is_followed_by_numerical_consistency_check():
    metadata = {
        "document_id": "7", "document_name": "Synthetic assessment (NOT OFFICIAL)",
        "document_type": "synthetic_test", "page_number": 1, "section": "Fictional allocation",
        "version": "1", "effective_date": "", "academic_year": "", "source_type": "synthetic_test",
        "verification_status": "unverified",
    }
    passage = RetrievedPassage(
        "real-passage", "ISA allocation is 40 marks and ESA allocation is 60 marks; separate scores are 32 and 45.",
        metadata, 0.1, 0.9,
    )

    class NumericRetriever:
        calls = []
        def retrieve(self, question, **kwargs):
            self.calls.append(question)
            return RetrievalResult(question, (passage,), 5, 0.35)

    class NumericModel(ModelMock):
        def generate(self, retrieval, **kwargs):
            return StructuredAnswer(
                answer="ISA allocation is 32 marks and ESA allocation is 45 marks.",
                evidence=[EvidenceItem(
                    text=passage.text, document=metadata["document_name"], page=1, section=metadata["section"],
                    passage_id=passage.id, document_id="7", version="1", effective_date="",
                    academic_year="", verification_status="unverified",
                )],
                sources=[SourceItem(
                    document=metadata["document_name"], document_id="7", document_type="synthetic_test",
                    pages=[1], sections=[metadata["section"]], academic_year="", version="1", effective_date="",
                    source_type="synthetic_test", verification_status="unverified",
                )], status=AnswerStatus.PARTIALLY_SUPPORTED,
                validation=CitationValidationSummary(citation_status="VERIFIED"),
            )

    checker_calls = []
    def reject_wrong_allocation(question, answer, evidence):
        checker_calls.append((question, answer, evidence))
        return {"checks": [{
            "claim": "32 ISA allocation and 45 ESA allocation marks",
            "verdict": "UNSUPPORTED",
            "evidence_ids": ["real-passage"],
        }]}

    retriever, generator = NumericRetriever(), NumericModel()
    service = AcademicChatService(
        retriever,
        generator,
        factual_verifier=FactualConsistencyVerifier(reject_wrong_allocation),
    )
    answer = service.answer("What is the allocation of marks for ISA and ESA?")

    assert answer.status == AnswerStatus.NOT_FOUND
    assert "32" not in answer.answer and "45" not in answer.answer
    assert answer.evidence[0].passage_id == "real-passage"
    assert checker_calls[0][0] == "What is the allocation of marks for ISA and ESA?"
    assert checker_calls[0][2][0]["passage_id"] == "real-passage"


def test_model_generated_unavailable_document_id_is_rejected_before_retrieval():
    retriever = RecordingRetriever()
    model = ModelMock(interpretation(target_document_id="999", analysis_scope="whole_document", retrieval_strategy="document_wide"))
    answer = AcademicChatService(retriever, model).answer(
        "Analyze my selected document", available_documents=[{"document_id": "7", "document_name": "Owned.pdf"}]
    )
    assert answer.status == AnswerStatus.NOT_FOUND
    assert retriever.calls == []
    assert "accessible document" in answer.answer


def test_selected_document_scope_reaches_interpreter_and_summary_even_if_it_asks_which_document():
    retriever = RecordingRetriever()
    model = ModelMock(interpretation(
        request_mode="clarification", clarification_needed=True,
        clarification_question="Which document should I summarize?", intent="document_summary",
        analysis_scope="whole_document", retrieval_strategy="document_wide", retrieval_query="",
    ))
    summarizer = RecordingSummarizer()
    documents = [{"document_id": "7", "document_name": "Owned synthetic test.pdf", "verification_status": "unverified"}]
    answer = AcademicChatService(retriever, model, document_summarizer=summarizer).answer(
        "Summarize the entire document in five points.",
        document_id=7,
        available_documents=documents,
    )

    assert answer.answer == "Synthetic summary only."
    assert model.interpretation_calls[0][1]["selected_document_id"] == "7"
    assert summarizer.calls == [("7", "Summarize the entire document in five points.", {"requested_points": None, "prompt_type": "C"})]
    assert retriever.calls == []


def test_explicit_selected_document_is_not_widened_to_model_target():
    retriever = RecordingRetriever()
    model = ModelMock(interpretation(
        intent="document_summary", target_document_id="8", analysis_scope="whole_document",
        retrieval_strategy="document_wide", retrieval_query="",
    ))
    summarizer = RecordingSummarizer()
    docs = [{"document_id": "7", "document_name": "Selected.pdf"}, {"document_id": "8", "document_name": "Other accessible.pdf"}]

    AcademicChatService(retriever, model, document_summarizer=summarizer).answer(
        "Summarize this document", document_id="7", available_documents=docs
    )

    assert summarizer.calls[0][0] == "7"


def test_inaccessible_selected_document_is_rejected_before_interpretation():
    retriever, model = RecordingRetriever(), ModelMock()

    answer = AcademicChatService(retriever, model).answer(
        "Summarize this document", document_id="8",
        available_documents=[{"document_id": "7", "document_name": "Owned.pdf"}],
    )

    assert answer.status == AnswerStatus.NOT_FOUND
    assert model.interpretation_calls == []
    assert retriever.calls == []


def test_missing_selected_document_for_whole_document_request_clarifies():
    retriever = RecordingRetriever()
    model = ModelMock(interpretation(
        request_mode="clarification", clarification_needed=True,
        clarification_question="Which uploaded document do you mean?", intent="document_summary",
        analysis_scope="whole_document", retrieval_strategy="document_wide", retrieval_query="",
    ))
    summarizer = RecordingSummarizer()
    answer = AcademicChatService(retriever, model, document_summarizer=summarizer).answer(
        "Summarize the entire document.", available_documents=[{"document_id": "7", "document_name": "Owned.pdf"}]
    )

    assert answer.answer == "Which uploaded document do you mean?"
    assert summarizer.calls == []
    assert retriever.calls == []


def test_model_clarification_stops_before_retrieval_and_answer_generation():
    retriever = RecordingRetriever()
    model = ModelMock(interpretation(
        clarification_needed=True,
        clarification_question="Which of the two uploaded documents do you mean?",
    ))
    answer = AcademicChatService(retriever, model).answer("Analyze the document")
    assert answer.answer == "Which of the two uploaded documents do you mean?"
    assert answer.status == AnswerStatus.NOT_FOUND
    assert answer.evidence == [] and answer.sources == []
    assert retriever.calls == []
    assert model.conversation_calls == [] and model.generation_calls == []


def test_conversational_messages_are_not_matched_by_application_phrase_lists():
    retriever = RecordingRetriever()
    model = ModelMock(interpretation(request_mode="conversation", requires_document_evidence=False, retrieval_query="", retrieval_strategy="none", analysis_scope="none", intent="conversation"))
    AcademicChatService(retriever, model).answer("A novel phrasing the application has never seen before")
    assert len(model.interpretation_calls) == 1
    assert len(model.conversation_calls) == 1
    assert retriever.calls == []
