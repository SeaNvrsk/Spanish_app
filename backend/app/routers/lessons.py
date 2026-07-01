from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import copy

from ..database import get_db
from ..deps import get_current_user
from ..models import User, LessonProgress
from ..curriculum import get_curriculum, get_lesson, get_all_lessons
from ..tip_service import resolve_lesson_tip
from ..schedule import (
    program_start,
    program_day_for_date,
    max_unlocked_global_day,
    lesson_schedule_meta,
)

router = APIRouter(prefix="/api", tags=["curriculum"])


def _assert_lesson_unlocked(lesson: dict, today: date | None = None) -> None:
    if not lesson_schedule_meta(lesson["day"], today)["unlocked"]:
        meta = lesson_schedule_meta(lesson["day"], today)
        raise HTTPException(
            status_code=403,
            detail={
                "code": "lesson_locked",
                "unlock_date": meta["unlock_date"],
                "message": "This lesson unlocks on a later calendar day.",
            },
        )


@router.get("/curriculum")
def curriculum(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Full course tree annotated with progress and calendar unlock state."""
    rows = db.query(LessonProgress).filter(LessonProgress.user_id == current.id).all()
    progress = {p.lesson_id: p for p in rows}

    today = date.today()
    start = program_start()
    prog_day = program_day_for_date(today, start)
    today_lesson_id = None
    all_lessons = get_all_lessons()
    if prog_day > 0:
        match = next((l for l in all_lessons.values() if l.get("day") == prog_day), None)
        if match:
            today_lesson_id = match["id"]

    out_levels = []
    for level in get_curriculum():
        level_total = 0
        level_done = 0
        out_weeks = []
        for wk in level["weeks"]:
            out_days = []
            for day in wk["days"]:
                p = progress.get(day["id"])
                sched = lesson_schedule_meta(day["day"], today, start)
                level_total += 1
                if p and p.completed:
                    level_done += 1
                out_days.append({
                    "id": day["id"],
                    "kind": day["kind"],
                    "day": day["day"],
                    "day_in_week": day["day_in_week"],
                    "title": day["title"],
                    "icon": day["icon"],
                    "xp": day["xp"],
                    "new_vocab_count": day.get("new_vocab_count", 0),
                    "est_minutes": day.get("est_minutes", 15),
                    "has_theory": day.get("theory") is not None,
                    "completed": bool(p and p.completed),
                    "stars": p.stars if p else 0,
                    "best_score": p.best_score if p else 0,
                    "unlocked": sched["unlocked"],
                    "unlock_date": sched["unlock_date"],
                    "is_today": sched["is_today"],
                })
            out_weeks.append({
                "week": wk["week"],
                "icon": wk["icon"],
                "theme": wk["theme"],
                "is_review": wk["is_review"],
                "days": out_days,
            })
        out_levels.append({
            "id": level["id"],
            "level": level["level"],
            "months": level["months"],
            "title": level["title"],
            "description": level["description"],
            "weeks": out_weeks,
            "total_lessons": level_total,
            "completed_lessons": level_done,
            "progress_percent": round(level_done / level_total * 100) if level_total else 0,
        })
    return {
        "levels": out_levels,
        "program_start_date": start.isoformat(),
        "program_day": prog_day,
        "max_unlocked_day": max_unlocked_global_day(today, start),
        "today_lesson_id": today_lesson_id,
    }


@router.get("/lessons/{lesson_id}")
async def lesson_detail(lesson_id: str, current: User = Depends(get_current_user)):
    lesson = get_lesson(lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    _assert_lesson_unlocked(lesson)
    out = copy.deepcopy(lesson)
    if out.get("theory"):
        tip = await resolve_lesson_tip(out)
        if tip:
            out["theory"]["tip"] = tip
    return out
