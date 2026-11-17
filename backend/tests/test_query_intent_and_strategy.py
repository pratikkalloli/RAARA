from app.services.chat import AcademicChatService
from app.services.generator import AnswerStatus, StructuredAnswer
from app.services.request_interpreter import RequestInterpretation
from app.services.retriever import RetrievedPassage, RetrievalResult


def interpreted(**overrides):
    values = {
        "request_mode": "document_evidence",
        "intent": "academic_question", "requires_document_evidence": True,
        "target_document_id": None, "retrieval_query": "meaning-based query",
        "retrieval_strategy": "focused", "retrieval_limit": 5, "requested_items": None,
        "response_format": "clear explanation", "analysis_scope": "retrieved_passages",
        "clarification_needed": False, "clarification_question": None, "page_number": None,
    }
    values.update(overrides)
    if "request_mode" not in overrides:
        if values["clarification_needed"]:
            values["request_mode"] = "clarification"
        elif not values["requires_document_evidence"]:
            values["request_mode"] = "conversation"
    return RequestInterpretation(**values)


class RecordingRetriever:
    def __init__(self):
        self.calls = []

    def retrieve(self, question, **kwargs):
        self.calls.append((question, kwargs))
        # These strategy tests assert that the academic path reaches answer
        # generation, so return a citation-ready synthetic passage rather than
        # an empty result (which must correctly short-circuit to abstention).
        passage = RetrievedPassage(
            id="synthetic-passage-1",
            text="Synthetic test evidence for request-strategy coverage.",
            metadata={
                "document_id": "synthetic-doc-1",
                "document_name": "Synthetic test document.pdf",
                "page_number": 1,
                "section": "Synthetic test section",
                "verification_status": "unverified",
                "source_type": "synthetic_test",
            },
            cosine_distance=0.1,
            relevance_score=0.9,
        )
        return RetrievalResult(question, (passage,), kwargs.get("top_k", 5), 0.35)


class RecordingModel:
    def __init__(self, interpretation):
        self.interpretation = interpretation
        self.generated = []

    def interpret_request(self, question, **kwargs):
        return self.interpretation

    def generate(self, retrieval, **kwargs):
        self.generated.append((retrieval, kwargs))
        return StructuredAnswer(answer="The synthetic evidence is insufficient.", evidence=[], sources=[], status=AnswerStatus.NOT_FOUND)

    def generate_conversational(self, question, **kwargs):
        return StructuredAnswer(answer="Mock conversational result.", evidence=[], sources=[], status=AnswerStatus.CONVERSATIONAL)


class FakeSummarizer:
    def __init__(self):
        self.calls = []

    def summarize(self, document_id, question, **kwargs):
        self.calls.append((document_id, question, kwargs))
        return StructuredAnswer(answer="Synthetic summary only.", evidence=[], sources=[], status=AnswerStatus.NOT_FOUND)


def test_model_output_selects_page_filter_and_preserves_original_question():
    retriever = RecordingRetriever()
    model = RecordingModel(interpreted(
        retrieval_query="section requirements on page five", retrieval_strategy="page_specific", page_number=5,
        retrieval_limit=8,
    ))
    AcademicChatService(retriever, model).answer("Could you walk through the fifth page?", metadata_filters={"document_id": "42"})
    query, options = retriever.calls[0]
    assert query == "section requirements on page five"
    assert options["metadata_filters"] == {"document_id": "42", "page_number": 5}
    assert options["top_k"] == 8
    assert options["allow_multiple_documents"] is False
    assert model.generated[0][0].question == "Could you walk through the fifth page?"


def test_model_output_selects_comparison_and_bounded_retrieval():
    retriever = RecordingRetriever()
    model = RecordingModel(interpreted(
        retrieval_query="compare registration and withdrawal provisions", retrieval_strategy="comparison", retrieval_limit=11,
    ))
    AcademicChatService(retriever, model).answer("How do those two policies differ?")
    assert retriever.calls[0][1]["top_k"] == 11
    assert retriever.calls[0][1]["allow_multiple_documents"] is True


def test_model_selects_broad_information_retrieval_depth():
    retriever = RecordingRetriever()
    model = RecordingModel(interpreted(
        intent="information_extraction", retrieval_strategy="broad", retrieval_limit=23,
        response_format="organized list of dated items",
    ))
    AcademicChatService(retriever, model).answer("Pull together the dates I should know")
    assert retriever.calls[0][1]["top_k"] == 23
    assert model.generated[0][1]["response_format"] == "organized list of dated items"


def test_whole_document_analysis_uses_hierarchical_summarizer():
    retriever, model, summarizer = RecordingRetriever(), RecordingModel(interpreted(
        intent="document_summary", target_document_id="42", retrieval_strategy="document_wide",
        analysis_scope="whole_document", retrieval_query="", requested_items=10,
    )), FakeSummarizer()
    service = AcademicChatService(retriever, model, document_summarizer=summarizer)
    service.answer("Give me a comprehensive overview", available_documents=[{"document_id": "42", "document_name": "Owned.pdf"}])
    assert summarizer.calls == [("42", "Give me a comprehensive overview", {"requested_points": 10, "prompt_type": "C"})]
    assert retriever.calls == []


def test_follow_up_context_reaches_interpreter_and_generator_gets_current_question():
    retriever = RecordingRetriever()
    model = RecordingModel(interpreted(retrieval_query="clarify previously discussed synthetic rule"))
    history = [{"role": "user", "content": "What does the synthetic rule state?"}]
    AcademicChatService(retriever, model).answer("Can you expand on that?", conversation_history=history)
    assert retriever.calls[0][0] == "clarify previously discussed synthetic rule"
    assert model.generated[0][0].question == "Can you expand on that?"
