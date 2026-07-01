"""Test 4/5 — HTTP API smoke (auth, curriculum lock, tools)."""

import os
import tempfile
import uuid

import pytest
from fastapi.testclient import TestClient

# Isolated DB per test module — must set before app import.
_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_db.name}"
os.environ.setdefault("SECRET_KEY", "pytest-secret-key-minimum-32-characters-long")

from app.config import get_settings  # noqa: E402
from app.main import app  # noqa: E402

get_settings.cache_clear()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def auth_headers(client):
    email = f"prodtest-{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(
        "/api/auth/register",
        json={"email": email, "password": "testpass123", "name": "ProdTest", "avatar": "🦊"},
    )
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health_endpoint(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_curriculum_returns_calendar_fields(client, auth_headers):
    r = client.get("/api/curriculum", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "program_start_date" in data
    assert "program_day" in data
    assert "today_lesson_id" in data
    day = data["levels"][0]["weeks"][0]["days"][0]
    assert "unlocked" in day
    assert "unlock_date" in day


def test_locked_lesson_returns_403(client, auth_headers):
    """Lesson for a future calendar day must be blocked."""
    from datetime import date
    from app.schedule import max_unlocked_global_day

    max_day = max_unlocked_global_day(date.today())
    r = client.get("/api/lessons/w29-d1", headers=auth_headers)
    if max_day < 200:
        assert r.status_code == 403
    else:
        assert r.status_code in (200, 403)


def test_conjugate_endpoint_mexican_pronouns(client, auth_headers):
    r = client.post(
        "/api/tools/conjugate",
        headers=auth_headers,
        json={"verb": "hablar", "tense": "present"},
    )
    assert r.status_code == 200
    data = r.json()
    pronouns = [row["pronoun"] for row in data["forms"]]
    assert "vosotros" not in " ".join(pronouns).lower()
    assert "ustedes" in pronouns[4].lower()
    assert data["forms"][0]["form"] == "hablo"


def test_spa_index_served(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert "root" in r.text
