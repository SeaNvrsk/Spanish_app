from datetime import date, timedelta, datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User, Card, DailyActivity
from ..curriculum.builder import build_quiz, all_vocab_pool, repair_card_vocab
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
MAX_REVIEW_INTERVAL_DAYS = 365
LEARNER_REPS_CAP = 3


class GradeItem(BaseModel):
    word_es: str
    word_en: str = ""
    word_ru: str = ""
    correct: bool


class GradePayload(BaseModel):
    items: List[GradeItem]
    award_pesos: bool = False


def _cap_interval(interval: int) -> int:
    return max(1, min(int(interval or 0), MAX_REVIEW_INTERVAL_DAYS))


def _sanitize_card(card: Card) -> bool:
    """Clamp corrupted SRS values so due dates never overflow."""
    changed = False
    capped = _cap_interval(card.interval)
    if card.interval != capped:
        card.interval = capped
        changed = True
    if card.ease > 3.0:
        card.ease = 3.0
        changed = True
    elif card.ease < 1.3:
        card.ease = 1.3
        changed = True
    today = msk_today()
    max_due = today + timedelta(days=MAX_REVIEW_INTERVAL_DAYS)
    if card.due > max_due:
        card.due = today + timedelta(days=card.interval)
        changed = True
    return changed


def lesson_flashcard_vocab(lesson: dict) -> List[dict]:
    """All new words introduced in a lesson (flashcard preview)."""
    out: List[dict] = []
    seen: set[str] = set()
    for ex in lesson.get("exercises", []):
        if ex.get("type") != "flashcard":
            continue
        es = (ex.get("es") or "").strip()
        if not es or es in seen:
            continue
        seen.add(es)
        tr = ex.get("translations") or {}
        out.append({"es": es, "en": tr.get("en", ""), "ru": tr.get("ru", "")})
    return out


def _get_or_create_card(db, user_id: int, item: GradeItem, cache: Dict[str, Card]) -> Card:
    card = cache.get(item.word_es)
    if card is None:
        card = (
            db.query(Card)
            .filter(Card.user_id == user_id, Card.word_es == item.word_es)
            .first()
        )
    if card is None:
        # Atomic upsert: the lesson finish screen fires /review/grade and
        # /lessons/{id}/complete (which also seeds cards) close together, so a
        # plain "check then insert" can race and hit the unique constraint on
        # (user_id, word_es). That used to crash the whole request and roll
        # back pesos/streak/progress that had already been computed. Using
        # ON CONFLICT DO NOTHING makes card creation race-safe.
        stmt = (
            sqlite_insert(Card)
            .values(
                user_id=user_id,
                word_es=item.word_es,
                word_en=item.word_en or "",
                word_ru=item.word_ru or "",
                ease=2.5,
                interval=0,
                reps=0,
                lapses=0,
                due=msk_today(),
            )
            .on_conflict_do_nothing(index_elements=["user_id", "word_es"])
        )
        db.execute(stmt)
        db.flush()
        card = (
            db.query(Card)
            .filter(Card.user_id == user_id, Card.word_es == item.word_es)
            .first()
        )
    elif item.word_en or item.word_ru:
        card.word_en = item.word_en or card.word_en
        card.word_ru = item.word_ru or card.word_ru
    cache[item.word_es] = card
    _sanitize_card(card)
    return card


def _dedupe_grade_items(items: List[GradeItem]) -> List[GradeItem]:
    """One update per word; any wrong answer marks the word wrong."""
    merged: Dict[str, GradeItem] = {}
    for item in items:
        if not item.word_es:
            continue
        prev = merged.get(item.word_es)
        if prev is None:
            merged[item.word_es] = item
        elif not item.correct:
            merged[item.word_es] = item
    return list(merged.values())


def _apply_lesson_touch(card: Card):
    """Lesson finish: add/update words without pushing SRS intervals far ahead."""
    today = msk_today()
    card.due = today
    if card.interval <= 0:
        card.interval = 1
    card.last_reviewed = msk_now().replace(tzinfo=None)


def seed_lesson_cards(db: Session, user_id: int, lesson: dict) -> int:
    """Ensure every flashcard word from a completed lesson is in the review deck."""
    today = msk_today()
    added = 0
    cache: Dict[str, Card] = {}
    for vocab in lesson_flashcard_vocab(lesson):
        item = GradeItem(word_es=vocab["es"], word_en=vocab["en"], word_ru=vocab["ru"], correct=True)
        card = _get_or_create_card(db, user_id, item, cache)
        is_new = card.reps == 0 and card.lapses == 0 and (card.last_reviewed is None)
        card.due = today
        if card.interval <= 0:
            card.interval = 1
        if is_new:
            added += 1
    return added


def rebalance_learner_cards(db: Session, user_id: int) -> int:
    """Pull still-learning words back into today's review pool."""
    today = msk_today()
    changed = 0
    cards = db.query(Card).filter(Card.user_id == user_id, Card.reps < LEARNER_REPS_CAP).all()
    for card in cards:
        if card.due > today + timedelta(days=1):
            card.due = today
            card.interval = min(_cap_interval(card.interval), 1)
            changed += 1
    return changed


def _card_review_priority(card: Card, today: date) -> tuple:
    if card.due <= today:
        return (0, card.due.toordinal(), card.word_es)
    if card.reps < LEARNER_REPS_CAP:
        return (1, card.due.toordinal(), card.word_es)
    if card.due <= today + timedelta(days=7):
        return (2, card.due.toordinal(), card.word_es)
    return (3, card.due.toordinal(), card.word_es)


def _review_queue_cards(db: Session, user_id: int, limit: int = DAILY_QUEUE_LIMIT) -> List[Card]:
    """Daily review queue: due today first, then still-learning words."""
    today = msk_today()
    cards = db.query(Card).filter(Card.user_id == user_id).all()
    cards.sort(key=lambda c: _card_review_priority(c, today))
    return cards[:limit]


def _reviewable_count(db: Session, user_id: int) -> int:
    today = msk_today()
    total = db.query(Card).filter(Card.user_id == user_id).count()
    if total == 0:
        return 0
    ready = sum(
        1
        for c in db.query(Card).filter(Card.user_id == user_id).all()
        if c.due <= today or c.reps < LEARNER_REPS_CAP
    )
    return min(total, DAILY_QUEUE_LIMIT, ready)


def _repair_cards(db, user_id: int, cards: List[Card]) -> List[Card]:
    """Upgrade legacy cloze fragment cards so audio, Spanish and gloss stay aligned."""
    out: List[Card] = []
    changed = False
    for card in cards:
        norm = repair_card_vocab(card.word_es, card.word_en or "", card.word_ru or "")
        if norm["es"] == card.word_es:
            out.append(card)
            continue
        conflict = (
            db.query(Card)
            .filter(Card.user_id == user_id, Card.word_es == norm["es"], Card.id != card.id)
            .first()
        )
        if conflict:
            # Keep the sooner review date when merging fragment -> full sentence.
            if card.due <= conflict.due:
                conflict.due = card.due
                conflict.interval = _cap_interval(card.interval)
                conflict.reps = card.reps
                conflict.ease = card.ease
                conflict.lapses = card.lapses
                conflict.last_reviewed = card.last_reviewed or conflict.last_reviewed
            conflict.word_en = norm["en"] or conflict.word_en
            conflict.word_ru = norm["ru"] or conflict.word_ru
            _sanitize_card(conflict)
            db.delete(card)
            changed = True
            if conflict not in out:
                out.append(conflict)
            continue
        card.word_es = norm["es"]
        card.word_en = norm["en"]
        card.word_ru = norm["ru"]
        _sanitize_card(card)
        changed = True
        out.append(card)
    for card in out:
        if _sanitize_card(card):
            changed = True
    if changed:
        db.flush()
    return out


def _apply_sm2(card: Card, correct: bool):
    if correct:
        card.reps += 1
        if card.reps == 1:
            card.interval = 1
        elif card.reps == 2:
            card.interval = 3
        else:
            card.interval = _cap_interval(max(1, round(card.interval * card.ease)))
        card.ease = min(3.0, card.ease + 0.1)
    else:
        card.reps = 0
        card.lapses += 1
        card.interval = 1
        card.ease = max(1.3, card.ease - 0.2)
    card.interval = _cap_interval(card.interval)
    card.due = msk_today() + timedelta(days=card.interval)
    card.last_reviewed = msk_now().replace(tzinfo=None)


@router.post("/grade")
def grade(payload: GradePayload, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    updated = 0
    correct_count = 0
    cache: Dict[str, Card] = {}
    lesson_mode = not payload.award_pesos
    for item in _dedupe_grade_items(payload.items):
        card = _get_or_create_card(db, current.id, item, cache)
        if lesson_mode:
            _apply_lesson_touch(card)
        else:
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
    due = _reviewable_count(db, current.id)
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
        cards = _review_queue_cards(db, current.id, DAILY_QUEUE_LIMIT)
    cards = _repair_cards(db, current.id, cards)
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
