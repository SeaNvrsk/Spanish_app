"""Angélica — Mexican Spanish chat companion for family learners."""

from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..deps import get_current_user
from ..models import ChatMessage, User

router = APIRouter(prefix="/api/angelica", tags=["angelica"])
settings = get_settings()

MAX_STORED = 40
MAX_CONTEXT = 18

WELCOME_ES = (
    "¡Hola! Soy Angélica 👋 Vivo en la Ciudad de México y estudio biomedicina en la UNAM — voy en tercer año. "
    "Me gusta platicar, el fútbol y salir con mis amigas. "
    "¿Cómo estás? Puedes escribirme en cualquier idioma — te entiendo. Yo respondo en español mexicano. "
    "¿Practicamos?"
)

ANGELICA_SYSTEM = """You are Angélica, a warm and friendly university student.

Identity & life:
- You live in Mexico City (Ciudad de México), Mexico.
- You are in your 3rd year (tercer año) at UNAM (Universidad Nacional Autónoma de México), studying biomedicine (biomedicina).
- You know campus life, Ciudad Universitaria, exams, labs, and student routines.
- You still love fútbol, dancing, and hanging out with friends; you have a dog named Luna.
- You know CDMX well: Santa Fe, Chapultepec, Metro, tacos, mercados, and Mexican culture.

Language rules (strict):
- Reply ONLY in Mexican Spanish (es-MX), never Spain Spanish (no vosotros, no vos).
- Use ustedes when needed; keep vocabulary clear for learners (A1–B1) unless they ask for harder words.
- Short, natural messages: usually 1–3 sentences, like texting a friend.

Personality:
- Kind, curious, supportive — a peer who helps practice Spanish, not a formal teacher.
- Share bits of student life when relevant (classes, UNAM, biomedicine in simple words).

Learners:
- Eva, Kristina, and Veronica are learning Spanish; they may write in Russian, English, or broken Spanish.
- Understand any language they use, but always answer in Spanish.
- Gently model correct Spanish; never give long grammar lectures.

Safety & character:
- Stay in character as Angélica. Never say you are an AI, a bot, or a language model.
- If asked something inappropriate, redirect kindly in Spanish to studies, hobbies, or life in CDMX."""


class ChatSendRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)


class ChatMessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    messages: list[ChatMessageOut]


class ChatSendResponse(BaseModel):
    message: ChatMessageOut


def _row_out(row: ChatMessage) -> ChatMessageOut:
    return ChatMessageOut(id=row.id, role=row.role, content=row.content, created_at=row.created_at)


def _trim_old_messages(db: Session, user_id: int):
    ids = (
        db.query(ChatMessage.id)
        .filter(ChatMessage.user_id == user_id)
        .order_by(ChatMessage.id.desc())
        .offset(MAX_STORED)
        .all()
    )
    if ids:
        db.query(ChatMessage).filter(ChatMessage.id.in_([i[0] for i in ids])).delete(synchronize_session=False)


async def _call_angelica(history: list[dict]) -> str:
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=503,
            detail="Angélica chat requires OpenAI API key (set OPENAI_API_KEY in .env)",
        )

    url = f"{settings.openai_base_url}/chat/completions"
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    messages = [{"role": "system", "content": ANGELICA_SYSTEM}]
    messages.extend(history)

    body = {
        "model": settings.openai_angelica_model,
        "messages": messages,
        "temperature": 0.85,
        "max_tokens": 350,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(url, headers=headers, json=body)
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Angélica is unavailable right now")
    reply = (resp.json()["choices"][0]["message"]["content"] or "").strip()
    if not reply:
        raise HTTPException(status_code=502, detail="Empty reply from Angélica")
    return reply


@router.get("/history", response_model=ChatHistoryResponse)
def chat_history(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == current.id)
        .order_by(ChatMessage.id.asc())
        .limit(MAX_STORED)
        .all()
    )
    if not rows:
        return ChatHistoryResponse(
            messages=[ChatMessageOut(id=0, role="assistant", content=WELCOME_ES, created_at=datetime.utcnow())]
        )
    return ChatHistoryResponse(messages=[_row_out(r) for r in rows])


@router.post("/send", response_model=ChatSendResponse)
async def chat_send(
    body: ChatSendRequest,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    text = body.message.strip()
    user_row = ChatMessage(user_id=current.id, role="user", content=text)
    db.add(user_row)
    db.commit()
    db.refresh(user_row)

    rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == current.id)
        .order_by(ChatMessage.id.asc())
        .all()
    )
    recent = rows[-MAX_CONTEXT:]
    history = [{"role": r.role, "content": r.content} for r in recent]

    reply_text = await _call_angelica(history)
    assistant_row = ChatMessage(user_id=current.id, role="assistant", content=reply_text)
    db.add(assistant_row)
    db.commit()
    db.refresh(assistant_row)
    _trim_old_messages(db, current.id)
    db.commit()

    return ChatSendResponse(message=_row_out(assistant_row))


@router.delete("/history")
def clear_history(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(ChatMessage).filter(ChatMessage.user_id == current.id).delete()
    db.commit()
    return {"ok": True}
