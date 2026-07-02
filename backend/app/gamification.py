"""Shared gamification helpers: pesos, streaks and daily activity."""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from .models import User, DailyActivity

# --- Pesos reward economy ---------------------------------------------------
PESOS_PER_LEVEL = 25
# Anti-inflation: cap how many pesos the Daily Review can grant per day.
REVIEW_DAILY_PESOS_CAP = 5
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


def peso_level(total_pesos: int) -> int:
    """One gamified level per 25 pesos earned."""
    return (total_pesos or 0) // PESOS_PER_LEVEL + 1


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
        row = DailyActivity(user_id=user.id, day=today, pesos=0, review_pesos=0, lessons_completed=0)
        db.add(row)
    return row


def bump_daily(
    db: Session,
    user: User,
    today: date,
    pesos: int,
    completed: bool,
    review_pesos: int = 0,
):
    row = get_daily(db, user, today)
    row.pesos += pesos
    row.review_pesos = (row.review_pesos or 0) + review_pesos
    if completed:
        row.lessons_completed += 1
