"""Test 1/5 — Production configuration & secrets."""

from datetime import date
from pathlib import Path

import pytest

from app.config import get_settings

ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST = ROOT / "frontend" / "dist"
ENV_FILES = [ROOT / ".env", ROOT / "backend" / ".env"]


def test_openai_api_key_configured():
    """TTS, tips and RU→MX translator need a real OpenAI key."""
    settings = get_settings()
    key = (settings.openai_api_key or "").strip()
    assert key, "OPENAI_API_KEY is missing — set it in .env"
    assert key.startswith("sk-"), "OPENAI_API_KEY does not look valid"


def test_secret_key_not_default():
    """JWT secret must be changed before production."""
    settings = get_settings()
    assert settings.secret_key != "change-me-in-production-please-use-a-long-random-string", (
        "SECRET_KEY is still the default — set a long random string in .env"
    )
    assert len(settings.secret_key) >= 32, "SECRET_KEY should be at least 32 characters"


def test_program_start_date_july_first():
    """Family calendar starts 1 July (day 1 = first lesson)."""
    settings = get_settings()
    assert settings.program_start_date == date(2026, 7, 1)


def test_env_file_present():
    """At least one .env file exists at project or backend root."""
    assert any(p.is_file() for p in ENV_FILES), "No .env file found (root or backend/.env)"


def test_frontend_built():
    """Production serves static files from frontend/dist."""
    index = FRONTEND_DIST / "index.html"
    assert index.is_file(), "Run: cd frontend && npm run build"
    html = index.read_text(encoding="utf-8")
    assert 'id="root"' in html
    assert "/assets/" in html
