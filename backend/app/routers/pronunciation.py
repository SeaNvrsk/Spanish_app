import httpx
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form

from ..config import get_settings
from ..deps import get_current_user
from ..models import User
from ..pronunciation_score import PronunciationResult, score_pronunciation

router = APIRouter(prefix="/api/pronunciation", tags=["pronunciation"])
settings = get_settings()


async def _transcribe(client: httpx.AsyncClient, data: bytes, filename: str, content_type: str, prompt: str) -> str:
    url = f"{settings.openai_base_url}/audio/transcriptions"
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    files = {"file": (filename, data, content_type)}
    form = {
        "model": "whisper-1",
        "language": "es",
        "response_format": "json",
        "prompt": prompt,
    }
    resp = await client.post(url, headers=headers, files=files, data=form)
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Transcription provider error")
    return resp.json().get("text", "")


def _pick_best(target: str, transcripts: list[str]) -> tuple[PronunciationResult, str]:
    """Prefer exact ASR match; otherwise best passing score."""
    best_result = PronunciationResult(0, False, False)
    best_raw = transcripts[0] if transcripts else ""

    for text in transcripts:
        if not text:
            continue
        result = score_pronunciation(target, text)
        if result.passed and not result.asr_corrected:
            return result, text
        if result.passed and (not best_result.passed or result.score > best_result.score):
            best_result, best_raw = result, text
        elif not best_result.passed and result.score > best_result.score:
            best_result, best_raw = result, text

    return best_result, best_raw


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

    target = target.strip()
    filename = audio.filename or "speech.webm"
    content_type = audio.content_type or "audio/webm"

    prompts = [
        target,
        f"Palabra en español: {target}",
        f"El estudiante repite: {target}",
    ]

    transcripts: list[str] = []
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            for prompt in prompts:
                transcripts.append(await _transcribe(client, data, filename, content_type, prompt))
                result = score_pronunciation(target, transcripts[-1])
                if result.passed and not result.asr_corrected:
                    break
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Transcription error: {exc}")

    result, raw = _pick_best(target, transcripts)
    display_transcript = target if result.asr_corrected else (raw or target)

    return {
        "transcript": display_transcript,
        "raw_transcript": raw if result.asr_corrected else None,
        "score": result.score,
        "passed": result.passed,
        "asr_corrected": result.asr_corrected,
        "target": target,
    }
