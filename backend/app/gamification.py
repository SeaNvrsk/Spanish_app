"""Shared gamification helpers: XP levels, pesos, streaks and daily activity."""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from .models import User, DailyActivity

# --- Pesos reward economy ---------------------------------------------------
# Points (XP) convert to spendable Mexican pesos for the monthly family contest.
PESOS_PER_POINT = 0.25
# Anti-inflation: cap how many XP the Daily Review can grant per day.
REVIEW_DAILY_XP_CAP = 20
# Share of the monthly balance each podium place may actually spend.
PLACE_SPEND_SHARE = {1: 1.0, 2: 0.75, 3: 0.5}


def pesos_from_xp(xp: int) -> int:
    return int((xp or 0) * PESOS_PER_POINT)


def xp_level(total_xp: int) -> int:
    """One gamified level per 100 XP."""
    return total_xp // 100 + 1


def update_streak(user: User, today: date):
    last = user.last_active_date
    if last == today:
        return
    if last == today - timedelta(days=1):
        user.current_streak += 1
    else:
        user.current_streak = 1
    user.last_active_date = today
    user.longest_streak = max(user.longest_streak, user.current_streak)


def get_daily(db: Session, user: User, today: date) -> DailyActivity:
    row = (
        db.query(DailyActivity)
        .filter(DailyActivity.user_id == user.id, DailyActivity.day == today)
        .first()
    )
    if not row:
        row = DailyActivity(user_id=user.id, day=today, xp=0, review_xp=0, lessons_completed=0)
        db.add(row)
    return row


def bump_daily(db: Session, user: User, today: date, xp: int, completed: bool, review_xp: int = 0):
    row = get_daily(db, user, today)
    row.xp += xp
    row.review_xp = (row.review_xp or 0) + review_xp
    if completed:
        row.lessons_completed += 1
