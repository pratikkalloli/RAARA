import json
from types import SimpleNamespace

from app.evaluation.experiments import PromptExperimentRunner
from app.prompting.system_prompt import PromptType
from app.services.generator import GroqAnswerGenerator, StructuredAnswer
from app.services.retriever import RetrievalResult, RetrievedPassage


def make_passage(identifier, text, page, status="unverified"):
    return RetrievedPassage(
        id=identifier,
        text=text,
        metadata={
            "document_id": identifier,
            "document_name": "Synthetic Experiment Handbook.pdf",
            "document_type": "synthetic_test",
            "page_number": page,
            "section": "Synthetic test section",
            "academic_year": "2026-2027",
            "version": "1",
            "effective_date": "",
            "source_type": "synthetic_test",
            "verification_status": status,
        },
        cosine_distance=0.1,
        relevance_score=0.9,
    )


class FixedRetriever:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def retrieve(self, question, *, top_k=None, metadata_filters=None):
        self.calls.append((question, top_k, metadata_filters))
        return self.result


class MockModels:
    def __init__(self):
        self.calls = []

    def retrieve(self, model):
        self.calls.append(model)
        return SimpleNamespace(id=model)


class MockResponses:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            output_text=json.dumps({
                "answer": "The retrieved synthetic passage supports this answer.",
                "evidence_ids": ["P1"],
                "status": "SUPPORTED",
            }),
            usage=SimpleNamespace(input_tokens=128, output_tokens=24),
        )


def test_experiment_retrieves_once_and_keeps_every_other_input_identical():
    retrieval = RetrievalResult(
        question="What is in the synthetic test handbook?",
        passages=(
            make_passage("chunk-1", "Synthetic test passage one.", 1),
            make_passage("chunk-2", "Synthetic test passage two.", 2),
        ),
        top_k=5,
        relevance_threshold=0.35,
    )
    retriever = FixedRetriever(retrieval)
    models = MockModels()
    responses = MockResponses()
    model_name = "mock-configured-model"
    generator = GroqAnswerGenerator(model=model_name, client=SimpleNamespace(models=models, responses=responses))

    comparison = PromptExperimentRunner(retriever, generator).run(retrieval.question)

    assert len(retriever.calls) == 1
    assert len(responses.calls) == 3
    assert [item.prompt_type for item in comparison.experiments] == [PromptType.A, PromptType.B, PromptType.C]
    assert all(item.question == retrieval.question for item in comparison.experiments)
    assert all(item.retrieved_passage_ids == ["chunk-1", "chunk-2"] for item in comparison.experiments)
    assert len({item.retrieved_context_hash for item in comparison.experiments}) == 1
    assert len({json.dumps(json.loads(call["input"]), sort_keys=True) for call in responses.calls}) == 1
    assert len({call["model"] for call in responses.calls}) == 1
    assert {call["model"] for call in responses.calls} == {model_name}
    assert len({json.dumps(call["text"], sort_keys=True) for call in responses.calls}) == 1
    assert len({call["instructions"] for call in responses.calls}) == 3
    assert models.calls == [model_name]


def test_experiment_records_prompt_config_model_latency_and_usage():
    retrieval = RetrievalResult(
        question="What is in the synthetic test handbook?",
        passages=(make_passage("chunk-1", "Synthetic test passage.", 1),),
        top_k=5,
        relevance_threshold=0.35,
    )
    models = MockModels()
    responses = MockResponses()
    generator = GroqAnswerGenerator(
        model="mock-configured-model",
        client=SimpleNamespace(models=models, responses=responses),
    )

    comparison = PromptExperimentRunner(FixedRetriever(retrieval), generator).run(retrieval.question)

    assert comparison.model == "mock-configured-model"
    assert comparison.retrieval_latency_ms >= 0
    for experiment in comparison.experiments:
        assert experiment.model == comparison.model
        assert experiment.prompt_name
        assert experiment.system_instructions
        assert experiment.generation_latency_ms >= 0
        assert experiment.input_tokens == 128
        assert experiment.output_tokens == 24
        assert isinstance(experiment.response, StructuredAnswer)
        assert experiment.response.evidence[0].document == "Synthetic Experiment Handbook.pdf"
