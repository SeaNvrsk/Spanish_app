"""Tests for pronunciation scoring (no API calls)."""

from app.pronunciation_score import normalize, score_pronunciation


def test_normalize_strips_spanish_punctuation():
    assert normalize("¡Ey ya!") == "ey ya"


def test_ella_vs_mistranscription_ey_ya():
    result = score_pronunciation("ella", "¡Ey ya!")
    assert result.passed
    assert result.score == 100
    assert result.asr_corrected


def test_exact_match():
    result = score_pronunciation("ella", "ella")
    assert result.score == 100
    assert result.passed
    assert not result.asr_corrected


def test_hola_variants():
    result = score_pronunciation("hola", "hola!")
    assert result.score == 100
    assert result.passed


def test_clearly_wrong():
    result = score_pronunciation("ella", "buenos dias señor")
    assert not result.passed
    assert result.score < 70
