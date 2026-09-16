"""Vocabulary illustration cache — slug lookup and URLs for flashcards."""

import json
import os
import re
import unicodedata
from functools import lru_cache
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


def _token_key(word_es: str) -> Optional[str]:
    """Normalized single-token key, or None for phrases / empty."""
    raw = (word_es or "").strip()
    if not raw:
        return None
    # Phrases and full sentences keep their own image identity.
    if any(ch.isspace() for ch in raw) or "¿" in raw or "?" in raw or "¡" in raw or "!" in raw:
        return None
    key = _norm(raw)
    key = re.sub(r"[^a-z0-9]+", "", key)
    return key or None


@lru_cache(maxsize=1)
def _form_to_lemma() -> dict[str, str]:
    """Map conjugated forms → infinitive so flashcards share one picture per verb."""
    from .conjugation import IRREGULAR, TENSES, conjugate
    from .curriculum.a1_boost import A1_BOOST
    from .curriculum.a1_boost_extra import A1_BOOST_EXTRA
    from .curriculum.program import WEEKS

    infinitives: dict[str, str] = {}  # norm → surface infinitive
    irreg_keys = {_token_key(v) for v in IRREGULAR if _token_key(v)}

    def add_inf(word: str, en: str = ""):
        token = _token_key(word)
        if not token or len(token) < 3:
            return
        if not (token.endswith("ar") or token.endswith("er") or token.endswith("ir")):
            return
        en_l = (en or "").strip().lower()
        if token not in irreg_keys and not en_l.startswith("to "):
            return
        infinitives.setdefault(token, word.strip().lower())

    for wk in WEEKS:
        for raw in wk.get("vocab", []):
            add_inf(raw[0], raw[1] if len(raw) > 1 else "")
        w = wk.get("week")
        for raw in A1_BOOST.get(w, []) + A1_BOOST_EXTRA.get(w, []):
            add_inf(raw[0], raw[1] if len(raw) > 1 else "")
    for verb in IRREGULAR:
        add_inf(verb)

    mapping: dict[str, str] = {}
    for norm_inf, surface in infinitives.items():
        mapping.setdefault(norm_inf, surface)
        for tense in TENSES:
            try:
                data = conjugate(surface, tense)
            except Exception:
                continue
            for row in data.get("forms") or []:
                form = _token_key(row.get("form") or "")
                if not form:
                    continue
                # Don't steal another infinitive's identity (rare collisions).
                if form in infinitives and form != norm_inf:
                    continue
                mapping.setdefault(form, surface)
    return mapping


def image_lemma_for(word_es: str) -> Optional[str]:
    """Infinitive to share an image with, if this word is a conjugated form."""
    key = _token_key(word_es)
    if not key:
        return None
    lemma = _form_to_lemma().get(key)
    if not lemma:
        return None
    if _token_key(lemma) == key:
        return None  # already the infinitive
    return lemma


def image_canonical_word(word_es: str) -> str:
    """Word used as the image identity (infinitive when conjugated)."""
    return image_lemma_for(word_es) or (word_es or "").strip()


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


def _path_from_manifest_slug(slug: str) -> Optional[str]:
    entry = _load_manifest().get(slug)
    if not entry:
        return None
    fname = entry.get("file") if isinstance(entry, dict) else entry
    if not fname:
        return None
    path = os.path.join(_DIR, fname)
    return path if os.path.isfile(path) else None


def image_file_for(word_es: str) -> Optional[str]:
    canonical = image_canonical_word(word_es)
    path = _path_from_manifest_slug(vocab_slug(canonical))
    if path:
        return path
    # Fall back to the exact word (legacy per-form downloads).
    if canonical != (word_es or "").strip():
        return _path_from_manifest_slug(vocab_slug(word_es))
    return None


def image_file_for_slug(slug: str) -> Optional[str]:
    path = _path_from_manifest_slug(slug)
    if path:
        return path
    # Conjugation slug → infinitive file (e.g. hablo → hablar.webp).
    lemma = _form_to_lemma().get(slug)
    if not lemma:
        compact = _norm(slug).replace("-", "")
        lemma = _form_to_lemma().get(compact)
    if lemma:
        return _path_from_manifest_slug(vocab_slug(lemma))
    return None


def manifest_has(slug: str) -> bool:
    if slug in _load_manifest():
        return True
    return image_file_for_slug(slug) is not None


def image_url_for(word_es: str) -> Optional[str]:
    path = image_file_for(word_es)
    if not path:
        return None
    try:
        ver = int(os.path.getmtime(path))
    except OSError:
        ver = 0
    # URL slug must match the file we serve (infinitive when shared).
    slug = vocab_slug(image_canonical_word(word_es))
    # If only a legacy per-form file exists, serve under that slug.
    if not _path_from_manifest_slug(slug):
        slug = vocab_slug(word_es)
    return f"/api/images/vocab/{slug}?v={ver}"


def attach_image(vocab_item: dict) -> dict:
    """Add image_url to a vocab dict when a cached illustration exists."""
    url = image_url_for(vocab_item.get("es", ""))
    if url:
        vocab_item = dict(vocab_item)
        vocab_item["image_url"] = url
    return vocab_item


def refresh_images(obj):
    """Re-bind image_url fields from the on-disk cache (lesson build is LRU-cached)."""
    if isinstance(obj, dict):
        es = obj.get("es")
        if isinstance(es, str) and es.strip():
            url = image_url_for(es)
            if url:
                obj["image_url"] = url
            else:
                obj.pop("image_url", None)
        for value in obj.values():
            refresh_images(value)
    elif isinstance(obj, list):
        for item in obj:
            refresh_images(item)
    return obj


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
