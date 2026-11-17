from __future__ import annotations

from datetime import timedelta
from datetime import datetime, timezone
from typing import Iterator

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.auth.dependencies import get_current_user, get_db, require_admin
from app.config import settings
from app.database.db import Base, migrate_user_schema
from app.database.models import User
from app.routes.auth import router as auth_router
from app.scripts import bootstrap_admin
from app.services.security import create_access_token, hash_password, verify_password


@pytest.fixture
def auth_client(tmp_path, monkeypatch) -> Iterator[tuple[TestClient, Session]]:
    engine = create_engine(f"sqlite:///{tmp_path / 'auth-test.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = session_factory()
    monkeypatch.setattr(settings, "jwt_secret_key", "test-signing-secret-with-at-least-32-bytes")
    monkeypatch.setattr(settings, "access_token_expire_minutes", 30)

    app = FastAPI()
    app.include_router(auth_router)

    @app.get("/admin-test")
    def admin_test(user: User = Depends(require_admin)) -> dict[str, str]:
        return {"role": user.role}

    def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as client:
        yield client, session
    app.dependency_overrides.clear()
    session.close()
    engine.dispose()


def register(client: TestClient, **values) -> object:
    payload = {"username": "Student.One", "email": "Student@Example.edu", "password": "long-test-password-123"}
    payload.update(values)
    return client.post("/api/auth/register", json=payload)


def login(client: TestClient, identifier: str, password: str = "long-test-password-123"):
    return client.post("/api/auth/login", json={"identifier": identifier, "password": password})


def test_password_hashing_uses_argon2_and_verifies_both_cases():
    encoded = hash_password("a-strong-test-password")
    assert encoded.startswith("$argon2")
    assert verify_password("a-strong-test-password", encoded)
    assert not verify_password("incorrect-password", encoded)


def test_register_creates_student_and_never_returns_password(auth_client):
    client, session = auth_client
    response = register(client)
    assert response.status_code == 201
    assert response.json() == {
        "id": 1,
        "username": "student.one",
        "email": "student@example.edu",
        "role": "student",
        "is_active": True,
    }
    user = session.scalar(select(User))
    assert user.password_hash != "long-test-password-123"
    assert user.password_hash.startswith("$argon2")
    assert "password" not in response.json() and "password_hash" not in response.json()


def test_duplicate_username_and_email_are_rejected_case_insensitively(auth_client):
    client, _ = auth_client
    assert register(client).status_code == 201
    assert register(client, username="STUDENT.ONE", email="other@example.edu").status_code == 409
    assert register(client, username="other", email="STUDENT@example.edu").status_code == 409


def test_public_registration_rejects_admin_role_and_invalid_password(auth_client):
    client, _ = auth_client
    assert register(client, role="admin").status_code == 422
    assert register(client, password="short").status_code == 422


@pytest.mark.parametrize("identifier", ["student.one", "student@example.edu"])
def test_login_accepts_normalized_username_or_email(auth_client, identifier):
    client, _ = auth_client
    assert register(client).status_code == 201
    response = login(client, identifier)
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == settings.access_token_expire_minutes * 60
    assert body["user"]["role"] == "student"
    assert "password_hash" not in body["user"]


@pytest.mark.parametrize(
    ("identifier", "password"),
    [("unknown@example.edu", "long-test-password-123"), ("student.one", "incorrect-password")],
)
def test_login_failure_is_generic(auth_client, identifier, password):
    client, _ = auth_client
    register(client)
    response = login(client, identifier, password)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username/email or password."


def test_me_with_valid_token_returns_safe_user(auth_client):
    client, _ = auth_client
    register(client)
    token = login(client, "student.one").json()["access_token"]
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["role"] == "student"
    assert "password_hash" not in response.json()


@pytest.mark.parametrize("authorization", [None, "Bearer invalid-token"])
def test_me_rejects_missing_or_invalid_token(auth_client, authorization):
    client, _ = auth_client
    headers = {} if authorization is None else {"Authorization": authorization}
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_expired_token_is_rejected(auth_client):
    client, _ = auth_client
    register(client)
    user_id = 1
    now = datetime.now(timezone.utc)
    expired = jwt.encode(
        {"sub": str(user_id), "type": "access", "iat": now - timedelta(minutes=2), "exp": now - timedelta(minutes=1)},
        settings.jwt_secret_key,
        algorithm="HS256",
    )
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401


def test_inactive_account_is_rejected(auth_client):
    client, session = auth_client
    register(client)
    user = session.get(User, 1)
    user.is_active = False
    session.commit()
    token = create_access_token(user.id)
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401
    assert login(client, "student.one").status_code == 401


def test_student_is_forbidden_on_admin_route_and_admin_is_allowed(auth_client):
    client, session = auth_client
    register(client)
    student_token = login(client, "student.one").json()["access_token"]
    assert client.get("/admin-test", headers={"Authorization": f"Bearer {student_token}"}).status_code == 403

    session.add(
        User(
            username="first.admin",
            email="admin@example.edu",
            password_hash=hash_password("admin-test-password-long"),
            role="admin",
        )
    )
    session.commit()
    admin_token = create_access_token(2)
    response = client.get("/admin-test", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    assert response.json() == {"role": "admin"}


def test_role_claim_in_token_is_ignored_in_favor_of_database(auth_client):
    client, session = auth_client
    register(client)
    token = jwt.encode(
        {
            "sub": "1",
            "role": "admin",
            "type": "access",
            "iat": datetime.now(timezone.utc) - timedelta(seconds=1),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        },
        settings.jwt_secret_key,
        algorithm="HS256",
    )
    response = client.get("/admin-test", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
    assert session.get(User, 1).role == "student"


def test_token_requires_configured_secret(monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret_key", None)
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        create_access_token(1)


def test_bootstrap_creates_first_admin_with_argon2_hash(tmp_path, monkeypatch, capsys):
    engine = create_engine(f"sqlite:///{tmp_path / 'bootstrap.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(bootstrap_admin, "SessionLocal", factory)
    answers = iter(["First.Admin", "ADMIN@example.edu"])
    secrets = iter(["admin-bootstrap-password", "admin-bootstrap-password"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    monkeypatch.setattr("getpass.getpass", lambda _prompt: next(secrets))

    assert bootstrap_admin.main() == 0
    with factory() as session:
        admin = session.scalar(select(User).where(User.role == "admin"))
        assert admin.username == "first.admin"
        assert admin.email == "admin@example.edu"
        assert admin.password_hash.startswith("$argon2")
        assert verify_password("admin-bootstrap-password", admin.password_hash)
    assert "Administrator account created." in capsys.readouterr().out
    engine.dispose()


def test_bootstrap_refuses_when_an_admin_already_exists(tmp_path, monkeypatch, capsys):
    engine = create_engine(f"sqlite:///{tmp_path / 'bootstrap-existing.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory.begin() as session:
        session.add(
            User(
                username="already.admin",
                email="already@example.edu",
                password_hash=hash_password("an-existing-admin-password"),
                role="admin",
            )
        )
    monkeypatch.setattr(bootstrap_admin, "SessionLocal", factory)
    monkeypatch.setattr("builtins.input", lambda _prompt: pytest.fail("must refuse before prompting"))
    assert bootstrap_admin.main() == 1
    assert "already exists" in capsys.readouterr().err
    engine.dispose()


def test_user_table_migration_is_idempotent_and_preserves_existing_rows(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE documents (id INTEGER PRIMARY KEY, filename TEXT NOT NULL)")
        connection.exec_driver_sql("INSERT INTO documents (id, filename) VALUES (1, 'keep.pdf')")
        connection.exec_driver_sql(
            "CREATE TABLE conversation_messages (id INTEGER PRIMARY KEY, role TEXT NOT NULL, content TEXT NOT NULL)"
        )
        connection.exec_driver_sql(
            "INSERT INTO conversation_messages (id, role, content) VALUES (1, 'user', 'keep message')"
        )
    migrate_user_schema(engine)
    migrate_user_schema(engine)
    with engine.connect() as connection:
        assert connection.exec_driver_sql("SELECT filename FROM documents").scalar_one() == "keep.pdf"
        assert connection.exec_driver_sql("SELECT content FROM conversation_messages").scalar_one() == "keep message"
        assert "users" in __import__("sqlalchemy").inspect(connection).get_table_names()
    engine.dispose()
