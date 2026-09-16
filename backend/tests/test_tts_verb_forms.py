"""TTS must treat conjugated verbs as Spanish, not English."""

from app.routers.tts import (
    MEXICAN_INSTRUCTIONS,
    TTS_CACHE_VERSION,
    _cache_key,
    _single_word,
    _tts_instructions,
    _verb_form_meta,
)


def test_cache_version_bumped_for_verb_prompts():
    assert TTS_CACHE_VERSION == "teacher-v17"


def test_hablo_is_conjugated_hablar():
    meta = _verb_form_meta("hablo")
    assert meta is not None
    assert meta["infinitive"] == "hablar"
    assert meta["pronoun"] == "yo"
    assert meta["tense"] == "present"


def test_hablas_hablamos_trabajo_estudio():
    assert _verb_form_meta("hablas")["infinitive"] == "hablar"
    assert _verb_form_meta("hablamos")["infinitive"] == "hablar"
    assert _verb_form_meta("trabajo")["infinitive"] == "trabajar"
    assert _verb_form_meta("estudio")["infinitive"] == "estudiar"


def test_ser_estar_short_forms():
    assert _verb_form_meta("soy")["infinitive"] == "ser"
    assert _verb_form_meta("es")["infinitive"] == "ser"
    assert _verb_form_meta("estoy")["infinitive"] == "estar"
    assert _verb_form_meta("está")["infinitive"] == "estar"


def test_infinitive_is_not_tagged_as_conjugated_form():
    assert _verb_form_meta("hablar") is None
    assert _single_word("hablar") == "hablar"


def test_phrases_are_not_single_verb_forms():
    assert _verb_form_meta("Yo hablo español.") is None
    assert _verb_form_meta("¿Hablas inglés?") is None
    assert _single_word("¿Hablas inglés?") is None


def test_hablo_instructions_force_spanish_not_infinitive():
    instr = _tts_instructions("hablo", MEXICAN_INSTRUCTIONS)
    assert "hablar" in instr
    assert "hablo" in instr
    assert "yo" in instr
    assert "NOT English" in instr or "not English" in instr.lower()
    assert "do not say the infinitive" in instr.lower()


def test_es_instructions_are_spanish_ser():
    instr = _tts_instructions("es", MEXICAN_INSTRUCTIONS)
    assert "ser" in instr
    assert "«es»" in instr or "es" in instr


def test_phrase_keeps_base_without_conjugation_blurb():
    instr = _tts_instructions("Yo hablo español.", MEXICAN_INSTRUCTIONS)
    assert "conjugated Mexican Spanish verb" not in instr
    assert "Mexican Spanish" in instr


def test_conjugated_and_infinitive_keep_distinct_cache_keys():
    assert _cache_key("hablo", "teacher") != _cache_key("hablar", "teacher")
    assert _cache_key("trabajo", "teacher") != _cache_key("trabajar", "teacher")
    assert _cache_key("es", "teacher") != _cache_key("ser", "teacher")


def test_comer_infinitive_not_tagged_as_a_form():
    assert _verb_form_meta("comer") is None
    assert _single_word("comer") == "comer"


def test_come_como_comes_resolve_to_comer():
    assert _verb_form_meta("come")["infinitive"] == "comer"
    assert _verb_form_meta("come")["pronoun"] == "él/ella/usted"
    assert _verb_form_meta("como")["infinitive"] == "comer"
    assert _verb_form_meta("comes")["infinitive"] == "comer"
    assert _verb_form_meta("comemos")["infinitive"] == "comer"


def test_conjugator_hint_pins_comer():
    meta = _verb_form_meta("come", "comer")
    assert meta["infinitive"] == "comer"
    instr = _tts_instructions("come", MEXICAN_INSTRUCTIONS, "comer")
    assert "comer" in instr
    assert "NEVER the English verb 'come'" in instr or "English" in instr


def test_comer_instructions_are_spanish_infinitive_not_english_noun():
    instr = _tts_instructions("comer", MEXICAN_INSTRUCTIONS)
    assert "INFINITIVE" in instr
    assert "NEVER English" in instr or "NEVER English 'comer'" in instr
    assert "ONLY Mexican Spanish" in instr or "Mexican Spanish" in instr


def test_come_instructions_forbid_english_come():
    instr = _tts_instructions("come", MEXICAN_INSTRUCTIONS)
    assert "comer" in instr
    assert "NEVER the English verb 'come'" in instr
    assert "conjugated" in instr


def test_ayer_is_not_treated_as_infinitive():
    from app.routers.tts import _is_known_infinitive, _is_speakable_spanish

    assert not _is_known_infinitive("ayer")
    instr = _tts_instructions("ayer", MEXICAN_INSTRUCTIONS)
    assert "INFINITIVE" not in instr
    assert _is_speakable_spanish("ayer")
    assert not _is_speakable_spanish("ir a + infinitive")
    assert not _is_speakable_spanish("-er")
    assert not _is_speakable_spanish("estoy + -ando/-iendo")
    assert not _is_speakable_spanish("más ... que")

