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
    "You are a friendly Mexican Spanish teacher from Mexico City. "
    "Read the given text in clear, natural Mexican Spanish (español mexicano) with an "
    "authentic central-Mexican (chilango) accent: seseo (pronounce c/z as 's'), clear "
    "vowels, and soft, warm intonation. Speak a little slowly and articulate each "
    "syllable so a beginner learner can follow. Do NOT translate, spell out, or add any "
    "extra words — only pronounce exactly the text provided."
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

TTS_CACHE_VERSION = "teacher-v14"

ANGELICA_TTS_INSTRUCTIONS = (
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


def _is_cognate_word(text: str) -> bool:
    """True for lone words that look identical in EN/ES and confuse TTS."""
    clean = _normalize(text)
    if not clean or " " in clean:
        return False
    token = re.sub(r"[^a-zA-ZáéíóúüñÁÉÍÓÚÜÑ¿¡]", "", clean).lower()
    return token in SPANISH_COGNATE_WORDS


def _tts_instructions(text: str, base: str) -> str:
    if _is_cognate_word(text):
        word = _normalize(text)
        return (
            f"{base} The input is ONE Spanish vocabulary word: «{word}». "
            f"Pronounce it in Mexican Spanish (Spanish vowels, Spanish rhythm) — "
            f"NOT with English pronunciation. Say only «{word}», nothing else."
        )
    return base


def _cache_key(text: str, profile: str = "teacher") -> str:
    if profile == "angelica":
        raw = (
            f"{settings.openai_tts_model}|{settings.openai_angelica_tts_voice}|"
            f"{settings.openai_angelica_tts_speed}|{settings.openai_angelica_tts_pitch_semitones}|"
            f"angelica-v13|{_normalize(text)}"
        )
    else:
        raw = f"{settings.openai_tts_model}|{settings.openai_tts_voice}|{TTS_CACHE_VERSION}|{_normalize(text)}"
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
            # Content is immutable per key, so let the browser cache aggressively.
            "Cache-Control": "public, max-age=31536000, immutable",
            "ETag": f'"{key}"',
            "X-TTS-Cache": cache_state,
        },
    )


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=300)


@router.get("/config")
def tts_config():
    """Tells the frontend whether high-quality server audio is available (no auth needed)."""
    return {"server_tts": bool(settings.openai_api_key), "provider": "openai" if settings.openai_api_key else None}


@router.post("/speak")
async def speak(payload: TTSRequest, request: Request, current: User = Depends(get_current_user)):
    return await _speak_profile(payload.text, request, profile="teacher")


@router.post("/speak/angelica")
async def speak_angelica(payload: TTSRequest, request: Request, current: User = Depends(get_current_user)):
    return await _speak_profile(payload.text, request, profile="angelica")


async def _speak_profile(text: str, request: Request, profile: str):
    if not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="Server TTS not configured")

    key = _cache_key(text, profile)

    if request.headers.get("if-none-match") == f'"{key}"':
        return Response(status_code=304, headers={"ETag": f'"{key}"', "X-TTS-Cache": "HIT-304"})

    cached = _load_cached(key)
    if cached is not None:
        return _audio_response(cached, key, "HIT")

    lock = _locks.setdefault(key, asyncio.Lock())
    async with lock:
        cached = _load_cached(key)
        if cached is not None:
            return _audio_response(cached, key, "HIT")

        voice = settings.openai_angelica_tts_voice if profile == "angelica" else settings.openai_tts_voice
        instructions = _tts_instructions(text, ANGELICA_TTS_INSTRUCTIONS if profile == "angelica" else MEXICAN_INSTRUCTIONS)

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
        # Pitch shift disabled for Angélica — ffmpeg resampling sounds cartoonish.

        _store_cached(key, audio)
        return _audio_response(audio, key, "MISS")
