from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User, DailyActivity, MonthPrizeCredit
from ..family import competitors, FAMILY_COMPETITORS, is_competitor
from ..gamification import month_rankings
from ..msk_time import msk_today, msk_month_start, msk_month_end, msk_days_left_in_month
from ..prize_bank import settle_closed_months, quarter_window, piggy_bank_by_user


router = APIRouter(prefix="/api/rewards", tags=["rewards"])


def _month_bounds(today: date | None = None):
    today = today or msk_today()
    start = msk_month_start(today)
    end = msk_month_end(today)
    return start, end


def _month_pesos_by_user(db: Session, start: date):
    rows = (
        db.query(DailyActivity.user_id, func.sum(DailyActivity.pesos))
        .filter(DailyActivity.day >= start)
        .group_by(DailyActivity.user_id)
        .all()
    )
    return {uid: int(x or 0) for uid, x in rows}


@router.get("/summary")
def summary(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Close any finished months first: place-share → piggy bank (not 100% of pesos).
    settled = settle_closed_months(db)
    if settled:
        db.commit()

    today = msk_today()
    start, end = _month_bounds(today)
    days_left = msk_days_left_in_month(today)
    banks = piggy_bank_by_user(db)
    quarter = quarter_window(today)

    pesos_map = _month_pesos_by_user(db, start)
    comp = competitors(db)
    ranked = month_rankings(comp, pesos_map)
    by_id = {u.id: u for u in comp}

    entries = []
    my = None
    for row in ranked:
        u = by_id[row["user_id"]]
        share = row["spend_share"]
        bank = banks.get(u.id, 0)
        entry = {
            "rank": row["rank"],
            "id": u.id,
            "name": u.name,
            "avatar": u.avatar,
            "month_pesos": row["month_pesos"],
            "spend_percent": round(share * 100),
            "spendable": row["spendable"],
            "piggy_bank": bank,
            "tied": row["tied"],
            "tie_size": row["tie_size"],
            "is_me": u.id == current.id,
        }
        entries.append(entry)
        if u.id == current.id:
            my = {
                "rank": row["rank"],
                "month_pesos": row["month_pesos"],
                "carryover": bank,
                "piggy_bank": bank,
                "spend_percent": round(share * 100),
                # Preview of this month's place share; bank is what can already be ordered.
                "month_share_preview": row["spendable"],
                "spendable": bank,
                "tied": row["tied"],
                "tie_size": row["tie_size"],
                "is_admin": False,
            }

    if current.is_admin:
        my = {
            "rank": None,
            "month_pesos": pesos_map.get(current.id, 0),
            "carryover": 0,
            "piggy_bank": 0,
            "month_share_preview": 0,
            "spend_percent": 0,
            "spendable": 0,
            "tied": False,
            "tie_size": 1,
            "is_admin": True,
            "excluded": True,
        }

    history = []
    if is_competitor(current) or current.is_admin:
        q = db.query(MonthPrizeCredit).order_by(MonthPrizeCredit.month.desc(), MonthPrizeCredit.rank.asc())
        if not current.is_admin:
            q = q.filter(MonthPrizeCredit.user_id == current.id)
        for row in q.limit(36).all():
            u = next((c for c in comp if c.id == row.user_id), None)
            history.append({
                "month": row.month,
                "user_id": row.user_id,
                "name": u.name if u else str(row.user_id),
                "rank": row.rank,
                "month_pesos": row.month_pesos,
                "spend_percent": round((row.spend_share or 0) * 100, 1),
                "credited": row.credited,
            })

    return {
        "month": today.strftime("%Y-%m"),
        "days_left": days_left,
        "competitors": FAMILY_COMPETITORS,
        "me": my,
        "entries": entries,
        "piggy_banks": [
            {
                "id": u.id,
                "name": u.name,
                "avatar": u.avatar,
                "piggy_bank": banks.get(u.id, 0),
                "is_me": u.id == current.id,
            }
            for u in comp
        ],
        "quarter": quarter,
        "settlements": history,
    }


@router.post("/settle")
def settle_now(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Admin/manual trigger — same auto logic as summary (idempotent)."""
    if not current.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")
    rows = settle_closed_months(db)
    if rows:
        db.commit()
    return {"settled": rows, "quarter": quarter_window()}
