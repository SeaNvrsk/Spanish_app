from app.usage_examples import lookup_usage_examples


def test_amanecio_curated_examples():
    hit = lookup_usage_examples("¿Cómo amaneció?")
    assert hit is not None
    assert "утро" in hit["explanation_ru"].lower()
    assert len(hit["examples"]) == 2
    assert hit["examples"][0]["ru"]
    assert hit["examples"][1]["ru"]


def test_unknown_phrase_returns_none():
    assert lookup_usage_examples("xyznotfound") is None
