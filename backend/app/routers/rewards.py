import calendar
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User, DailyActivity
from ..family import competitors, FAMILY_COMPETITORS, is_competitor
from ..gamification import month_rankings

router = APIRouter(prefix="/api/rewards", tags=["rewards"])


def _month_bounds(today: date):
    start = today.replace(day=1)
    last_day = calendar.monthrange(today.year, today.month)[1]
    end = today.replace(day=last_day)
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
    today = date.today()
    start, end = _month_bounds(today)
    days_left = (end - today).days

    pesos_map = _month_pesos_by_user(db, start)
    comp = competitors(db)
    ranked = month_rankings(comp, pesos_map)
    by_id = {u.id: u for u in comp}

    entries = []
    my = None
    for row in ranked:
        u = by_id[row["user_id"]]
        share = row["spend_share"]
        entry = {
            "rank": row["rank"],
            "id": u.id,
            "name": u.name,
            "avatar": u.avatar,
            "month_pesos": row["month_pesos"],
            "spend_percent": round(share * 100),
            "spendable": row["spendable"],
            "tied": row["tied"],
            "tie_size": row["tie_size"],
            "is_me": u.id == current.id,
        }
        entries.append(entry)
        if u.id == current.id:
            my = {
                "rank": row["rank"],
                "month_pesos": row["month_pesos"],
                "carryover": current.carryover_pesos or 0,
                "spend_percent": round(share * 100),
                "spendable": row["spendable"] + (current.carryover_pesos or 0),
                "tied": row["tied"],
                "tie_size": row["tie_size"],
                "is_admin": False,
            }

    if current.is_admin:
        my = {
            "rank": None,
            "month_pesos": pesos_map.get(current.id, 0),
            "carryover": 0,
            "spend_percent": 0,
            "spendable": 0,
            "tied": False,
            "tie_size": 1,
            "is_admin": True,
            "excluded": True,
        }

    return {
        "month": today.strftime("%Y-%m"),
        "days_left": days_left,
        "competitors": FAMILY_COMPETITORS,
        "me": my,
        "entries": entries,
    }


@router.post("/carryover")
def carryover(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current.is_admin:
        raise HTTPException(status_code=403, detail="Admin is excluded from the monthly prize pool")

    today = date.today()
    start, _ = _month_bounds(today)
    pesos_map = _month_pesos_by_user(db, start)

    ranked = month_rankings(competitors(db), pesos_map)
    my_row = next((r for r in ranked if r["user_id"] == current.id), None)
    if not is_competitor(current) or my_row is None:
        raise HTTPException(status_code=403, detail="Not eligible for carryover")

    mp = my_row["month_pesos"]
    spendable = my_row["spendable"]
    current.carryover_pesos = spendable + (current.carryover_pesos or 0)
    db.commit()
    return {"carryover": current.carryover_pesos}
