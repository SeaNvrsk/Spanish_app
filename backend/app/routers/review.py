from datetime import date, timedelta, datetime
from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User, Card, DailyActivity
from ..curriculum.builder import build_quiz, all_vocab_pool
from ..vocab_images import attach_image
from ..gamification import update_streak, bump_daily, REVIEW_DAILY_PESOS_CAP

router = APIRouter(prefix="/api/review", tags=["review"])

REVIEW_PESOS_PER_CARD = 1
DAILY_QUEUE_LIMIT = 20


class GradeItem(BaseModel):
    word_es: str
    word_en: str = ""
    word_ru: str = ""
    correct: bool


class GradePayload(BaseModel):
    items: List[GradeItem]
    award_pesos: bool = False


def _apply_sm2(card: Card, correct: bool):
    if correct:
        card.reps += 1
        if card.reps == 1:
            card.interval = 1
        elif card.reps == 2:
            card.interval = 3
        else:
            card.interval = max(1, round(card.interval * card.ease))
        card.ease = min(3.0, card.ease + 0.1)
    else:
        card.reps = 0
        card.lapses += 1
        card.interval = 1
        card.ease = max(1.3, card.ease - 0.2)
    card.due = date.today() + timedelta(days=card.interval)
    card.last_reviewed = datetime.utcnow()


@router.post("/grade")
def grade(payload: GradePayload, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    updated = 0
    correct_count = 0
    cache = {}
    for item in payload.items:
        if not item.word_es:
            continue
        card = cache.get(item.word_es)
        if card is None:
            card = (
                db.query(Card)
                .filter(Card.user_id == current.id, Card.word_es == item.word_es)
                .first()
            )
        if card is None:
            card = Card(
                user_id=current.id, word_es=item.word_es,
                word_en=item.word_en or "", word_ru=item.word_ru or "",
                ease=2.5, interval=0, reps=0, lapses=0, due=date.today(),
            )
            db.add(card)
        cache[item.word_es] = card
        _apply_sm2(card, item.correct)
        if item.correct:
            correct_count += 1
        updated += 1

    pesos_earned = 0
    if payload.award_pesos and correct_count:
        today = date.today()
        today_row = (
            db.query(DailyActivity)
            .filter(DailyActivity.user_id == current.id, DailyActivity.day == today)
            .first()
        )
        already = (today_row.review_pesos or 0) if today_row else 0
        allowed = max(0, REVIEW_DAILY_PESOS_CAP - already)
        pesos_earned = min(correct_count * REVIEW_PESOS_PER_CARD, allowed)
        if pesos_earned > 0:
            current.pesos += pesos_earned
            update_streak(current, today)
            bump_daily(db, current, today, pesos_earned, completed=False, review_pesos=pesos_earned)

    db.commit()
    return {"updated": updated, "pesos_earned": pesos_earned, "total_pesos": current.pesos}


@router.get("/status")
def status(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    today = date.today()
    total = db.query(Card).filter(Card.user_id == current.id).count()
    due = db.query(Card).filter(Card.user_id == current.id, Card.due <= today).count()
    practice = min(total, DAILY_QUEUE_LIMIT)
    return {"total_cards": total, "due": due, "practice_available": practice}


@router.get("/queue")
def queue(
    mode: str = "due",
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """due = SRS words due today; practice = relearn any saved words from lessons."""
    today = date.today()
    q = db.query(Card).filter(Card.user_id == current.id)
    if mode == "practice":
        cards = (
            q.order_by(Card.last_reviewed.asc().nullsfirst(), Card.word_es.asc())
            .limit(DAILY_QUEUE_LIMIT)
            .all()
        )
    else:
        cards = (
            q.filter(Card.due <= today)
            .order_by(Card.due.asc())
            .limit(DAILY_QUEUE_LIMIT)
            .all()
        )
    vocab = [
        attach_image({"es": c.word_es, "translations": {"en": c.word_en, "ru": c.word_ru}})
        for c in cards
    ]
    exercises = build_quiz(vocab, all_vocab_pool(), seed=f"review-{current.id}-{today}-{mode}") if vocab else []
    return {
        "mode": mode,
        "count": len(vocab),
        "pesos_per_card": REVIEW_PESOS_PER_CARD if mode == "due" else 0,
        "exercises": exercises,
    }
