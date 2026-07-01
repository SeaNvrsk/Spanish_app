from datetime import date, timedelta, datetime
from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User, Card, DailyActivity
from ..curriculum.builder import build_quiz, all_vocab_pool
from ..gamification import update_streak, bump_daily, REVIEW_DAILY_XP_CAP

router = APIRouter(prefix="/api/review", tags=["review"])

REVIEW_XP_PER_CARD = 2
DAILY_QUEUE_LIMIT = 20


class GradeItem(BaseModel):
    word_es: str
    word_en: str = ""
    word_ru: str = ""
    correct: bool


class GradePayload(BaseModel):
    items: List[GradeItem]
    award_xp: bool = False  # True when this is a standalone Daily Review session


def _apply_sm2(card: Card, correct: bool):
    """Lightweight SM-2: correct pushes the interval out (1→3→8→20...);
    a mistake resets it and lowers ease, so the word comes back sooner."""
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
    """Feed word results (from a lesson or a review session) into the SRS scheduler."""
    updated = 0
    correct_count = 0
    cache = {}  # reuse the same Card object if a word repeats within this payload
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

    xp_earned = 0
    if payload.award_xp and correct_count:
        today = date.today()
        # Anti-inflation cap: at most REVIEW_DAILY_XP_CAP review XP per day.
        today_row = (
            db.query(DailyActivity)
            .filter(DailyActivity.user_id == current.id, DailyActivity.day == today)
            .first()
        )
        already = (today_row.review_xp or 0) if today_row else 0
        allowed = max(0, REVIEW_DAILY_XP_CAP - already)
        xp_earned = min(correct_count * REVIEW_XP_PER_CARD, allowed)
        if xp_earned > 0:
            current.xp += xp_earned
            update_streak(current, today)
            bump_daily(db, current, today, xp_earned, completed=False, review_xp=xp_earned)

    db.commit()
    return {"updated": updated, "xp_earned": xp_earned, "total_xp": current.xp}


@router.get("/status")
def status(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    today = date.today()
    total = db.query(Card).filter(Card.user_id == current.id).count()
    due = db.query(Card).filter(Card.user_id == current.id, Card.due <= today).count()
    return {"total_cards": total, "due": due}


@router.get("/queue")
def queue(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return today's due cards turned into quiz exercises for a Daily Review."""
    today = date.today()
    cards = (
        db.query(Card)
        .filter(Card.user_id == current.id, Card.due <= today)
        .order_by(Card.due.asc())
        .limit(DAILY_QUEUE_LIMIT)
        .all()
    )
    vocab = [
        {"es": c.word_es, "translations": {"en": c.word_en, "ru": c.word_ru}}
        for c in cards
    ]
    exercises = build_quiz(vocab, all_vocab_pool(), seed=f"review-{current.id}-{today}") if vocab else []
    return {
        "count": len(vocab),
        "xp_per_card": REVIEW_XP_PER_CARD,
        "exercises": exercises,
    }
