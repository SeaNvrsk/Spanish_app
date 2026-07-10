"""Curated usage examples for lesson phrases (fallback before AI explain)."""

from __future__ import annotations

import re
import unicodedata
from typing import Optional


def _norm_phrase(text: str) -> str:
    t = unicodedata.normalize("NFD", text.strip().lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^\w\s]", " ", t)
    return " ".join(t.split())


# key = normalized Spanish phrase
CURATED: dict[str, dict] = {
    "como amanecio": {
        "explanation_ru": (
            "Утреннее приветствие в Мексике: спрашивают, как прошло утро или как человек "
            "себя чувствует с утра. Форма «amaneció» — вежливое обращение на «usted». "
            "Это не буквальный вопрос «как вы проснулись»."
        ),
        "examples": [
            {
                "es": "¿Cómo amaneció, señora García?",
                "ru": "Как ваше утро, señora García?",
            },
            {
                "es": "Bien, gracias. ¿Y usted cómo amaneció?",
                "ru": "Хорошо, спасибо. А у вас как утро?",
            },
        ],
    },
}


def lookup_usage_examples(spanish: str) -> Optional[dict]:
    key = _norm_phrase(spanish)
    hit = CURATED.get(key)
    if not hit:
        return None
    examples = hit.get("examples") or []
    if len(examples) < 2:
        return None
    return {
        "explanation_ru": hit["explanation_ru"].strip(),
        "examples": [{"es": e["es"].strip(), "ru": e["ru"].strip()} for e in examples[:2]],
    }
