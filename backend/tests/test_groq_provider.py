import json
from types import ModuleType, SimpleNamespace

import pytest

from app.config import settings
from app.services.generator import (
    GenerationError,
    GroqAnswerGenerator,
    ModelAuthenticationError,
    ModelAccessError,
    ModelPermissionError,
    ModelRateLimitError,
    ModelUnavailableError,
    GroqRequestError,
    StructuredOutputSchemaError,
    _ABSTENTION_SCHEMA,
    _CONVERSATION_SCHEMA,
    _NUMERICAL_REVIEW_SCHEMA,
    _OUTPUT_SCHEMA,
    _GroqResponsesAdapter,
    _translate_groq_error,
    create_answer_generator,
    supports_strict_json_schema,
    validate_strict_json_schema,
)
from app.services.request_interpreter import REQUEST_INTERPRETATION_SCHEMA
from app.services.retriever import RetrievalResult, RetrievedPassage


def _retrieval():
    passage = RetrievedPassage(
        id="synthetic-passage-1",
        text="Synthetic test guidance: ISA is 40% and ESA is 60%.",
        metadata={
            "document_id": "41", "document_name": "Synthetic Guide.pdf",
            "document_type": "synthetic_test", "page_number": 2,
            "section": "Assessment", "academic_year": "", "version": "1",
            "effective_date": "", "source_type": "synthetic_test",
            "verification_status": "unverified",
        },
        cosine_distance=0.1,
        relevance_score=0.9,
    )
    return RetrievalResult("What are the assessment allocations?", (passage,), 5, 0.35)


class FakeCompletionAPI:
    def __init__(self, payload=None, error=None):
        self.payload = payload or {
            "answer": "The synthetic guide states ISA 40% and ESA 60%.",
            "evidence_ids": ["P1"],
            "status": "SUPPORTED",
        }
        self.error = error
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(self.payload)))],
            usage=SimpleNamespace(prompt_tokens=91, completion_tokens=24),
        )


def _fake_groq_client(payload=None, error=None):
    api = FakeCompletionAPI(payload, error)
    client = SimpleNamespace(chat=SimpleNamespace(completions=api))
    return client, api


class FakeStatusError(Exception):
    def __init__(self, status_code, body=None):
        super().__init__("safe mock provider error")
        self.status_code = status_code
        self.body = body


def test_factory_selects_only_groq_and_validates_config(monkeypatch):
    monkeypatch.setattr(settings, "ai_provider", "groq")
    monkeypatch.setattr(settings, "groq_chat_model", "openai/gpt-oss-20b")
    assert isinstance(create_answer_generator(), GroqAnswerGenerator)
    for retired_provider in ("gemini", "openai"):
        monkeypatch.setattr(settings, "ai_provider", retired_provider)
        with pytest.raises(ModelAccessError, match="must be 'groq'"):
            create_answer_generator()


def test_groq_chat_request_uses_system_user_messages_and_strict_json_schema():
    client, api = _fake_groq_client()
    answer = GroqAnswerGenerator(model="mock-groq-model", client=client).generate(_retrieval())

    request = api.calls[0]
    assert request["model"] == "mock-groq-model"
    assert [message["role"] for message in request["messages"]] == ["system", "user"]
    assert request["response_format"]["type"] == "json_schema"
    assert request["response_format"]["json_schema"]["strict"] is True
    assert request["response_format"]["json_schema"]["schema"]["required"] == ["answer", "evidence_ids", "status"]
    assert "stream" not in request
    assert "tools" not in request
    assert answer.evidence[0].document == "Synthetic Guide.pdf"
    assert answer.evidence[0].page == 2
    assert "unverified" in answer.answer.casefold()


def test_groq_usage_metadata_is_mapped_to_existing_generation_schema():
    client, api = _fake_groq_client()
    record = GroqAnswerGenerator(model="mock-groq-model", client=client).generate_with_usage(_retrieval())
    assert record.input_tokens == 91
    assert record.output_tokens == 24
    assert record.answer.status.value == "SUPPORTED"


def test_missing_groq_key_fails_without_network_or_secret_disclosure(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", None)
    generator = GroqAnswerGenerator(model="mock-groq-model", api_key="")
    with pytest.raises(ModelAccessError, match="GROQ_API_KEY") as error:
        generator.generate(_retrieval())
    assert "secret" not in str(error.value).casefold()


@pytest.mark.parametrize(
    ("status", "expected", "message"),
    [
        (401, ModelAuthenticationError, "HTTP 401"),
        (403, ModelPermissionError, "HTTP 403"),
        (404, ModelUnavailableError, "GROQ_CHAT_MODEL"),
        (429, ModelRateLimitError, "rate limit"),
        (400, GroqRequestError, "HTTP 400"),
    ],
)
def test_groq_status_errors_are_actionable_and_sanitized(status, expected, message):
    error = FakeStatusError(status)
    translated = _translate_groq_error(error, "mock-groq-model", "test")
    assert isinstance(translated, expected)
    assert message.casefold() in str(translated).casefold()
    assert "safe mock" not in str(translated)


def test_groq_400_preserves_provider_schema_error_instead_of_claiming_model_unsupported(caplog):
    error = FakeStatusError(400, {"error": {"code": "invalid_json_schema", "message": "schema path $.properties.answer is invalid"}})

    translated = _translate_groq_error(error, "openai/gpt-oss-20b", "interpret the request")

    assert isinstance(translated, GroqRequestError)
    assert "HTTP 400" in str(translated)
    assert "invalid_json_schema" in str(translated)
    assert "schema path $.properties.answer is invalid" in str(translated)
    assert "supports JSON Schema" not in str(translated)
    assert "openai/gpt-oss-20b" in caplog.text


def test_groq_strict_schema_validator_accepts_all_application_schemas():
    for schema in (
        REQUEST_INTERPRETATION_SCHEMA,
        _OUTPUT_SCHEMA,
        _CONVERSATION_SCHEMA,
        _ABSTENTION_SCHEMA,
        _NUMERICAL_REVIEW_SCHEMA,
    ):
        validate_strict_json_schema(schema)


@pytest.mark.parametrize(
    "schema",
    [
        {"type": "object", "properties": {"answer": {"type": "string"}}, "required": [], "additionalProperties": False},
        {"type": "object", "properties": {"answer": {"type": "string"}}, "required": ["answer"]},
        {"type": "object", "properties": {"answer": {"type": "object", "properties": {"x": {"type": "string"}}, "required": ["x"]}}, "required": ["answer"], "additionalProperties": False},
    ],
)
def test_invalid_strict_schema_is_rejected_before_api_call(schema):
    client, api = _fake_groq_client()
    adapter = _GroqResponsesAdapter(client)

    with pytest.raises(StructuredOutputSchemaError):
        adapter.create(
            model="openai/gpt-oss-20b",
            instructions="instructions",
            input="safe test input",
            text={"format": {"type": "json_schema", "name": "invalid_schema_test", "schema": schema}},
            max_output_tokens=100,
        )

    assert api.calls == []


def test_strict_schema_capability_recognizes_gpt_oss_and_rejects_unsupported_model_without_request():
    assert supports_strict_json_schema("openai/gpt-oss-20b")
    unsupported = GroqAnswerGenerator(model="some/unsupported-model", api_key="fake-test-key")
    with pytest.raises(ModelUnavailableError, match="not listed as supporting strict JSON Schema"):
        unsupported.generate(_retrieval())


def test_configured_gpt_oss_model_is_sent_unchanged_to_groq():
    client, api = _fake_groq_client()
    GroqAnswerGenerator(model="openai/gpt-oss-20b", client=client).generate(_retrieval())

    assert api.calls[0]["model"] == "openai/gpt-oss-20b"


def test_groq_rate_limit_does_not_retry_auth_errors_or_leak_error_body():
    client, api = _fake_groq_client(error=FakeStatusError(429))
    generator = GroqAnswerGenerator(model="mock-groq-model", client=client)
    with pytest.raises(GenerationError, match="rate limit") as error:
        generator.generate(_retrieval())
    assert len(api.calls) == 1
    assert "safe mock" not in str(error.value)


def test_groq_sdk_client_is_configured_without_making_a_request(monkeypatch):
    calls = []

    class FakeGroq:
        def __init__(self, **kwargs):
            calls.append(kwargs)
            self.chat = SimpleNamespace(completions=FakeCompletionAPI())

    module = ModuleType("groq")
    module.Groq = FakeGroq
    monkeypatch.setitem(__import__("sys").modules, "groq", module)
    monkeypatch.setattr(settings, "groq_api_key", "not-a-real-key-used-only-for-this-test")
    monkeypatch.setattr(settings, "groq_chat_model", "mock-groq-model")

    generator = GroqAnswerGenerator()
    _ = generator.client

    assert calls == [{
        "api_key": "not-a-real-key-used-only-for-this-test",
        "timeout": settings.groq_request_timeout_seconds,
        "max_retries": settings.groq_max_retries,
    }]


def test_backend_dotenv_loads_groq_key_name_and_normalizes_whitespace(tmp_path, monkeypatch):
    from app.config import Settings

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.delenv("GROQ_CHAT_MODEL", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    (tmp_path / ".env").write_text(
        'AI_PROVIDER=groq\nGROQ_CHAT_MODEL=mock-groq-model\nGROQ_API_KEY = "  gsk_test_only  "\n',
        encoding="utf-8",
    )

    loaded = Settings()

    assert loaded.ai_provider == "groq"
    assert loaded.active_chat_model == "mock-groq-model"
    assert loaded.active_api_key == "gsk_test_only"


def test_successful_sdk_response_logs_authentication_without_exposing_key(monkeypatch, caplog):
    caplog.set_level("INFO")
    calls = []

    class FakeGroq:
        def __init__(self, **kwargs):
            calls.append(kwargs)
            self.chat = SimpleNamespace(completions=FakeCompletionAPI())

    module = ModuleType("groq")
    module.Groq = FakeGroq
    monkeypatch.setitem(__import__("sys").modules, "groq", module)
    monkeypatch.setattr(settings, "groq_api_key", "gsk_test_only_secret")
    monkeypatch.setattr(settings, "groq_chat_model", "openai/gpt-oss-20b")

    answer = GroqAnswerGenerator().generate(_retrieval())

    assert answer.status.value == "SUPPORTED"
    assert calls[0]["api_key"] == "gsk_test_only_secret"
    assert "Groq authentication succeeded (key_configured=True)" in caplog.text
    assert "model=openai/gpt-oss-20b" in caplog.text
    assert "gsk_test_only_secret" not in caplog.text
