"""Vocabulary illustration cache — slug lookup and URLs for flashcards."""

import json
import os
import re
import unicodedata
from typing import Optional

_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vocab_images")
_MANIFEST_PATH = os.path.join(_DIR, "manifest.json")
_manifest_cache: dict | None = None
_manifest_mtime: float = 0.0


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFD", (text or "").lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def vocab_slug(word_es: str) -> str:
    """Stable filesystem-safe key for a Spanish word or phrase."""
    s = _norm(word_es)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return (s[:80] or "word")


def _load_manifest() -> dict:
    global _manifest_cache, _manifest_mtime
    try:
        mtime = os.path.getmtime(_MANIFEST_PATH)
    except OSError:
        return {}
    if _manifest_cache is not None and mtime == _manifest_mtime:
        return _manifest_cache
    try:
        with open(_MANIFEST_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        _manifest_cache = data if isinstance(data, dict) else {}
        _manifest_mtime = mtime
        return _manifest_cache
    except (OSError, json.JSONDecodeError):
        return {}


def manifest_path() -> str:
    return _MANIFEST_PATH


def images_dir() -> str:
    os.makedirs(_DIR, exist_ok=True)
    return _DIR


def image_file_for(word_es: str) -> Optional[str]:
    slug = vocab_slug(word_es)
    return image_file_for_slug(slug)


def image_file_for_slug(slug: str) -> Optional[str]:
    entry = _load_manifest().get(slug)
    if not entry:
        return None
    fname = entry.get("file") if isinstance(entry, dict) else entry
    if not fname:
        return None
    path = os.path.join(_DIR, fname)
    return path if os.path.isfile(path) else None


def manifest_has(slug: str) -> bool:
    return slug in _load_manifest()


def image_url_for(word_es: str) -> Optional[str]:
    if image_file_for(word_es):
        return f"/api/images/vocab/{vocab_slug(word_es)}"
    return None


def attach_image(vocab_item: dict) -> dict:
    """Add image_url to a vocab dict when a cached illustration exists."""
    url = image_url_for(vocab_item.get("es", ""))
    if url:
        vocab_item = dict(vocab_item)
        vocab_item["image_url"] = url
    return vocab_item


def save_manifest_entry(slug: str, filename: str, word_es: str, gloss_en: str = ""):
    manifest = dict(_load_manifest())
    manifest[slug] = {"file": filename, "es": word_es, "en": gloss_en}
    os.makedirs(_DIR, exist_ok=True)
    tmp = _MANIFEST_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, _MANIFEST_PATH)
    invalidate_manifest_cache()


def invalidate_manifest_cache():
    global _manifest_cache, _manifest_mtime
    _manifest_cache = None
    _manifest_mtime = 0.0
