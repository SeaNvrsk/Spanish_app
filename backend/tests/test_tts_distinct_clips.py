"""Consecutive lesson words must not share TTS cache identity or browser cache."""

from app.routers.tts import _audio_response, _cache_key
from app.curriculum.builder import get_lesson


def test_cache_keys_differ_for_different_words():
    assert _cache_key("hola", "teacher") != _cache_key("adiós", "teacher")
    assert _cache_key("ser", "teacher") != _cache_key("estar", "teacher")
    assert _cache_key("la mamá", "teacher") != _cache_key("el papá", "teacher")


def test_same_word_reuses_cache_key():
    assert _cache_key("hola", "teacher") == _cache_key("  hola  ", "teacher")


def test_teacher_and_angelica_keys_differ():
    assert _cache_key("hola", "teacher") != _cache_key("hola", "angelica")


def test_tts_response_must_not_be_immutable():
    """POST /tts/speak is one URL for every word. Immutable cache replays clip 1."""
    resp = _audio_response(b"\xff\xf3" + b"\x00" * 400, "abc123", "HIT")
    cc = (resp.headers.get("cache-control") or "").lower()
    assert "immutable" not in cc
    assert "no-store" in cc or "no-cache" in cc
    assert "max-age=31536000" not in cc


def test_listen_exercises_in_a_lesson_are_not_all_the_same_word():
    for lesson_id in ("w03-d1", "w04-d3", "w06-d1", "w07-d1"):
        lesson = get_lesson(lesson_id)
        listens = [ex for ex in lesson.get("exercises") or [] if ex.get("type") == "listen"]
        audios = [ex["audio"] for ex in listens]
        unique = set(audios)
        assert len(unique) >= min(2, len(audios)), f"{lesson_id} listen clips: {audios}"


def test_listen_audio_matches_prompt_word():
    for lesson_id in ("w03-d1", "w04-d3", "w06-d1", "w07-d1"):
        lesson = get_lesson(lesson_id)
        assert lesson, lesson_id
        listens = [ex for ex in lesson.get("exercises") or [] if ex.get("type") == "listen"]
        assert listens, f"{lesson_id} has no listen exercises"
        for ex in listens:
            assert ex.get("audio"), f"{lesson_id} listen {ex.get('id')} missing audio"
            assert ex["audio"] == ex.get("es") or ex["audio"] == ex.get("answer")


def test_week11_has_no_grammar_formula_flashcards():
    from app.curriculum.builder import get_lesson

    lesson = get_lesson("w11-d3")
    assert lesson
    texts = [ex.get("es") or "" for ex in lesson.get("exercises") or []]
    assert not any("+" in t or t.startswith("-") for t in texts)


def test_lloviendo_russian_is_rain():
    from app.curriculum.a1_boost import A1_BOOST

    hits = [row for row in A1_BOOST[11] if row[0] == "Está lloviendo."]
    assert hits
    assert "дождь" in hits[0][2]
