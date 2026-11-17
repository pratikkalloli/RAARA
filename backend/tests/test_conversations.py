from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.auth.dependencies import get_db
from app.config import settings
from app.database.db import Base, migrate_conversation_schema
from app.database.models import Conversation, ConversationMessage, User
from app.main import app
from app.routes.chat import get_chat_service
from app.services.generator import AnswerStatus, EvidenceItem, GenerationError, SourceItem, StructuredAnswer
from app.services.conversations import ConversationService
from app.services.request_interpreter import RequestInterpretation
from app.services.chat import AcademicChatService
from app.services.security import create_access_token, hash_password


class FakeChatService:
    def __init__(self):
        self.calls = []
        self.histories = []
        self.fail = False

    def answer(self, question, *, top_k=None, metadata_filters=None, prompt_type=None, conversation_history=(), available_documents=(), **kwargs):
        self.calls.append((question, top_k, metadata_filters, prompt_type))
        self.histories.append(list(conversation_history))
        if self.fail:
            raise GenerationError("mocked generation failure")
        return StructuredAnswer(
            answer=f"Synthetic supported answer for: {question}",
            evidence=[EvidenceItem(
                text="Synthetic test evidence; not an official regulation.",
                document="Synthetic Conversation Fixture.pdf",
                page=2,
                section="Synthetic Section",
                passage_id="synthetic-chunk-1",
                document_id="synthetic-doc-1",
                version="1",
                verification_status="verified",
            )],
            sources=[SourceItem(
                document="Synthetic Conversation Fixture.pdf",
                document_id="synthetic-doc-1",
                document_type="test_fixture",
                pages=[2],
                sections=["Synthetic Section"],
                academic_year="2026-2027",
                version="1",
                effective_date="2026-08-01",
                source_type="synthetic_test",
                verification_status="verified",
            )],
            status=AnswerStatus.SUPPORTED,
        )


@pytest.fixture
def conversation_context(tmp_path, monkeypatch) -> Iterator[tuple]:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'conversations.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = factory()
    suffix = uuid4().hex[:8]
    owner = User(
        username=f"owner{suffix}",
        email=f"owner{suffix}@example.edu",
        password_hash=hash_password("synthetic-conversation-test-password"),
        role="student",
    )
    other = User(
        username=f"other{suffix}",
        email=f"other{suffix}@example.edu",
        password_hash=hash_password("synthetic-conversation-test-password"),
        role="student",
    )
    admin = User(
        username=f"admin{suffix}",
        email=f"admin{suffix}@example.edu",
        password_hash=hash_password("synthetic-conversation-test-password"),
        role="admin",
    )
    session.add_all([owner, other, admin])
    session.commit()
    monkeypatch.setattr(settings, "jwt_secret_key", "phase-6c-test-jwt-signing-key-with-32-bytes")
    chat_service = FakeChatService()

    def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_chat_service] = lambda: chat_service
    client = TestClient(app)
    tokens = {
        "owner": create_access_token(owner.id),
        "other": create_access_token(other.id),
        "admin": create_access_token(admin.id),
    }
    yield client, session, owner, other, admin, tokens, chat_service
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_chat_service, None)
    session.close()
    engine.dispose()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_owner_can_rename_conversation_but_other_users_cannot(conversation_context):
    client, session, owner, other, _admin, tokens, _chat_service = conversation_context
    created = client.post("/api/conversations", headers=auth(tokens["owner"]), json={"title": "Old title"})
    assert created.status_code == 201
    conversation_id = created.json()["id"]

    denied = client.patch(
        f"/api/conversations/{conversation_id}",
        headers=auth(tokens["other"]),
        json={"title": "Stolen title"},
    )
    assert denied.status_code == 404

    renamed = client.patch(
        f"/api/conversations/{conversation_id}",
        headers=auth(tokens["owner"]),
        json={"title": "  Attendance follow-up  "},
    )
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "Attendance follow-up"
    assert session.get(Conversation, conversation_id).title == "Attendance follow-up"


@pytest.mark.parametrize("title", ["", "   ", "x" * 161])
def test_conversation_rename_rejects_invalid_titles(conversation_context, title):
    client, _session, _owner, _other, _admin, tokens, _chat_service = conversation_context
    created = client.post("/api/conversations", headers=auth(tokens["owner"]), json={})
    response = client.patch(
        f"/api/conversations/{created.json()['id']}",
        headers=auth(tokens["owner"]),
        json={"title": title},
    )
    assert response.status_code == 422


def create_conversation(client: TestClient, token: str, body: dict | None = None) -> dict:
    response = client.post("/api/conversations", headers=auth(token), json=body or {})
    assert response.status_code == 201, response.text
    return response.json()


def test_conversation_creation_assigns_owner_server_side_and_safe_default_title(conversation_context):
    client, session, owner, _, _, tokens, _ = conversation_context
    response = client.post("/api/conversations", headers=auth(tokens["owner"]), json={})
    assert response.status_code == 201
    payload = response.json()
    assert payload["title"] == "New conversation"
    assert payload["message_count"] == 0
    assert payload["question_count"] == 0
    assert payload["id"] is not None
    conversation = session.get(Conversation, payload["id"])
    assert conversation.user_id == owner.id
    assert "user_id" not in payload


def test_conversation_creation_rejects_client_supplied_owner_and_requires_auth(conversation_context):
    client, _, _, _, _, tokens, _ = conversation_context
    assert client.post("/api/conversations", json={}).status_code == 401
    response = client.post(
        "/api/conversations",
        headers=auth(tokens["owner"]),
        json={"user_id": 999, "title": "Private"},
    )
    assert response.status_code == 422
    titled = create_conversation(client, tokens["owner"], {"title": "  Attendance questions  "})
    assert titled["title"] == "Attendance questions"


def test_conversation_listing_is_owner_scoped_counts_messages_and_sorts_updated(conversation_context):
    client, session, owner, _, _, tokens, _ = conversation_context
    first = create_conversation(client, tokens["owner"])
    second = create_conversation(client, tokens["owner"])
    foreign = create_conversation(client, tokens["other"])
    session.add_all([
        ConversationMessage(conversation_id=first["id"], role="user", content="first question"),
        ConversationMessage(conversation_id=first["id"], role="assistant", content="first answer"),
    ])
    session.commit()
    first_record = session.get(Conversation, first["id"])
    from datetime import datetime, timedelta, timezone

    first_record.updated_at = datetime.now(timezone.utc) + timedelta(seconds=10)
    session.commit()

    response = client.get("/api/conversations", headers=auth(tokens["owner"]))
    assert response.status_code == 200
    entries = response.json()
    assert [entry["id"] for entry in entries] == [first["id"], second["id"]]
    assert entries[0]["message_count"] == 2
    assert entries[0]["question_count"] == 1
    assert entries[1]["question_count"] == 0
    assert all(entry["id"] != foreign["id"] for entry in entries)


def test_conversation_detail_preserves_order_and_structured_citations(conversation_context):
    client, session, _, _, _, tokens, _ = conversation_context
    conversation = create_conversation(client, tokens["owner"])
    for question in ("First synthetic question", "Second synthetic question"):
        response = client.post(
            "/api/chat",
            headers=auth(tokens["owner"]),
            json={"question": question, "conversation_id": conversation["id"]},
        )
        assert response.status_code == 200

    detail = client.get(f"/api/conversations/{conversation['id']}", headers=auth(tokens["owner"]))
    assert detail.status_code == 200
    body = detail.json()
    assert body["message_count"] == 4
    assert body["question_count"] == 2
    assert [message["role"] for message in body["messages"]] == ["user", "assistant", "user", "assistant"]
    assert [message["content"] for message in body["messages"] if message["role"] == "user"] == [
        "First synthetic question",
        "Second synthetic question",
    ]
    assistant = body["messages"][1]
    assert assistant["structured_response"]["status"] == "SUPPORTED"
    assert assistant["structured_response"]["evidence"][0]["page"] == 2
    assert assistant["structured_response"]["sources"][0]["verification_status"] == "verified"
    assert session.query(ConversationMessage).filter_by(conversation_id=conversation["id"]).count() == 4


def test_chat_with_conversation_persists_one_atomic_pair_and_idempotent_retry(conversation_context):
    client, session, _, _, _, tokens, chat_service = conversation_context
    conversation = create_conversation(client, tokens["owner"])
    request = {
        "question": "A synthetic chat question",
        "conversation_id": conversation["id"],
        "idempotency_key": "8d7d7d31-9b72-45db-9f68-8ca4f510d70c",
        "prompt_type": "B",
    }
    first = client.post("/api/chat", headers=auth(tokens["owner"]), json=request)
    retry = client.post("/api/chat", headers=auth(tokens["owner"]), json=request)
    assert first.status_code == retry.status_code == 200
    assert first.json() == retry.json()
    assert len(chat_service.calls) == 1
    assert session.query(ConversationMessage).filter_by(conversation_id=conversation["id"]).count() == 2
    assert chat_service.histories[-1] == []

    mismatched = {**request, "question": "A different question"}
    assert client.post("/api/chat", headers=auth(tokens["owner"]), json=mismatched).status_code == 409
    assert session.query(ConversationMessage).filter_by(conversation_id=conversation["id"]).count() == 2


def test_chat_without_conversation_remains_backward_compatible_and_does_not_persist(conversation_context):
    client, session, _, _, _, tokens, chat_service = conversation_context
    response = client.post("/api/chat", headers=auth(tokens["owner"]), json={"question": "No history requested"})
    assert response.status_code == 200
    assert set(response.json()) == {"answer", "evidence", "sources", "status"}
    assert chat_service.calls[-1][0] == "No history requested"
    assert session.query(Conversation).count() == 0
    assert session.query(ConversationMessage).count() == 0


@pytest.mark.parametrize("prompt_type", ["A", "B", "C"])
def test_greeting_is_persisted_without_retrieval_or_generation(conversation_context, prompt_type):
    client, session, _owner, _other, _admin, tokens, _ = conversation_context

    class ConversationOnlyModel:
        def interpret_request(self, question, **kwargs):
            return RequestInterpretation(
                request_mode="conversation",
                intent="conversation", requires_document_evidence=False, target_document_id=None,
                retrieval_query="", retrieval_strategy="none", retrieval_limit=1, requested_items=None,
                response_format="natural", analysis_scope="none", clarification_needed=False,
                clarification_question=None, page_number=None,
            )

        def retrieve(self, *_args, **_kwargs):
            raise AssertionError("Conversational turns must not retrieve")

        def generate(self, *_args, **_kwargs):
            raise AssertionError("Conversational turns must not generate an evidence answer")

        def generate_conversational(self, question, **kwargs):
            return StructuredAnswer(
                answer="Hello. I can help with your academic documents.", evidence=[], sources=[],
                status=AnswerStatus.CONVERSATIONAL,
            )

    app.dependency_overrides[get_chat_service] = lambda: AcademicChatService(
        ConversationOnlyModel(), ConversationOnlyModel()
    )
    conversation = create_conversation(client, tokens["owner"])
    response = client.post(
        "/api/chat",
        headers=auth(tokens["owner"]),
        json={
            "question": "hello",
            "prompt_type": prompt_type,
            "conversation_id": conversation["id"],
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "CONVERSATIONAL"
    assert response.json()["evidence"] == []
    assert response.json()["sources"] == []
    assert response.json()["answer"] == "Hello. I can help with your academic documents."
    details = client.get(
        f"/api/conversations/{conversation['id']}",
        headers=auth(tokens["owner"]),
    ).json()
    assert details["message_count"] == 2
    assert [message["content"] for message in details["messages"] if message["role"] == "user"] == ["hello"]
    assert details["messages"][1]["structured_response"]["status"] == "CONVERSATIONAL"
    assert session.query(ConversationMessage).filter_by(conversation_id=conversation["id"]).count() == 2


def test_followup_receives_bounded_owned_conversation_context(conversation_context):
    client, _, _, _, _, tokens, chat_service = conversation_context
    conversation = create_conversation(client, tokens["owner"])
    headers = auth(tokens["owner"])
    first = client.post("/api/chat", headers=headers, json={
        "question": "What does the synthetic attendance rule say?",
        "conversation_id": conversation["id"],
    })
    assert first.status_code == 200
    second = client.post("/api/chat", headers=headers, json={
        "question": "Explain that again.",
        "conversation_id": conversation["id"],
    })
    assert second.status_code == 200
    third = client.post("/api/chat", headers=headers, json={
        "question": "Give one more detail.",
        "conversation_id": conversation["id"],
    })
    assert third.status_code == 200
    assert chat_service.histories[-1] == [
        {"role": "user", "content": "What does the synthetic attendance rule say?"},
        {"role": "assistant", "content": "Synthetic supported answer for: What does the synthetic attendance rule say?",
         "answer_status": "SUPPORTED", "evidence_count": 1},
        {"role": "user", "content": "Explain that again."},
        {"role": "assistant", "content": "Synthetic supported answer for: Explain that again.",
         "answer_status": "SUPPORTED", "evidence_count": 1},
    ]


def test_recent_context_preserves_abstention_status_without_including_structured_evidence_text(conversation_context):
    client, session, _, _, _, tokens, _ = conversation_context
    conversation = create_conversation(client, tokens["owner"])
    session.add_all([
        ConversationMessage(conversation_id=conversation["id"], role="user", content="What does ISA mean?"),
        ConversationMessage(
            conversation_id=conversation["id"], role="assistant",
            content="I could not support an answer from available documents.",
            structured_response={"status": "NOT_FOUND", "evidence": [], "sources": []},
        ),
    ])
    session.commit()

    context = ConversationService(session).recent_context(conversation["id"])

    assert context == [
        {"role": "user", "content": "What does ISA mean?"},
        {"role": "assistant", "content": "I could not support an answer from available documents.",
         "answer_status": "NOT_FOUND", "evidence_count": 0},
    ]


def test_non_owner_and_admin_cannot_read_another_users_conversation(conversation_context):
    client, _, _, _, _, tokens, _ = conversation_context
    conversation = create_conversation(client, tokens["owner"])
    assert client.get(f"/api/conversations/{conversation['id']}", headers=auth(tokens["other"])).status_code == 404
    assert client.get(f"/api/conversations/{conversation['id']}", headers=auth(tokens["admin"])).status_code == 404
    assert client.get("/api/conversations/999999", headers=auth(tokens["owner"])).status_code == 404


def test_chat_checks_ownership_before_running_retrieval_or_generation(conversation_context):
    client, _, _, _, _, tokens, chat_service = conversation_context
    conversation = create_conversation(client, tokens["owner"])
    response = client.post(
        "/api/chat",
        headers=auth(tokens["other"]),
        json={"question": "Must not be processed", "conversation_id": conversation["id"]},
    )
    assert response.status_code == 404
    assert chat_service.calls == []


def test_failed_generation_does_not_persist_messages(conversation_context):
    client, session, _, _, _, tokens, chat_service = conversation_context
    conversation = create_conversation(client, tokens["owner"])
    chat_service.fail = True
    response = client.post(
        "/api/chat",
        headers=auth(tokens["owner"]),
        json={"question": "This generation will fail", "conversation_id": conversation["id"]},
    )
    assert response.status_code == 503
    assert session.query(ConversationMessage).filter_by(conversation_id=conversation["id"]).count() == 0


def test_conversation_delete_is_owned_and_removes_messages_transactionally(conversation_context):
    client, session, _, _, _, tokens, _ = conversation_context
    conversation = create_conversation(client, tokens["owner"])
    client.post(
        "/api/chat",
        headers=auth(tokens["owner"]),
        json={"question": "Synthetic question", "conversation_id": conversation["id"]},
    )
    assert client.delete(f"/api/conversations/{conversation['id']}", headers=auth(tokens["other"])).status_code == 404

    def fail_before_commit(current_session):
        if current_session.info.pop("fail_next_commit", False):
            raise SQLAlchemyError("synthetic commit failure")

    event.listen(session, "before_commit", fail_before_commit)
    session.info["fail_next_commit"] = True
    failure = client.delete(f"/api/conversations/{conversation['id']}", headers=auth(tokens["owner"]))
    event.remove(session, "before_commit", fail_before_commit)
    assert failure.status_code == 503
    assert session.get(Conversation, conversation["id"]) is not None
    assert session.query(ConversationMessage).filter_by(conversation_id=conversation["id"]).count() == 2

    removed = client.delete(f"/api/conversations/{conversation['id']}", headers=auth(tokens["owner"]))
    assert removed.status_code == 204
    assert session.get(Conversation, conversation["id"]) is None
    assert session.query(ConversationMessage).filter_by(conversation_id=conversation["id"]).count() == 0


def test_legacy_orphan_messages_survive_migration_and_are_not_exposed(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy-messages.db'}")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE conversation_messages (id INTEGER PRIMARY KEY, role VARCHAR(32) NOT NULL, "
            "content TEXT NOT NULL, created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
        connection.exec_driver_sql(
            "INSERT INTO conversation_messages (id, role, content) VALUES (41, 'user', 'legacy orphan message')"
        )
    Base.metadata.create_all(engine)
    migrate_conversation_schema(engine)
    migrate_conversation_schema(engine)
    with engine.connect() as connection:
        row = connection.exec_driver_sql(
            "SELECT id, role, content, conversation_id, structured_response, idempotency_key "
            "FROM conversation_messages WHERE id=41"
        ).one()
        assert row == (41, "user", "legacy orphan message", None, None, None)
    with pytest.raises(Exception, match="conversation message role"):
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "INSERT INTO conversation_messages (role, content) VALUES ('system', 'must be rejected')"
            )
    engine.dispose()
