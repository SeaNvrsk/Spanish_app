import asyncio
import hashlib
import os
import re
from collections import OrderedDict

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from ..config import get_settings
from ..deps import get_current_user
from ..models import User

router = APIRouter(prefix="/api/tts", tags=["tts"])
settings = get_settings()

MEXICAN_INSTRUCTIONS = (
    "CRITICAL LANGUAGE LOCK: speak ONLY Mexican Spanish (español mexicano, es-MX, "
    "Mexico City / chilango accent, seseo). English, US, or UK pronunciation is forbidden "
    "even when the spelling looks like an English word (come, me, son, no, sea, pan). "
    "You are a friendly Mexican Spanish teacher from Mexico City. "
    "Read the given text in clear, natural Mexican Spanish with authentic central-Mexican "
    "accent: seseo (pronounce c/z as 's'), clear Spanish vowels (a e i o u), and soft, warm "
    "intonation. Speak a little slowly and articulate each syllable so a beginner learner "
    "can follow. Do NOT translate, spell out, or add any extra words — only pronounce "
    "exactly the text provided."
)

# Single words spelled like English that TTS often reads with English phonetics.
SPANISH_COGNATE_WORDS = frozenset({
    "formal", "informal", "natural", "normal", "popular", "familiar",
    "similar", "digital", "personal", "social", "special", "general",
    "local", "global", "original", "ideal", "legal", "final", "total",
    "animal", "hospital", "doctor", "motor", "color", "director",
    "actor", "error", "central", "visual", "manual", "moral", "oral",
    "sexual", "cultural", "musical", "tropical",
})

TTS_CACHE_VERSION = "teacher-v17"
ANGELICA_CACHE_VERSION = "angelica-v16"

# Isolated spellings TTS otherwise reads as English.
_ENGLISH_TRAP_HINTS = {
    "come": "Mexican Spanish /ˈko.me/ (KOH-meh). NEVER the English verb 'come'.",
    "comer": "Mexican Spanish infinitive /koˈmeɾ/ (ko-MEHR, to eat). NEVER English 'comer'.",
    "como": "Mexican Spanish /ˈko.mo/ (KOH-moh). NEVER English.",
    "comes": "Mexican Spanish /ˈko.mes/ (KOH-mes). NEVER English 'comes'.",
    "comemos": "Mexican Spanish /koˈme.mos/ (ko-MEH-mohs).",
    "comen": "Mexican Spanish /ˈko.men/ (KOH-men).",
    "me": "Mexican Spanish /me/ (meh). NEVER English 'me'.",
    "te": "Mexican Spanish /te/ (teh). NEVER English 'tea'.",
    "se": "Mexican Spanish /se/ (seh). NEVER English 'say'.",
    "de": "Mexican Spanish /de/ (deh). NEVER English 'day'.",
    "a": "Mexican Spanish /a/ as in 'casa'. NEVER English letter A.",
    "el": "Mexican Spanish /el/. NEVER English letter L.",
    "la": "Mexican Spanish /la/. NEVER English 'la'.",
    "es": "Mexican Spanish /es/ of ser ('ess'). NEVER English S or 'is'.",
    "son": "Mexican Spanish /son/ (they are). NEVER English 'son'.",
    "soy": "Mexican Spanish /soi/ of ser. NEVER English 'soy sauce'.",
    "no": "Mexican Spanish /no/ (pure o). NEVER English 'no' diphthong.",
    "si": "Mexican Spanish /si/. NEVER English 'see'.",
    "sí": "Mexican Spanish /si/ (yes).",
    "sea": "Mexican Spanish /ˈse.a/ of ser. NEVER English 'sea'.",
    "once": "Mexican Spanish /ˈon.se/ (eleven). NEVER English 'once'.",
    "pan": "Mexican Spanish /pan/ (bread). NEVER English 'pan'.",
    "red": "Mexican Spanish /red/ (net). NEVER English 'red'.",
    "do": "Mexican Spanish /do/. NEVER English 'do'.",
    "so": "Mexican Spanish /so/. NEVER English 'so'.",
    "or": "Mexican Spanish /or/. NEVER English 'or'.",
    "in": "Mexican Spanish /in/. NEVER English 'in'.",
    "on": "Mexican Spanish /on/. NEVER English 'on'.",
    "he": "Mexican Spanish /e/. NEVER English 'he'.",
    "be": "Mexican Spanish /be/. NEVER English 'be'.",
    "fine": "Mexican Spanish /ˈfi.ne/. NEVER English 'fine'.",
    "normal": "Mexican Spanish /noɾˈmal/. NEVER English 'normal'.",
    "formal": "Mexican Spanish /foɾˈmal/. NEVER English 'formal'.",
}

ANGELICA_TTS_INSTRUCTIONS = (
    "CRITICAL LANGUAGE LOCK: speak ONLY Mexican Spanish (es-MX). Never English phonetics. "
    "You are Angélica, a university student from Mexico City (UNAM). "
    "Speak in clear, natural Mexican Spanish (es-MX) with chilango accent and seseo. "
    "Voice: a young Mexican woman in her early 20s — warm, friendly, natural. "
    "NOT elderly, NOT cartoon, NOT US English accent. "
    "Pace: clear and lively at this speed. "
    "Read exactly the text provided — do not add, translate, or explain anything."
)

# --- Audio cache -------------------------------------------------------------
# The same words are spoken many times (spaced repetition), so we cache the
# generated MP3 by (model, voice, text). This means each unique phrase costs
# tokens only ONCE; every later play is served for free from disk/memory.
_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "tts_cache")
os.makedirs(_CACHE_DIR, exist_ok=True)

_MEM_CACHE: "OrderedDict[str, bytes]" = OrderedDict()
_MEM_CACHE_MAX = 512                 # hottest phrases kept in RAM
_MEM_CACHE_MAX_BYTES = 200_000       # don't hold very large clips in RAM
_locks: dict[str, asyncio.Lock] = {}  # avoid generating the same phrase twice at once


def _normalize(text: str) -> str:
    """Collapse whitespace so trivially different strings share one cache entry."""
    return re.sub(r"\s+", " ", text).strip()


def _single_word(text: str) -> str | None:
    """Return the isolated token, or None for phrases/sentences."""
    clean = _normalize(text)
    if not clean or " " in clean:
        return None
    if any(ch in clean for ch in "¿?¡!."):
        return None
    token = re.sub(r"[^a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]", "", clean)
    return token or None


def _norm_letters(text: str) -> str:
    return re.sub(r"[^a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]", "", _normalize(text)).lower()


def _is_infinitive_token(word: str) -> bool:
    w = _norm_letters(word or "")
    return len(w) >= 4 and w.endswith(("ar", "er", "ir"))


def _is_known_infinitive(word: str) -> bool:
    """True only for real Spanish infinitives in the curriculum/conjugator."""
    w = _norm_letters(word or "")
    if len(w) < 4 or not w.endswith(("ar", "er", "ir")):
        return False
    from ..vocab_images import _form_to_lemma, _token_key

    lemma = _form_to_lemma().get(w)
    return bool(lemma and _token_key(lemma) == w)


def _is_speakable_spanish(text: str) -> bool:
    """Skip grammar formulas that OpenAI TTS reads as English or silence."""
    clean = _normalize(text)
    if not clean:
        return False
    low = clean.lower()
    if "+" in clean or "..." in clean or "infinitive" in low:
        return False
    if clean.startswith("-") and len(clean) <= 5:
        return False
    return True


def _looks_like_mp3(data: bytes) -> bool:
    if not data or len(data) < 800:
        return False
    if data[:3] == b"ID3":
        return True
    return data[0] == 0xFF and (data[1] & 0xE0) == 0xE0


def _candidate_infinitives(word: str, hint: str | None = None) -> list[str]:
    """Infinitives to try: UI hint, curriculum lemma, then regular reverse-guess."""
    w = _norm_letters(word or "")
    out: list[str] = []
    if hint:
        h = _norm_letters(hint)
        if h:
            out.append(h)
    if w:
        from ..vocab_images import image_lemma_for

        lemma = image_lemma_for(w)
        if lemma:
            out.append(_norm_letters(lemma))
        if _is_infinitive_token(w):
            out.append(w)
        for n in range(1, min(6, max(1, len(w) - 1))):
            stem = w[:-n]
            if len(stem) < 2:
                continue
            for end in ("er", "ir", "ar"):
                out.append(stem + end)
    seen: set[str] = set()
    uniq: list[str] = []
    for inf in out:
        if inf and inf not in seen:
            seen.add(inf)
            uniq.append(inf)
    return uniq[:24]


def _match_conjugated(infinitive: str, target: str) -> dict | None:
    from ..conjugation import TENSES, conjugate

    for tense in TENSES:
        try:
            data = conjugate(infinitive, tense)
        except ValueError:
            continue
        for row in data.get("forms") or []:
            if _norm_letters(row.get("form") or "") == target:
                return {
                    "form": target,
                    "infinitive": infinitive,
                    "pronoun": row.get("pronoun") or "",
                    "tense": tense,
                }
    return None


def _verb_form_meta(text: str, hint_infinitive: str | None = None) -> dict | None:
    """Conjugated form → infinitive. Works for conjugator verbs, not only lessons."""
    word = _single_word(text)
    if not word:
        return None
    target = _norm_letters(word)
    if _is_infinitive_token(word) and not hint_infinitive:
        return None
    if hint_infinitive and _norm_letters(hint_infinitive) == target and _is_infinitive_token(word):
        return None
    for inf in _candidate_infinitives(word, hint_infinitive):
        if inf == target:
            continue
        hit = _match_conjugated(inf, target)
        if hit:
            hit["form"] = word
            return hit
    return None


def _is_cognate_word(text: str) -> bool:
    """True for lone words that look identical in EN/ES and confuse TTS."""
    token = _single_word(text)
    if not token:
        return False
    return token.lower() in SPANISH_COGNATE_WORDS


def _trap_hint(word: str) -> str:
    return _ENGLISH_TRAP_HINTS.get(_norm_letters(word), "")


def _tts_instructions(text: str, base: str, hint_infinitive: str | None = None) -> str:
    extra = []
    word = _single_word(text)
    meta = _verb_form_meta(text, hint_infinitive)
    trap = _trap_hint(word or text)
    if meta:
        extra.append(
            f"The input is ONE conjugated Mexican Spanish verb: «{meta['form']}», "
            f"the {meta['pronoun'] or 'conjugated'} form of {meta['infinitive']} "
            f"({meta['tense'] or 'present'} tense). "
            "Pronounce it with Spanish vowels (a e i o u), seseo, and Spanish rhythm. "
            "Stress the penultimate syllable unless there is a written accent. "
            f"This is NOT English. Say only «{meta['form']}» — do not say the infinitive "
            f"{meta['infinitive']} or any extra words."
        )
    elif word and (_is_known_infinitive(word) or (hint_infinitive and _norm_letters(hint_infinitive) == _norm_letters(word) and _is_known_infinitive(word))):
        extra.append(
            f"The input is the Spanish INFINITIVE «{word}» (Mexican Spanish). "
            "Pronounce it as Mexican Spanish with stress on the last syllable. "
            f"Say only «{word}». NEVER English."
        )
    elif _is_cognate_word(text):
        extra.append(
            f"The input is ONE Spanish vocabulary word: «{word}». "
            "Pronounce it in Mexican Spanish (Spanish vowels, Spanish rhythm) — "
            f"NOT with English pronunciation. Say only «{word}», nothing else."
        )
    elif word:
        extra.append(
            f"The input is ONE Mexican Spanish word: «{word}». "
            "Use Spanish vowels and stress; do NOT switch to English. "
            f"Say only «{word}»."
        )
    if trap:
        extra.append(trap)
    if not extra:
        return base
    return f"{base} {' '.join(extra)}"


def _cache_key(text: str, profile: str = "teacher", hint_infinitive: str = "") -> str:
    hint = _norm_letters(hint_infinitive) if hint_infinitive else ""
    if profile == "angelica":
        raw = (
            f"{settings.openai_tts_model}|{settings.openai_angelica_tts_voice}|"
            f"{settings.openai_angelica_tts_speed}|{settings.openai_angelica_tts_pitch_semitones}|"
            f"{ANGELICA_CACHE_VERSION}|{hint}|{_normalize(text)}"
        )
    else:
        raw = f"{settings.openai_tts_model}|{settings.openai_tts_voice}|{TTS_CACHE_VERSION}|{hint}|{_normalize(text)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _cache_path(key: str) -> str:
    return os.path.join(_CACHE_DIR, f"{key}.mp3")


def _mem_get(key: str):
    data = _MEM_CACHE.get(key)
    if data is not None:
        _MEM_CACHE.move_to_end(key)
    return data


def _mem_put(key: str, data: bytes):
    if len(data) > _MEM_CACHE_MAX_BYTES:
        return
    _MEM_CACHE[key] = data
    _MEM_CACHE.move_to_end(key)
    while len(_MEM_CACHE) > _MEM_CACHE_MAX:
        _MEM_CACHE.popitem(last=False)


def _load_cached(key: str):
    data = _mem_get(key)
    if data is not None:
        return data
    path = _cache_path(key)
    if os.path.isfile(path):
        try:
            with open(path, "rb") as fh:
                data = fh.read()
            _mem_put(key, data)
            return data
        except OSError:
            return None
    return None


def _store_cached(key: str, data: bytes):
    _mem_put(key, data)
    try:
        tmp = _cache_path(key) + ".tmp"
        with open(tmp, "wb") as fh:
            fh.write(data)
        os.replace(tmp, _cache_path(key))
    except OSError:
        pass


def _audio_response(data: bytes, key: str, cache_state: str) -> Response:
    return Response(
        content=data,
        media_type="audio/mpeg",
        headers={
            # Same URL for every word (POST /tts/speak). Do not let Safari /
            # Cloudflare reuse clip #1 on the next lesson.
            "Cache-Control": "private, no-store, no-cache",
            "ETag": f'"{key}"',
            "X-TTS-Cache": cache_state,
        },
    )


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=300)
    infinitive: str = Field(default="", max_length=80)


@router.get("/config")
def tts_config():
    """Tells the frontend whether high-quality server audio is available (no auth needed)."""
    return {"server_tts": bool(settings.openai_api_key), "provider": "openai" if settings.openai_api_key else None}


@router.post("/speak")
async def speak(payload: TTSRequest, request: Request, current: User = Depends(get_current_user)):
    return await _speak_profile(payload.text, request, profile="teacher", hint_infinitive=payload.infinitive)


@router.post("/speak/angelica")
async def speak_angelica(payload: TTSRequest, request: Request, current: User = Depends(get_current_user)):
    return await _speak_profile(payload.text, request, profile="angelica", hint_infinitive=payload.infinitive)


async def _speak_profile(text: str, request: Request, profile: str, hint_infinitive: str = ""):
    if not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="Server TTS not configured")

    if not _is_speakable_spanish(text):
        raise HTTPException(status_code=400, detail="Text is not speakable Spanish")

    hint = (hint_infinitive or "").strip()
    key = _cache_key(text, profile, hint)

    cached = _load_cached(key)
    if cached is not None:
        return _audio_response(cached, key, "HIT")

    lock = _locks.setdefault(key, asyncio.Lock())
    async with lock:
        cached = _load_cached(key)
        if cached is not None:
            return _audio_response(cached, key, "HIT")

        voice = settings.openai_angelica_tts_voice if profile == "angelica" else settings.openai_tts_voice
        instructions = _tts_instructions(
            text,
            ANGELICA_TTS_INSTRUCTIONS if profile == "angelica" else MEXICAN_INSTRUCTIONS,
            hint or None,
        )

        url = f"{settings.openai_base_url}/audio/speech"
        headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
        body = {
            "model": settings.openai_tts_model,
            "voice": voice,
            "input": text,
            "instructions": instructions,
            "response_format": "mp3",
        }
        if profile == "angelica":
            body["speed"] = settings.openai_angelica_tts_speed
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(url, headers=headers, json=body)
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"TTS upstream error: {exc}") from exc

        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="TTS provider error")

        audio = resp.content
        if not _looks_like_mp3(audio):
            raise HTTPException(status_code=502, detail="TTS provider returned invalid audio")

        _store_cached(key, audio)
        return _audio_response(audio, key, "MISS")
