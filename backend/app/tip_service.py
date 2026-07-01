"""AI-generated Mexican culture tips with disk cache (one OpenAI call per lesson day, ever)."""

import asyncio
import json
import os
import re
from typing import Optional

import httpx

from .config import get_settings

settings = get_settings()

_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tips_cache")
os.makedirs(_CACHE_DIR, exist_ok=True)

_locks: dict[int, asyncio.Lock] = {}


def _cache_path(global_day: int) -> str:
    return os.path.join(_CACHE_DIR, f"day-{global_day:03d}.json")


def _load_cached(global_day: int) -> Optional[dict]:
    path = _cache_path(global_day)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        if all(k in data for k in ("en", "ru", "es")):
            return {"en": data["en"], "ru": data["ru"], "es": data["es"]}
    except (OSError, json.JSONDecodeError, KeyError):
        pass
    return None


def _store_cached(global_day: int, tip: dict):
    path = _cache_path(global_day)
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(tip, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except OSError:
        pass


def _recent_tips(limit: int = 12) -> list[str]:
    """Summaries of recently cached tips so the model avoids repeating them."""
    if not os.path.isdir(_CACHE_DIR):
        return []
    files = sorted(
        (f for f in os.listdir(_CACHE_DIR) if f.startswith("day-") and f.endswith(".json")),
        reverse=True,
    )[:limit]
    out = []
    for name in files:
        try:
            with open(os.path.join(_CACHE_DIR, name), encoding="utf-8") as fh:
                out.append(json.load(fh).get("en", "")[:120])
        except (OSError, json.JSONDecodeError):
            continue
    return [t for t in out if t]


def _theme_en(theme: dict) -> str:
    return (theme or {}).get("en") or "Mexican Spanish"


def _fallback_tip(global_day: int) -> dict:
    from .curriculum.mexican_tips import mexican_tip_for_day

    return mexican_tip_for_day(global_day)


async def _call_openai(global_day: int, theme_en: str, level: str, lesson_id: str) -> Optional[dict]:
    if not settings.openai_api_key:
        return None

    avoid = _recent_tips()
    avoid_block = "\n".join(f"- {t}" for t in avoid) if avoid else "(none yet)"

    system = (
        "You write short Mexican Spanish culture tips for a family language-learning app. "
        "Tips must be practical, accurate, and specific to Mexico (CDMX / central Mexican usage). "
        "Return ONLY valid JSON with keys en, ru, es — each 1-2 sentences, same meaning in all three."
    )
    user = (
        f"Lesson day {global_day} ({lesson_id}), CEFR level {level}, weekly theme: «{theme_en}».\n"
        f"Write ONE fresh tip related to this theme or daily life in Mexico.\n"
        f"Do NOT repeat or closely paraphrase these recent tips:\n{avoid_block}\n"
        "Avoid overusing «¿Qué onda?» unless you add a new angle. "
        "Prefer slang, food, politeness, markets, transport, festivals, or study advice."
    )

    url = f"{settings.openai_base_url}/chat/completions"
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    body = {
        "model": settings.openai_chat_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.9,
        "max_tokens": 280,
    }

    try:
        async with httpx.AsyncClient(timeout=45) as client:
            resp = await client.post(url, headers=headers, json=body)
        if resp.status_code != 200:
            return None
        raw = resp.json()["choices"][0]["message"]["content"]
        data = json.loads(raw)
        tip = {"en": data["en"].strip(), "ru": data["ru"].strip(), "es": data["es"].strip()}
        if not all(tip.values()):
            return None
        return tip
    except (httpx.HTTPError, KeyError, json.JSONDecodeError, IndexError):
        return None


async def resolve_lesson_tip(lesson: dict) -> Optional[dict]:
    """Return the tip dict {en, ru, es} for this lesson. Cached after first AI call."""
    theory = lesson.get("theory")
    if not theory:
        return None

    day_in_week = lesson.get("day_in_week") or 1
    global_day = lesson.get("day") or 1
    kind = lesson.get("kind", "lesson")

    # Day 1 of a regular week keeps the hand-authored topic tip from the curriculum.
    if kind == "lesson" and day_in_week == 1:
        return theory.get("tip")

    cached = _load_cached(global_day)
    if cached:
        return cached

    lock = _locks.setdefault(global_day, asyncio.Lock())
    async with lock:
        cached = _load_cached(global_day)
        if cached:
            return cached

        theme_en = _theme_en(lesson.get("theme"))
        level = lesson.get("level") or "A1"
        lesson_id = lesson.get("id") or f"day-{global_day}"

        tip = await _call_openai(global_day, theme_en, level, lesson_id)
        if tip is None:
            tip = _fallback_tip(global_day)

        _store_cached(global_day, tip)
        return tip
