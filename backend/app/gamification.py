"""Shared gamification helpers: pesos, streaks and daily activity."""

from datetime import date, timedelta

from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from .models import User, DailyActivity

# --- Pesos reward economy ---------------------------------------------------
PESOS_PER_LEVEL = 25
# Anti-inflation: daily review pays 0.1 peso per correct answer, max 5 pesos/day total.
REVIEW_TENTHS_PER_CORRECT = 1   # 0.1 peso
REVIEW_DAILY_CAP_TENTHS = 50    # 5.0 pesos
REVIEW_DAILY_PESOS_CAP = 5      # display cap (whole pesos)
# Share of the monthly balance each podium place may actually spend.
PLACE_SPEND_SHARE = {1: 1.0, 2: 0.75, 3: 0.5}


def month_rankings(users: list, pesos_map: dict[int, int]) -> list[dict]:
    """Rank learners by month pesos; tied scores pool place shares and split evenly.

    Example: two tied for 1st pool 100% + 75% → each gets 87.5% of their balance.
    """
    ordered = sorted(users, key=lambda u: (-int(pesos_map.get(u.id, 0) or 0), u.id))
    entries: list[dict] = []
    i = 0
    rank = 1
    while i < len(ordered):
        score = int(pesos_map.get(ordered[i].id, 0) or 0)
        j = i + 1
        while j < len(ordered) and int(pesos_map.get(ordered[j].id, 0) or 0) == score:
            j += 1
        group = ordered[i:j]
        n = len(group)
        pooled = sum(PLACE_SPEND_SHARE.get(rank + k, 0.0) for k in range(n))
        share_each = pooled / n if n else 0.0
        for u in group:
            mp = score
            entries.append({
                "user_id": u.id,
                "rank": rank,
                "month_pesos": mp,
                "spend_share": share_each,
                "spendable": int(mp * share_each),
                "tied": n > 1,
                "tie_size": n,
            })
        rank += n
        i = j
    return entries


def spend_share_for_rank(rank: int, tie_size: int = 1) -> float:
    """Effective spend share for a rank group (tie_size competitors at the same score)."""
    if tie_size < 1:
        tie_size = 1
    pooled = sum(PLACE_SPEND_SHARE.get(rank + k, 0.0) for k in range(tie_size))
    return pooled / tie_size


def apply_review_award(user: User, correct_count: int, already_review_tenths: int) -> dict:
    """Award review pesos in 0.1 steps; shared daily cap across all review sessions."""
    if correct_count <= 0:
        return {"earned_tenths": 0, "pesos_whole": 0, "pesos_display": 0.0}

    room = max(0, REVIEW_DAILY_CAP_TENTHS - (already_review_tenths or 0))
    earned_tenths = min(correct_count * REVIEW_TENTHS_PER_CORRECT, room)
    if earned_tenths <= 0:
        return {"earned_tenths": 0, "pesos_whole": 0, "pesos_display": 0.0}

    before = int(getattr(user, "peso_tenths", 0) or 0)
    after = before + earned_tenths
    pesos_whole = after // 10 - before // 10
    user.peso_tenths = after % 10
    user.pesos = (user.pesos or 0) + pesos_whole

    return {
        "earned_tenths": earned_tenths,
        "pesos_whole": pesos_whole,
        "pesos_display": round(earned_tenths / 10, 1),
    }


def peso_level(total_pesos: int) -> int:
    """One gamified level per 25 pesos earned."""
    return (total_pesos or 0) // PESOS_PER_LEVEL + 1


def lesson_pesos_for_score(base_pesos: int, score: int) -> int:
    """Whole pesos earned for a lesson at a given score (0–base_pesos)."""
    score = max(0, min(100, score))
    return round((base_pesos or 0) * score / 100)


def lesson_pesos_delta(base_pesos: int, new_score: int, already_earned: int) -> int:
    """Pesos to award when improving best score (never negative, never above lesson cap)."""
    target = lesson_pesos_for_score(base_pesos, new_score)
    return max(0, target - (already_earned or 0))


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
    if row:
        return row
    # /review/grade and /lessons/{id}/complete run back-to-back for the same
    # user+day, so a plain "check then insert" can race and hit the unique
    # constraint on (user_id, day), crashing the whole request and rolling
    # back pesos/streak/progress that had already been computed. ON CONFLICT
    # DO NOTHING makes this race-safe (same fix as Card creation in review.py).
    stmt = (
        sqlite_insert(DailyActivity)
        .values(user_id=user.id, day=today, pesos=0, review_pesos=0, lessons_completed=0)
        .on_conflict_do_nothing(index_elements=["user_id", "day"])
    )
    db.execute(stmt)
    db.flush()
    return (
        db.query(DailyActivity)
        .filter(DailyActivity.user_id == user.id, DailyActivity.day == today)
        .first()
    )


def bump_daily(
    db: Session,
    user: User,
    today: date,
    pesos: int,
    completed: bool,
    review_pesos: int = 0,
    lesson_pesos: int = 0,
):
    row = get_daily(db, user, today)
    row.pesos += pesos
    row.lesson_pesos = (row.lesson_pesos or 0) + (lesson_pesos or 0)
    row.review_pesos = (row.review_pesos or 0) + review_pesos
    if completed:
        row.lessons_completed += 1
