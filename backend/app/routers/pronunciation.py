import difflib
import re

import httpx
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form

from ..config import get_settings
from ..deps import get_current_user
from ..models import User

router = APIRouter(prefix="/api/pronunciation", tags=["pronunciation"])
settings = get_settings()


def _normalize(s: str) -> str:
    s = s.lower().strip()
    s = s.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ü", "u").replace("ñ", "n")
    s = re.sub(r"[¿?¡!.,;:\"']", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


@router.get("/config")
def config(current: User = Depends(get_current_user)):
    return {"available": bool(settings.openai_api_key)}


@router.post("/check")
async def check(
    target: str = Form(...),
    audio: UploadFile = File(...),
    current: User = Depends(get_current_user),
):
    """Transcribe the learner's recording and score how close it is to the target."""
    if not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="Pronunciation check not configured")

    data = await audio.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty audio")

    filename = audio.filename or "speech.webm"
    content_type = audio.content_type or "audio/webm"

    url = f"{settings.openai_base_url}/audio/transcriptions"
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    files = {"file": (filename, data, content_type)}
    form = {"model": "whisper-1", "language": "es", "response_format": "json"}

    try:
        async with httpx.AsyncClient(timeout=45) as client:
            resp = await client.post(url, headers=headers, files=files, data=form)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Transcription error: {exc}")

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Transcription provider error")

    transcript = resp.json().get("text", "")
    a, b = _normalize(target), _normalize(transcript)
    ratio = difflib.SequenceMatcher(None, a, b).ratio() if a else 0.0
    score = round(ratio * 100)
    passed = score >= 70

    return {"transcript": transcript, "score": score, "passed": passed, "target": target}
