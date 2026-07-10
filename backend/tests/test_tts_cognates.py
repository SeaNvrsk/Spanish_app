"""TTS cognate-word detection for EN/ES homographs like «formal»."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.routers.tts import _is_cognate_word, _tts_instructions, MEXICAN_INSTRUCTIONS, _cache_key


def test_formal_is_cognate():
    assert _is_cognate_word("formal")
    assert _is_cognate_word("Formal")


def test_informal_is_cognate():
    assert _is_cognate_word("informal")


def test_phrase_is_not_cognate():
    assert not _is_cognate_word("¿Cómo estás?")
    assert not _is_cognate_word("Buenos días")


def test_spanish_only_word_not_in_set():
    assert not _is_cognate_word("encantado")
    assert not _is_cognate_word("presentar")


def test_cognate_gets_spanish_instructions():
    instr = _tts_instructions("formal", MEXICAN_INSTRUCTIONS)
    assert "formal" in instr
    assert "NOT with English" in instr or "NOT with English pronunciation" in instr


def test_cache_key_bumped_for_teacher():
    key = _cache_key("formal", "teacher")
    assert key  # stable hash
    assert _cache_key("formal", "teacher") == key
