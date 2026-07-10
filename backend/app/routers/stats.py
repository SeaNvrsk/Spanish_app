from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User, LessonProgress, DailyActivity
from ..msk_time import msk_today, msk_month_start
from ..schemas import (
    LeaderboardEntry,
    StatsResponse,
    DailyActivityPublic,
    FamilyOverviewResponse,
    FamilyMemberStats,
    EarningsTotalsPublic,
    LessonEarningsPublic,
)
from ..curriculum import get_curriculum, get_all_lessons
from ..family import competitors, FAMILY_COMPETITORS
from ..gamification import month_rankings
from ..stats_detail import build_user_stats_detail

router = APIRouter(prefix="/api", tags=["stats"])


def _cefr_progress(db: Session, user: User):
    completed_ids = {
        p.lesson_id
        for p in db.query(LessonProgress).filter(
            LessonProgress.user_id == user.id, LessonProgress.completed == True  # noqa: E712
        ).all()
    }
    tree = get_curriculum()
    current_level = tree[0]["level"]
    percent = 0
    for level in tree:
        lesson_ids = [d["id"] for wk in level["weeks"] for d in wk["days"]]
        done = sum(1 for lid in lesson_ids if lid in completed_ids)
        total = len(lesson_ids)
        pct = round(done / total * 100) if total else 0
        current_level = level["level"]
        percent = pct
        if done < total:
            break
    return current_level, percent, len(completed_ids)


def _month_pesos(db: Session, user_id: int) -> int:
    start = msk_month_start()
    total = (
        db.query(func.sum(DailyActivity.pesos))
        .filter(DailyActivity.user_id == user_id, DailyActivity.day >= start)
        .scalar()
    )
    return int(total or 0)


@router.get("/leaderboard", response_model=list[LeaderboardEntry])
def leaderboard(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Family peso ranking — admins are excluded from competition."""
    users = sorted(competitors(db), key=lambda u: (-u.pesos, u.id))
    entries = []
    for i, u in enumerate(users, start=1):
        entries.append(LeaderboardEntry(
            rank=i,
            id=u.id,
            name=u.name,
            avatar=u.avatar,
            pesos=u.pesos,
            current_streak=u.current_streak,
            is_me=(u.id == current.id),
        ))
    return entries


@router.get("/stats", response_model=StatsResponse)
def stats(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cefr, percent, lessons_completed = _cefr_progress(db, current)

    comp = sorted(competitors(db), key=lambda u: (-u.pesos, u.id))
    total_competitors = len(comp)
    if current.is_admin:
        rank = 0
        total_users = total_competitors
    else:
        rank = next((i for i, u in enumerate(comp, start=1) if u.id == current.id), total_competitors)
        total_users = total_competitors

    start = msk_today() - timedelta(days=29)
    detail = build_user_stats_detail(db, current, days=30)
    activity = [DailyActivityPublic(**row) for row in detail["daily_earnings"]]

    return StatsResponse(
        total_pesos=current.pesos,
        lessons_completed=lessons_completed,
        current_streak=current.current_streak,
        longest_streak=current.longest_streak,
        cefr_level=cefr,
        level_progress_percent=percent,
        rank=rank,
        total_users=total_users,
        is_admin=bool(current.is_admin),
        activity=activity,
        earnings_totals=EarningsTotalsPublic(**detail["earnings_totals"]),
        lesson_history=[LessonEarningsPublic(**row) for row in detail["lesson_history"]],
        daily_earnings=activity,
    )


@router.get("/admin/family-overview", response_model=FamilyOverviewResponse)
def family_overview(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    month = msk_today().strftime("%Y-%m")
    pesos_map = {u.id: _month_pesos(db, u.id) for u in competitors(db)}
    comp_ranked = month_rankings(competitors(db), pesos_map)
    comp_rank = {row["user_id"]: row["rank"] for row in comp_ranked}

    members = []
    for u in db.query(User).order_by(User.is_admin.asc(), User.name.asc()).all():
        cefr, pct, lessons = _cefr_progress(db, u)
        detail = build_user_stats_detail(db, u, days=30)
        daily = [DailyActivityPublic(**row) for row in detail["daily_earnings"]]
        members.append(FamilyMemberStats(
            id=u.id,
            name=u.name,
            avatar=u.avatar,
            is_admin=bool(u.is_admin),
            pesos=u.pesos,
            month_pesos=_month_pesos(db, u.id),
            current_streak=u.current_streak,
            longest_streak=u.longest_streak,
            lessons_completed=lessons,
            cefr_level=cefr,
            level_progress_percent=pct,
            rank=None if u.is_admin else comp_rank.get(u.id),
            earnings_totals=EarningsTotalsPublic(**detail["earnings_totals"]),
            lesson_history=[LessonEarningsPublic(**row) for row in detail["lesson_history"]],
            daily_earnings=daily,
        ))

    return FamilyOverviewResponse(
        competitors=FAMILY_COMPETITORS,
        month=month,
        members=members,
    )
