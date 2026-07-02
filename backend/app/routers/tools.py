"""Family tools: RU→Mexican Spanish translator (AI) and verb conjugator."""

import hashlib
import json
import os
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..config import get_settings
from ..conjugation import TENSES, conjugate
from ..deps import get_current_user
from ..models import User

router = APIRouter(prefix="/api/tools", tags=["tools"])
settings = get_settings()

_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "translate_cache")
_EXPLAIN_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "explain_cache")
os.makedirs(_CACHE_DIR, exist_ok=True)
os.makedirs(_EXPLAIN_CACHE_DIR, exist_ok=True)


class TranslateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500)


class TranslateResponse(BaseModel):
    russian: str
    spanish: str
    note: Optional[str] = None
    cached: bool = False


class ConjugateRequest(BaseModel):
    verb: str = Field(min_length=2, max_length=40)
    tense: str = "present"


class ConjugateResponse(BaseModel):
    verb: str
    infinitive: str
    tense: str
    pronouns_note: str
    forms: list[dict]


class ExplainRequest(BaseModel):
    spanish: str = Field(min_length=1, max_length=200)
    context_en: str = ""
    context_ru: str = ""


class ExplainResponse(BaseModel):
    spanish: str
    meaning: str
    mexico_usage: str
    example: str
    cached: bool = False


def _cache_key(text: str) -> str:
    return hashlib.sha256(_norm_key(text).encode()).hexdigest()


def _norm_key(text: str) -> str:
    return " ".join(text.strip().lower().split())


def _load_translation(key: str) -> Optional[dict]:
    path = os.path.join(_CACHE_DIR, f"{key}.json")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


def _store_translation(key: str, data: dict):
    path = os.path.join(_CACHE_DIR, f"{key}.json")
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except OSError:
        pass


def _load_explain(key: str) -> Optional[dict]:
    path = os.path.join(_EXPLAIN_CACHE_DIR, f"{key}.json")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


def _store_explain(key: str, data: dict):
    path = os.path.join(_EXPLAIN_CACHE_DIR, f"{key}.json")
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except OSError:
        pass


async def _translate_ai(text: str) -> dict:
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=503,
            detail="Translation requires OpenAI API key (set OPENAI_API_KEY in .env)",
        )

    system = (
        "You translate Russian into MEXICAN Spanish (es-MX), NOT Spain/Castilian Spanish. "
        "Rules: use 'ustedes' (never vosotros); prefer Mexican vocabulary and phrasing "
        "(e.g. '¿Qué onda?', 'platicar', 'chido' only when natural); neutral register unless "
        "the source is clearly informal. Return ONLY valid JSON: "
        '{"spanish": "...", "note": "optional 1 short sentence about Mexican usage or null"}'
    )
    user = f"Translate to Mexican Spanish:\n{text}"

    url = f"{settings.openai_base_url}/chat/completions"
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    body = {
        "model": settings.openai_chat_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.4,
        "max_tokens": 400,
    }

    async with httpx.AsyncClient(timeout=45) as client:
        resp = await client.post(url, headers=headers, json=body)
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Translation service error")
    raw = resp.json()["choices"][0]["message"]["content"]
    data = json.loads(raw)
    spanish = (data.get("spanish") or "").strip()
    if not spanish:
        raise HTTPException(status_code=502, detail="Empty translation")
    note = data.get("note")
    if note:
        note = str(note).strip() or None
    return {"spanish": spanish, "note": note}


async def _explain_ai(spanish: str, context_en: str, context_ru: str) -> dict:
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=503,
            detail="Explanation requires OpenAI API key (set OPENAI_API_KEY in .env)",
        )

    gloss_parts = []
    if context_en:
        gloss_parts.append(f"English gloss: {context_en}")
    if context_ru:
        gloss_parts.append(f"Russian gloss: {context_ru}")
    gloss = "\n".join(gloss_parts) if gloss_parts else "No translation provided."

    system = (
        "You teach Mexican Spanish (es-MX) to a family learner. "
        "Explain the given word or short phrase clearly and practically. "
        "Focus on how it is used in Mexico (register, context, alternatives). "
        "Return ONLY valid JSON: "
        '{"meaning": "short core meaning", "mexico_usage": "2-3 sentences about Mexican usage", '
        '"example": "one natural Mexican Spanish example sentence"}'
    )
    user = f"Word/phrase: {spanish}\n{gloss}"

    url = f"{settings.openai_base_url}/chat/completions"
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    body = {
        "model": settings.openai_chat_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.5,
        "max_tokens": 450,
    }

    async with httpx.AsyncClient(timeout=45) as client:
        resp = await client.post(url, headers=headers, json=body)
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Explanation service error")
    raw = resp.json()["choices"][0]["message"]["content"]
    data = json.loads(raw)
    meaning = (data.get("meaning") or "").strip()
    mexico_usage = (data.get("mexico_usage") or "").strip()
    example = (data.get("example") or "").strip()
    if not meaning or not mexico_usage:
        raise HTTPException(status_code=502, detail="Empty explanation")
    return {"meaning": meaning, "mexico_usage": mexico_usage, "example": example or meaning}


@router.get("/tenses")
def list_tenses(_: User = Depends(get_current_user)):
    return {"tenses": list(TENSES)}


@router.post("/translate", response_model=TranslateResponse)
async def translate_ru_to_mx(body: TranslateRequest, _: User = Depends(get_current_user)):
    text = body.text.strip()
    key = _cache_key(text)
    cached = _load_translation(key)
    if cached:
        return TranslateResponse(
            russian=text,
            spanish=cached["spanish"],
            note=cached.get("note"),
            cached=True,
        )

    result = await _translate_ai(text)
    _store_translation(key, result)
    return TranslateResponse(russian=text, spanish=result["spanish"], note=result.get("note"), cached=False)


@router.post("/conjugate", response_model=ConjugateResponse)
def conjugate_verb(body: ConjugateRequest, _: User = Depends(get_current_user)):
    try:
        out = conjugate(body.verb, body.tense)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ConjugateResponse(**out)


@router.post("/explain", response_model=ExplainResponse)
async def explain_spanish(body: ExplainRequest, _: User = Depends(get_current_user)):
    spanish = body.spanish.strip()
    key = _cache_key(f"{spanish}|{body.context_en}|{body.context_ru}")
    cached = _load_explain(key)
    if cached:
        return ExplainResponse(
            spanish=spanish,
            meaning=cached["meaning"],
            mexico_usage=cached["mexico_usage"],
            example=cached.get("example") or cached["meaning"],
            cached=True,
        )

    result = await _explain_ai(spanish, body.context_en.strip(), body.context_ru.strip())
    _store_explain(key, result)
    return ExplainResponse(spanish=spanish, cached=False, **result)
