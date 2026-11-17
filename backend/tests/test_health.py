from fastapi.testclient import TestClient

from app.main import app
from app.config import settings

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "RAARA"}


def test_ai_health_reports_provider_without_exposing_api_key():
    response = client.get("/api/health/ai")
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == settings.ai_provider.casefold()
    assert body["chat_model"] == settings.active_chat_model
    assert body["embedding_provider"] == "local"
    assert body["embedding_model"] == settings.active_embedding_model
    assert body["embedding_dimensions"] == 384
    assert body["credential_configured"] is bool(settings.active_api_key)
    assert body["availability"] == "not_checked"
    assert all("key" not in key.casefold() or key == "credential_configured" for key in body)
