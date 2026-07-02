"""Angélica chat API."""

import os
import tempfile
import uuid

import pytest
from fastapi.testclient import TestClient

_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_db.name}"
os.environ.setdefault("SECRET_KEY", "pytest-secret-key-minimum-32-characters-long")

from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def auth_headers(client):
    email = f"angelica-{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(
        "/api/auth/register",
        json={"email": email, "password": "testpass123", "name": "AngelicaTest", "avatar": "🦊"},
    )
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_angelica_history_welcome(client, auth_headers):
    r = client.get("/api/angelica/history", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data["messages"]) == 1
    assert data["messages"][0]["role"] == "assistant"
    assert "Soy" in data["messages"][0]["content"]


def test_angelica_send_requires_api_key(client, auth_headers, monkeypatch):
    from app.routers import angelica as angelica_mod

    monkeypatch.setattr(angelica_mod.settings, "openai_api_key", "")
    r = client.post(
        "/api/angelica/send",
        headers=auth_headers,
        json={"message": "Hola"},
    )
    assert r.status_code == 503


def test_angelica_clear_history(client, auth_headers):
    r = client.delete("/api/angelica/history", headers=auth_headers)
    assert r.status_code == 200
    r2 = client.get("/api/angelica/history", headers=auth_headers)
    assert r2.status_code == 200
    assert len(r2.json()["messages"]) == 1
