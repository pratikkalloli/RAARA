from fastapi.testclient import TestClient
import pytest
from fastapi import HTTPException

from app.main import app
from app.prompting.system_prompt import PromptType
from app.auth.dependencies import get_current_user
from app.auth.dependencies import get_db
from app.database.models import Document, User
from app.routes.chat import ChatRequest, chat as chat_route, get_chat_service
from app.services.generator import AnswerStatus, EvidenceItem, SourceItem, StructuredAnswer
from app.services.conversations import ConversationService


class FixedChatService:
    def __init__(self):
        self.calls = []

    def answer(self, question, *, top_k=None, metadata_filters=None, prompt_type=PromptType.C, document_id=None, available_documents=(), **kwargs):
        call = (question, top_k, metadata_filters, prompt_type)
        self.calls.append(call + (document_id,) if document_id is not None else call)
        return StructuredAnswer(
            answer="The retrieved synthetic test passage describes the threshold.",
            evidence=[EvidenceItem(
                text="Synthetic test content; not an official regulation.",
                document="Synthetic Test Handbook.pdf",
                page=2,
                section="Synthetic Attendance Test",
                document_id="5",
                version="1",
                verification_status="unverified",
            )],
            sources=[SourceItem(
                document="Synthetic Test Handbook.pdf",
                document_id="5",
                document_type="test_fixture",
                pages=[2],
                sections=["Synthetic Attendance Test"],
                academic_year="2026-2027",
                version="1",
                source_type="synthetic_test",
                verification_status="unverified",
            )],
            status=AnswerStatus.PARTIALLY_SUPPORTED,
        )


@pytest.fixture(autouse=True)
def isolate_chat_api_database(db_session):
    previous = app.dependency_overrides.get(get_db)

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    yield
    if previous is None:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previous


def _student_user():
    return User(
        id=99,
        username="test.student",
        email="test.student@example.edu",
        password_hash="unused-test-hash",
        role="student",
        is_active=True,
    )


def test_chat_route_supplies_only_owned_document_metadata(db_session):
    user = _student_user()
    db_session.add(user)
    db_session.flush()
    foreign_owner = User(
        id=1001, username="foreign.student", email="foreign.student@example.edu",
        password_hash="unused-test-hash", role="student", is_active=True,
    )
    db_session.add(foreign_owner)
    db_session.flush()
    owned = Document(
        filename="owned.pdf", document_name="Owned synthetic test.pdf", sha256="c" * 64,
        document_type="test_fixture", version="1", source_type="synthetic_test",
        verification_status="unverified", vector_sync_status="synced", uploaded_by_user_id=user.id,
        processing_status="indexed", storage_path="/tmp/owned.pdf", page_count=1, chunk_count=1,
    )
    foreign = Document(
        filename="foreign.pdf", document_name="Foreign synthetic test.pdf", sha256="d" * 64,
        document_type="test_fixture", version="1", source_type="synthetic_test",
        verification_status="unverified", vector_sync_status="synced", uploaded_by_user_id=foreign_owner.id,
        processing_status="indexed", storage_path="/tmp/foreign.pdf", page_count=1, chunk_count=1,
    )
    db_session.add(owned)
    db_session.add(foreign)
    db_session.commit()

    class CaptureService:
        calls = []

        def answer(self, question, **kwargs):
            self.calls.append((question, kwargs))
            return StructuredAnswer(answer="Mocked.", evidence=[], sources=[], status=AnswerStatus.NOT_FOUND)

    service = CaptureService()
    chat_route(ChatRequest(question="Explain the selected document"), service, user, db_session)
    passed_documents = service.calls[0][1]["available_documents"]
    assert [item["document_id"] for item in passed_documents] == [str(owned.id)]
    assert all(item["document_name"] != foreign.document_name for item in passed_documents)


def test_chat_route_rejects_unowned_document_selection_before_service_call(db_session):
    user = _student_user()
    db_session.add(user)
    db_session.flush()
    foreign_owner = User(
        id=1002, username="other.student", email="other.student@example.edu",
        password_hash="unused-test-hash", role="student", is_active=True,
    )
    db_session.add(foreign_owner)
    db_session.flush()
    foreign = Document(
        filename="foreign.pdf", document_name="Foreign synthetic test.pdf", sha256="e" * 64,
        document_type="test_fixture", version="1", source_type="synthetic_test",
        verification_status="unverified", vector_sync_status="synced", uploaded_by_user_id=foreign_owner.id,
        processing_status="indexed", storage_path="/tmp/foreign.pdf", page_count=1, chunk_count=1,
    )
    db_session.add(foreign)
    db_session.commit()

    class CaptureService:
        called = False

        def answer(self, question, **kwargs):
            self.called = True
            raise AssertionError("Service must not receive an unauthorized document.")

    service = CaptureService()
    with pytest.raises(HTTPException) as error:
        chat_route(ChatRequest(question="Analyze this", document_id=foreign.id), service, user, db_session)
    assert error.value.status_code == 404
    assert service.called is False


def test_chat_api_returns_structured_answer_and_passes_retrieval_options():
    service = FixedChatService()
    app.dependency_overrides[get_chat_service] = lambda: service
    app.dependency_overrides[get_current_user] = _student_user
    try:
        response = TestClient(app).post(
            "/api/chat",
            json={
                "question": "  What does this test document say?  ",
                "prompt_type": "B",
                "top_k": 3,
                "metadata_filters": {"academic_year": "2026-2027", "uploaded_by_user_id": 1234},
            },
        )
    finally:
        app.dependency_overrides.pop(get_chat_service, None)
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert set(response.json()) == {"answer", "evidence", "sources", "status"}
    assert response.json()["status"] == "PARTIALLY_SUPPORTED"
    assert response.json()["evidence"][0]["document"] == "Synthetic Test Handbook.pdf"
    assert response.json()["evidence"][0]["page"] == 2
    assert response.json()["evidence"][0]["verification_status"] == "unverified"
    assert service.calls == [
        (
            "What does this test document say?",
            3,
            {"academic_year": "2026-2027", "uploaded_by_user_id": 99},
            PromptType.B,
        )
    ]


def test_chat_api_rejects_blank_question():
    service = FixedChatService()
    app.dependency_overrides[get_chat_service] = lambda: service
    app.dependency_overrides[get_current_user] = _student_user
    try:
        response = TestClient(app).post("/api/chat", json={"question": "   "})
    finally:
        app.dependency_overrides.pop(get_chat_service, None)
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 422
    assert service.calls == []


def test_chat_api_defaults_to_prompt_c():
    service = FixedChatService()
    app.dependency_overrides[get_chat_service] = lambda: service
    app.dependency_overrides[get_current_user] = _student_user
    try:
        response = TestClient(app).post("/api/chat", json={"question": "A valid test question"})
    finally:
        app.dependency_overrides.pop(get_chat_service, None)
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert service.calls[0][3] == PromptType.C


def test_chat_api_rejects_invalid_prompt_type():
    service = FixedChatService()
    app.dependency_overrides[get_chat_service] = lambda: service
    app.dependency_overrides[get_current_user] = _student_user
    try:
        response = TestClient(app).post(
            "/api/chat",
            json={"question": "A valid test question", "prompt_type": "D"},
        )
    finally:
        app.dependency_overrides.pop(get_chat_service, None)
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 422
    assert service.calls == []


def test_summary_request_resolves_explicit_owned_indexed_document(db_session):
    document = Document(
        filename="synthetic-summary.pdf", document_name="Synthetic Summary Test.pdf", sha256="a" * 64,
        document_type="synthetic_test", version="1", source_type="synthetic_test",
        verification_status="unverified", vector_sync_status="synced", uploaded_by_user_id=99,
        processing_status="indexed", storage_path="/synthetic/test-only.pdf", page_count=2, chunk_count=2,
    )
    db_session.add(document)
    db_session.commit()
    service = FixedChatService()

    def override_db():
        yield db_session

    app.dependency_overrides[get_chat_service] = lambda: service
    app.dependency_overrides[get_current_user] = _student_user
    app.dependency_overrides[get_db] = override_db
    try:
        response = TestClient(app).post("/api/chat", json={
            "question": "Summarize this PDF in 10 points", "document_id": document.id,
        })
    finally:
        app.dependency_overrides.pop(get_chat_service, None)
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert service.calls[0][-1] == document.id


def test_summary_request_cannot_select_another_students_document(db_session):
    document = Document(
        filename="other.pdf", document_name="Synthetic Other Student.pdf", sha256="b" * 64,
        document_type="synthetic_test", version="1", source_type="synthetic_test",
        verification_status="unverified", vector_sync_status="synced", uploaded_by_user_id=123,
        processing_status="indexed", storage_path="/synthetic/other.pdf", page_count=1, chunk_count=1,
    )
    db_session.add(document)
    db_session.commit()
    service = FixedChatService()

    def override_db():
        yield db_session

    app.dependency_overrides[get_chat_service] = lambda: service
    app.dependency_overrides[get_current_user] = _student_user
    app.dependency_overrides[get_db] = override_db
    try:
        response = TestClient(app).post("/api/chat", json={
            "question": "Summarize this PDF", "document_id": document.id,
        })
    finally:
        app.dependency_overrides.pop(get_chat_service, None)
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 404
    assert service.calls == []


def test_selected_accessible_document_frontend_contract_is_accepted(db_session):
    user = _student_user()
    db_session.add(user)
    db_session.flush()
    document = Document(
        filename="selected-synthetic.pdf", document_name="Selected synthetic test.pdf", sha256="f" * 64,
        document_type="test_fixture", version="1", source_type="synthetic_test",
        verification_status="unverified", vector_sync_status="synced", uploaded_by_user_id=user.id,
        processing_status="indexed", storage_path="/tmp/selected-synthetic.pdf", page_count=1, chunk_count=1,
    )
    db_session.add(document)
    db_session.commit()
    conversation = ConversationService(db_session).create(user_id=user.id, title="Synthetic test")
    service = FixedChatService()

    def override_db():
        yield db_session

    app.dependency_overrides[get_chat_service] = lambda: service
    app.dependency_overrides[get_current_user] = _student_user
    app.dependency_overrides[get_db] = override_db
    try:
        response = TestClient(app).post("/api/chat", json={
            "question": "What does this selected synthetic document say?",
            "document_id": document.id,
            "conversation_id": conversation.id,
            "idempotency_key": "b2e0fd56-a8d4-4aef-85ae-0c086e60b45d",
            "prompt_type": "C",
        })
    finally:
        app.dependency_overrides.pop(get_chat_service, None)
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200, response.json()
    assert service.calls[0][-1] == document.id


def test_chat_api_requires_authentication():
    response = TestClient(app).post("/api/chat", json={"question": "A valid test question"})
    assert response.status_code == 401
