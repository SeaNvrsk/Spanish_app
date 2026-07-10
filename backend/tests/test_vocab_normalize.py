"""SRS vocab alignment — cloze fragments must match sentence-level glosses."""

from app.curriculum.builder import (
    normalize_vocab_entry,
    repair_card_vocab,
    get_all_lessons,
    build_quiz,
    all_vocab_pool,
)


def test_normalize_llamo_fragment_by_russian_gloss():
    n = normalize_vocab_entry("llamo", "", "Привет, меня зовут Ана.")
    assert n["es"] == "Hola, me llamo Ana."
    assert n["translations"]["ru"] == "Привет, меня зовут Ана."


def test_normalize_llamo_fragment_by_english_gloss():
    n = normalize_vocab_entry("llamo", "My name is Ana.", "")
    assert n["es"] == "Me llamo Ana."


def test_normalize_leaves_intact_vocab_word():
    n = normalize_vocab_entry("Hola", "Hello", "Привет")
    assert n["es"] == "Hola"


def test_cloze_exercises_store_full_sentence():
    lessons = get_all_lessons()
    for lesson in lessons.values():
        for ex in lesson["exercises"]:
            if ex["type"] != "cloze":
                continue
            assert ex["es"] == ex["sentence"], f"{ex['id']}: es must be full sentence"
            assert ex["audio"] == ex["sentence"], f"{ex['id']}: audio must match sentence"
            assert ex["answer"] in ex["sentence"], f"{ex['id']}: answer must appear in sentence"


def test_review_quiz_audio_matches_answer_gloss():
    """Listen exercises: Spanish audio and gloss must describe the same unit."""
    vocab = [
        {"es": "Hola", "translations": {"en": "Hello", "ru": "Привет"}},
        {"es": "Hola, me llamo Ana.", "translations": {"en": "Hi, my name is Ana.", "ru": "Привет, меня зовут Ана."}},
    ]
    exercises = build_quiz(vocab, all_vocab_pool(), seed="test-llamo")
    listen = next(ex for ex in exercises if ex["type"] == "listen" and ex["answer"] == "Hola, me llamo Ana.")
    assert listen["audio"] == "Hola, me llamo Ana."
    assert listen["answer"] == "Hola, me llamo Ana."
    correct = next(o for o in listen["options"] if o["es"] == listen["answer"])
    assert correct["translations"]["ru"] == "Привет, меня зовут Ана."


def test_repair_card_vocab():
    r = repair_card_vocab("llamo", "Hi, my name is Ana.", "Привет, меня зовут Ана.")
    assert r["es"] == "Hola, me llamo Ana."


def test_chao_and_adios_are_synonyms_in_translate_quiz():
    from app.curriculum.builder import _accepted_es_answers, _same_meaning

    adios = {"es": "Adiós", "translations": {"en": "Goodbye", "ru": "Пока"}}
    chao = {"es": "chao", "translations": {"en": "bye (casual)", "ru": "пока"}}
    mientras = {"es": "mientras", "translations": {"en": "while", "ru": "пока"}}
    assert _same_meaning(adios, chao)
    assert not _same_meaning(adios, mientras)
    accepted = {a.lower() for a in _accepted_es_answers(adios)}
    assert "chao" in accepted
    assert "mientras" not in accepted


def test_chao_and_adios_synonyms_in_native_to_es_choice():
    from app.curriculum.builder import _same_meaning

    chao = {"es": "chao", "translations": {"en": "bye (casual)", "ru": "пока"}}
    adios = {"es": "Adiós", "translations": {"en": "Goodbye", "ru": "Пока"}}
    assert _same_meaning(chao, adios)
