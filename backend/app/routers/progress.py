from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User, LessonProgress
from ..schemas import LessonResult, CompleteResponse
from ..curriculum import get_lesson
from ..schedule import lesson_schedule_meta
from ..msk_time import msk_today, msk_now
from ..gamification import (
    peso_level as _peso_level,
    update_streak as _update_streak,
    bump_daily as _bump_daily,
)

router = APIRouter(prefix="/api", tags=["progress"])

PASS_THRESHOLD = 50


def _stars_for(score: int) -> int:
    if score >= 90:
        return 3
    if score >= 70:
        return 2
    if score >= 50:
        return 1
    return 0


@router.post("/lessons/{lesson_id}/complete", response_model=CompleteResponse)
def complete_lesson(
    lesson_id: str,
    payload: LessonResult,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lesson = get_lesson(lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    if not lesson_schedule_meta(lesson["day"])["unlocked"]:
        raise HTTPException(status_code=403, detail="Lesson not unlocked yet")

    score = max(0, min(100, payload.score))
    base_pesos = lesson["pesos"]
    stars = _stars_for(score)
    passed = score >= PASS_THRESHOLD

    prog = (
        db.query(LessonProgress)
        .filter(LessonProgress.user_id == current.id, LessonProgress.lesson_id == lesson_id)
        .first()
    )

    new_completion = False
    if prog is None:
        prog = LessonProgress(
            user_id=current.id,
            lesson_id=lesson_id,
            completed=False,
            best_score=0,
            stars=0,
            pesos_earned=0,
            attempts=0,
        )
        db.add(prog)
        earned = round(base_pesos * score / 100) if passed else 0
        new_completion = passed
    else:
        prog.attempts = prog.attempts or 0
        prog.best_score = prog.best_score or 0
        prog.stars = prog.stars or 0
        prog.pesos_earned = prog.pesos_earned or 0
        prog.completed = bool(prog.completed)
        if score > prog.best_score:
            earned = round(base_pesos * (score - prog.best_score) / 100)
        else:
            earned = 0
        if passed and not prog.completed:
            new_completion = True

    prog.attempts += 1
    prog.best_score = max(prog.best_score, score)
    prog.stars = max(prog.stars, stars)
    if passed:
        prog.completed = True
    prog.pesos_earned += earned
    prog.last_completed_at = msk_now().replace(tzinfo=None)

    before_level = _peso_level(current.pesos)
    current.pesos += earned
    after_level = _peso_level(current.pesos)

    today = msk_today()
    if earned > 0 or new_completion:
        _update_streak(current, today)
    _bump_daily(db, current, today, earned, new_completion)

    db.commit()
    db.refresh(current)

    return CompleteResponse(
        pesos_earned=earned,
        total_pesos=current.pesos,
        stars=prog.stars,
        best_score=prog.best_score,
        current_streak=current.current_streak,
        leveled_up=after_level > before_level,
        new_completion=new_completion,
    )
