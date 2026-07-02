"""Spanish verb conjugation accuracy."""

import pytest

from app.conjugation import conjugate


def _forms(verb: str, tense: str) -> list[str]:
    return [r["form"] for r in conjugate(verb, tense)["forms"]]


def test_leer_preterite():
    assert _forms("leer", "preterite") == [
        "leí", "leíste", "leyó", "leímos", "leyeron", "leyeron",
    ]


def test_comer_preterite_regular():
    assert _forms("comer", "preterite") == [
        "comí", "comiste", "comió", "comimos", "comieron", "comieron",
    ]


def test_hablar_preterite():
    assert _forms("hablar", "preterite") == [
        "hablé", "hablaste", "habló", "hablamos", "hablaron", "hablaron",
    ]


def test_construir_preterite_vowel_stem():
    assert _forms("construir", "preterite") == [
        "construí", "construíste", "construyó", "construímos", "construyeron", "construyeron",
    ]


def test_traer_preterite_irregular():
    assert _forms("traer", "preterite") == [
        "traje", "trajiste", "trajo", "trajimos", "trajeron", "trajeron",
    ]


def test_leer_present():
    assert _forms("leer", "present")[0] == "leo"


# --- Spelling changes (-car / -gar / -zar) ---------------------------------
@pytest.mark.parametrize(
    "verb,expected_yo",
    [
        ("buscar", "busqué"),
        ("llegar", "llegué"),
        ("empezar", "empecé"),
        ("jugar", "jugué"),
        ("comenzar", "comencé"),
    ],
)
def test_preterite_ar_spelling(verb, expected_yo):
    assert _forms(verb, "preterite")[0] == expected_yo


# --- Preterite j-stem (-ucir) ----------------------------------------------
@pytest.mark.parametrize(
    "verb,expected_yo",
    [
        ("conducir", "conduje"),
        ("traducir", "traduje"),
        ("producir", "produje"),
        ("reducir", "reduje"),
        ("introducir", "introduje"),
    ],
)
def test_preterite_j_stem(verb, expected_yo):
    assert _forms(verb, "preterite")[0] == expected_yo


# --- Present yo-go / stem-change -------------------------------------------
@pytest.mark.parametrize(
    "verb,expected_yo",
    [
        ("oír", "oigo"),
        ("caer", "caigo"),
        ("traer", "traigo"),
        ("valer", "valgo"),
        ("empezar", "empiezo"),
        ("pensar", "pienso"),
        ("jugar", "juego"),
        ("conocer", "conozco"),
        ("traducir", "traduzco"),
    ],
)
def test_present_irregular_yo(verb, expected_yo):
    assert _forms(verb, "present")[0] == expected_yo


# --- Preterite stem-change -ir (e→i / o→u) ---------------------------------
@pytest.mark.parametrize(
    "verb,expected_el",
    [
        ("sentir", "sintió"),
        ("pedir", "pidió"),
        ("dormir", "durmió"),
        ("morir", "murió"),
        ("preferir", "prefirió"),
        ("servir", "sirvió"),
    ],
)
def test_preterite_ir_stem_change(verb, expected_el):
    assert _forms(verb, "preterite")[2] == expected_el


# --- Vowel-stem preterite ---------------------------------------------------
@pytest.mark.parametrize(
    "verb,expected_el",
    [
        ("huir", "huyó"),
        ("caer", "cayó"),
        ("creer", "creyó"),
        ("oír", "oyó"),
    ],
)
def test_preterite_vowel_stem_third(verb, expected_el):
    assert _forms(verb, "preterite")[2] == expected_el


# --- Future irregular stems -------------------------------------------------
@pytest.mark.parametrize(
    "verb,expected_yo",
    [
        ("valer", "valdré"),
        ("tener", "tendré"),
        ("poder", "podré"),
        ("salir", "saldré"),
        ("hacer", "haré"),
        ("decir", "diré"),
    ],
)
def test_future_irregular(verb, expected_yo):
    assert _forms(verb, "future")[0] == expected_yo


def test_future_regular():
    assert _forms("hablar", "future")[0] == "hablaré"


def test_reflexive_preterite():
    forms = _forms("levantarse", "preterite")
    assert forms[0] == "me levanté"
    assert forms[2] == "se levantó"


def test_invalid_verb_raises():
    with pytest.raises(ValueError):
        conjugate("xyz", "present")
