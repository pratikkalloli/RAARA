from collections import Counter
import asyncio
from types import SimpleNamespace
import json

import pytest

from app.main import app
from app.services.security import TokenConfigurationError, validate_jwt_secret
from app.services.chat import AcademicChatService
from app.services.document_summarizer import DocumentSummarizer
from app.services.citation_verifier import CitationVerifier
from app.services.generator import GroqAnswerGenerator
from app.services.ingestion import DocumentIngestionService
from app.services.retriever import Retriever
from app.services.vector_store import ChromaVectorStore
import app.main as main_module


def test_conversation_routes_are_registered_once():
    included = [
        route.original_router
        for route in app.routes
        if getattr(getattr(route, "original_router", None), "prefix", None) == "/api/conversations"
    ]
    assert len(included) == 1
    signatures = Counter(
        (included[0].prefix + route.path, method)
        for route in included[0].routes
        for method in route.methods
    )
    assert signatures
    assert all(count == 1 for count in signatures.values())


@pytest.mark.parametrize(
    ("secret", "message"),
    [
        (None, "missing"),
        ("short-secret", "too short"),
        ("CHANGE_ME_WITH_A_RANDOM_SECRET_OF_AT_LEAST_32_BYTES", "placeholder"),
    ],
)
def test_jwt_configuration_validation_is_actionable(secret, message, monkeypatch):
    if secret is None:
        from app.config import settings

        monkeypatch.setattr(settings, "jwt_secret_key", None)
        validate = lambda: validate_jwt_secret()
    else:
        validate = lambda: validate_jwt_secret(secret)
    with pytest.raises(TokenConfigurationError, match=message):
        validate()


def test_jwt_configuration_accepts_random_secret_material():
    validate_jwt_secret("test-only-secure-random-material-32-bytes")


def test_invalid_startup_secret_fails_before_database_migrations(monkeypatch):
    calls = []
    monkeypatch.setattr(main_module.settings, "jwt_secret_key", None)
    monkeypatch.setattr(main_module.Base.metadata, "create_all", lambda **kwargs: calls.append("create"))
    monkeypatch.setattr(main_module, "migrate_document_schema", lambda: calls.append("documents"))
    monkeypatch.setattr(main_module, "migrate_user_schema", lambda: calls.append("users"))
    monkeypatch.setattr(main_module, "migrate_conversation_schema", lambda: calls.append("conversations"))

    async def enter_lifespan():
        async with main_module.lifespan(main_module.app):
            pass

    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY is missing"):
        asyncio.run(enter_lifespan())
    assert calls == []


def test_synthetic_pdf_ingestion_retrieval_and_mocked_answer_are_integrated(db_session, tmp_path, synthetic_pdf):
    class FixedEmbedder:
        def embed_texts(self, texts):
            return [[1.0, 0.0, 0.0] for _ in texts]

    store = ChromaVectorStore(tmp_path / "isolated-chroma", collection_name="audit_e2e")
    document = DocumentIngestionService(
        db_session,
        embedder=FixedEmbedder(),
        vector_store=store,
        storage_dir=tmp_path / "uploads",
    ).ingest_pdf(
        synthetic_pdf,
        filename="SYNTHETIC_NOT_OFFICIAL.pdf",
        document_name="Synthetic test fixture, not an official regulation",
        source_type="synthetic_test",
    )
    assert document.verification_status == "unverified"

    class MockModels:
        def retrieve(self, model):
            return SimpleNamespace(id=model)

    class MockResponses:
        def __init__(self):
            self.calls = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            if kwargs.get("text", {}).get("format", {}).get("name") == "raara_request_interpretation":
                return SimpleNamespace(output_text=json.dumps({
                    "request_mode": "document_evidence",
                    "intent": "document_summary", "requires_document_evidence": True,
                    "target_document_id": None, "retrieval_query": "", "retrieval_strategy": "document_wide",
                    "retrieval_limit": 5, "requested_items": 8, "response_format": "numbered summary",
                    "analysis_scope": "whole_document", "clarification_needed": False,
                    "clarification_question": None, "page_number": None,
                }))
            data = json.loads(kwargs["input"])
            assert data["passages"]
            return SimpleNamespace(output_text=json.dumps({
                "answer": "The synthetic document describes attendance-related requirements.",
                "evidence_ids": [data["passages"][0]["passage_id"]],
                "status": "SUPPORTED",
            }))

    responses = MockResponses()
    generator = GroqAnswerGenerator(model="mock-model", client=SimpleNamespace(models=MockModels(), responses=responses))
    service = AcademicChatService(
        Retriever(FixedEmbedder(), store, relevance_threshold=0.35),
        generator,
        CitationVerifier(),
        DocumentSummarizer(store, generator),
    )
    answer = service.answer(
        "Summarize the synthetic attendance document.",
        document_id=document.id,
        available_documents=[{
            "document_id": str(document.id),
            "document_name": document.document_name,
            "document_type": document.document_type,
            "source_type": document.source_type,
            "verification_status": document.verification_status,
        }],
    )
    assert answer.evidence[0].document == document.document_name
    assert answer.evidence[0].page >= 1
    assert answer.evidence[0].verification_status == "unverified"
    assert len(responses.calls) == 2
