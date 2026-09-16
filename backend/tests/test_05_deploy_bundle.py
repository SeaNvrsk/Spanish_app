"""Test 5/5 — Deploy bundle: scripts, static assets, tools module."""

import os
import re
from pathlib import Path

from app.conjugation import PRONOUNS, conjugate
from app.main import app

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "frontend" / "dist"


def test_serve_script_executable():
    script = ROOT / "serve.sh"
    assert script.is_file()
    assert os.access(script, os.X_OK)


def test_frontend_assets_linked_from_index():
    index = DIST / "index.html"
    assert index.is_file()
    html = index.read_text(encoding="utf-8")
    parts = re.findall(r'"(app\.js\.p\d+)"', html)
    assert parts, "index.html must reference classic bundle parts"
    for name in parts:
        assert (DIST / "assets" / name).is_file(), f"Missing bundle: assets/{name}"


def test_frontend_assets_exist():
    assets = DIST / "assets"
    assert assets.is_dir()
    js_files = list(assets.glob("index-*.js")) or list(assets.glob("app*.js*"))
    assert js_files, "Missing built JS bundle"


def test_tools_routes_registered():
    paths = app.openapi().get("paths", {})
    assert "/api/tools/translate" in paths
    assert "/api/tools/conjugate" in paths


def test_conjugation_no_vosotros():
    assert not any("vosotros" in p for p in PRONOUNS)
    result = conjugate("tener", "present")
    forms = " ".join(r["form"] for r in result["forms"])
    assert "tenéis" not in forms.lower()
