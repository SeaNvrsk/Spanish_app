"""Conjugated verb forms share one flashcard image (the infinitive)."""

from app.vocab_images import (
    image_canonical_word,
    image_file_for,
    image_lemma_for,
    image_url_for,
    vocab_slug,
)


def test_hablar_conjugations_share_lemma():
    assert image_lemma_for("hablo") == "hablar"
    assert image_lemma_for("hablas") == "hablar"
    assert image_lemma_for("habla") == "hablar"
    assert image_lemma_for("hablamos") == "hablar"
    assert image_canonical_word("hablo") == "hablar"
    assert image_lemma_for("hablar") is None


def test_trabajar_estudio_lemmas():
    assert image_lemma_for("trabajo") == "trabajar"
    assert image_lemma_for("estudio") == "estudiar"


def test_phrases_not_collapsed():
    assert image_lemma_for("Yo hablo español.") is None
    assert image_canonical_word("Yo hablo español.") == "Yo hablo español."


def test_shared_file_when_infinitive_cached():
    # Requires hablar.webp from Unsplash cache on this server.
    path_inf = image_file_for("hablar")
    if not path_inf:
        return
    assert image_file_for("hablo") == path_inf
    assert image_file_for("hablas") == path_inf
    url = image_url_for("hablo")
    assert url and f"/api/images/vocab/{vocab_slug('hablar')}" in url
