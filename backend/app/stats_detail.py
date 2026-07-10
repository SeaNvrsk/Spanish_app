"""Detailed per-user earnings and lesson history for stats screens."""

from datetime import timedelta
from typing import List

from sqlalchemy.orm import Session

from .models import User, LessonProgress, DailyActivity
from .curriculum import get_all_lessons
from .msk_time import msk_today


def _lesson_title(meta: dict) -> dict:
    title = meta.get("title") or meta.get("theme") or {}
    if isinstance(title, dict) and (title.get("en") or title.get("ru")):
        return {"en": title.get("en", ""), "ru": title.get("ru", ""), "es": title.get("es", "")}
    text = str(title or meta.get("lesson_id") or "")
    return {"en": text, "ru": text, "es": text}


def _lesson_pesos_for_day(row: DailyActivity) -> int:
    """Whole pesos from lessons/exams on this day (excludes review)."""
    tracked = int(getattr(row, "lesson_pesos", 0) or 0)
    if tracked > 0:
        return tracked

    lessons = int(row.lessons_completed or 0)
    if lessons <= 0:
        return 0

    pesos = int(row.pesos or 0)
    review_tenths = int(row.review_pesos or 0)
    if review_tenths == 0:
        return pesos

    # Legacy rows mixed lesson + review in `pesos`; subtract review wholes and
    # tenths carry-over (e.g. 39 review tenths → +4 whole pesos, not +3).
    review_floor = review_tenths // 10
    carry_bonus = 1 if review_tenths % 10 >= 9 else 0
    lesson_day = max(0, pesos - review_floor - carry_bonus)
    if lessons == 1 and lesson_day > 15:
        lesson_day = 15
    elif lessons == 1 and lesson_day > 5:
        lesson_day = 5
    return lesson_day


def build_user_stats_detail(db: Session, user: User, days: int = 30) -> dict:
    """Lesson/exam/review earnings for one learner."""
    all_lessons = get_all_lessons()
    progress = (
        db.query(LessonProgress)
        .filter(LessonProgress.user_id == user.id, LessonProgress.completed == True)  # noqa: E712
        .order_by(LessonProgress.last_completed_at.asc().nullsfirst(), LessonProgress.lesson_id.asc())
        .all()
    )

    lesson_history: List[dict] = []
    pesos_lessons = 0
    pesos_exams = 0
    exams_completed = 0
    lessons_completed = 0

    for row in progress:
        meta = all_lessons.get(row.lesson_id, {})
        kind = meta.get("kind", "lesson")
        earned = int(row.pesos_earned or 0)
        if kind in ("exam", "capstone"):
            pesos_exams += earned
            exams_completed += 1
        else:
            pesos_lessons += earned
            lessons_completed += 1
        lesson_history.append({
            "lesson_id": row.lesson_id,
            "title": _lesson_title(meta),
            "kind": kind,
            "week": meta.get("week"),
            "best_score": int(row.best_score or 0),
            "stars": int(row.stars or 0),
            "pesos_earned": earned,
            "attempts": int(row.attempts or 0),
            "completed_at": row.last_completed_at,
        })

    start = msk_today() - timedelta(days=days - 1)
    daily_rows = (
        db.query(DailyActivity)
        .filter(DailyActivity.user_id == user.id, DailyActivity.day >= start)
        .order_by(DailyActivity.day.asc())
        .all()
    )

    daily_earnings: List[dict] = []
    review_total_tenths = 0
    for row in daily_rows:
        review_tenths = int(row.review_pesos or 0)
        review_total_tenths += review_tenths
        review_pesos = round(review_tenths / 10, 1)
        lesson_day = _lesson_pesos_for_day(row)
        daily_earnings.append({
            "day": row.day,
            "pesos": int(row.pesos or 0),
            "pesos_lessons": lesson_day,
            "pesos_review": review_pesos,
            "pesos_total": round(lesson_day + review_pesos, 1),
            "lessons_completed": int(row.lessons_completed or 0),
        })

    pesos_review = round(review_total_tenths / 10, 1)
    pesos_all = round(pesos_lessons + pesos_exams + pesos_review, 1)

    return {
        "earnings_totals": {
            "pesos_lessons": pesos_lessons,
            "pesos_exams": pesos_exams,
            "pesos_review": pesos_review,
            "pesos_all": pesos_all,
            "lessons_completed": lessons_completed,
            "exams_completed": exams_completed,
        },
        "lesson_history": lesson_history,
        "daily_earnings": daily_earnings,
    }
