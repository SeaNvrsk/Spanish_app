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
from ..msk_time import msk_today, msk_now
from ..gamification import (
    update_streak,
    bump_daily,
    get_daily,
    apply_review_award,
    REVIEW_DAILY_CAP_TENTHS,
    REVIEW_DAILY_PESOS_CAP,
    REVIEW_TENTHS_PER_CORRECT,
)

router = APIRouter(prefix="/api/review", tags=["review"])

DAILY_QUEUE_LIMIT = 20
REVIEW_PESOS_PER_CARD = REVIEW_TENTHS_PER_CORRECT / 10  # 0.1 for API hints


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
    card.due = msk_today() + timedelta(days=card.interval)
    card.last_reviewed = msk_now().replace(tzinfo=None)


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
                ease=2.5, interval=0, reps=0, lapses=0, due=msk_today(),
            )
            db.add(card)
        cache[item.word_es] = card
        _apply_sm2(card, item.correct)
        if item.correct:
            correct_count += 1
        updated += 1

    pesos_earned = 0.0
    if payload.award_pesos and correct_count:
        today = msk_today()
        daily = get_daily(db, current, today)
        already_tenths = daily.review_pesos or 0
        award = apply_review_award(current, correct_count, already_tenths)
        if award["earned_tenths"] > 0:
            bump_daily(
                db,
                current,
                today,
                award["pesos_whole"],
                completed=False,
                review_pesos=award["earned_tenths"],
            )
            update_streak(current, today)
            pesos_earned = award["pesos_display"]

    db.commit()
    return {"updated": updated, "pesos_earned": pesos_earned, "total_pesos": current.pesos}


@router.get("/status")
def status(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    today = msk_today()
    total = db.query(Card).filter(Card.user_id == current.id).count()
    due = db.query(Card).filter(Card.user_id == current.id, Card.due <= today).count()
    practice = min(total, DAILY_QUEUE_LIMIT)
    daily = (
        db.query(DailyActivity)
        .filter(DailyActivity.user_id == current.id, DailyActivity.day == today)
        .first()
    )
    review_tenths_today = (daily.review_pesos or 0) if daily else 0
    return {
        "total_cards": total,
        "due": due,
        "practice_available": practice,
        "review_pesos_today": round(review_tenths_today / 10, 1),
        "review_pesos_cap": REVIEW_DAILY_PESOS_CAP,
        "review_tenths_remaining": max(0, REVIEW_DAILY_CAP_TENTHS - review_tenths_today),
    }


@router.get("/queue")
def queue(
    mode: str = "due",
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """due = SRS words due today; practice = relearn any saved words from lessons."""
    today = msk_today()
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
        "pesos_per_card": REVIEW_PESOS_PER_CARD,
        "exercises": exercises,
    }
