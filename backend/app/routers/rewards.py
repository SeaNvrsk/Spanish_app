import calendar
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User, DailyActivity
from ..family import competitors, FAMILY_COMPETITORS, is_competitor
from ..gamification import PLACE_SPEND_SHARE

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


def _spendable(month_pesos: int, rank: int, carryover: int) -> int:
    share = PLACE_SPEND_SHARE.get(rank, 0.0)
    return int(month_pesos * share) + (carryover or 0)


@router.get("/summary")
def summary(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    today = date.today()
    start, end = _month_bounds(today)
    days_left = (end - today).days

    pesos_map = _month_pesos_by_user(db, start)
    ranked = sorted(
        competitors(db),
        key=lambda u: (-pesos_map.get(u.id, 0), u.id),
    )

    entries = []
    my = None
    for i, u in enumerate(ranked, start=1):
        mp = pesos_map.get(u.id, 0)
        share = PLACE_SPEND_SHARE.get(i, 0.0)
        entry = {
            "rank": i,
            "id": u.id,
            "name": u.name,
            "avatar": u.avatar,
            "month_pesos": mp,
            "spend_percent": int(share * 100),
            "spendable": int(mp * share),
            "is_me": u.id == current.id,
        }
        entries.append(entry)
        if u.id == current.id:
            my = {
                "rank": i,
                "month_pesos": mp,
                "carryover": current.carryover_pesos or 0,
                "spend_percent": int(share * 100),
                "spendable": _spendable(mp, i, current.carryover_pesos),
                "is_admin": False,
            }

    if current.is_admin:
        my = {
            "rank": None,
            "month_pesos": pesos_map.get(current.id, 0),
            "carryover": 0,
            "spend_percent": 0,
            "spendable": 0,
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

    ranked = sorted(competitors(db), key=lambda u: (-pesos_map.get(u.id, 0), u.id))
    my_rank = next((i for i, u in enumerate(ranked, start=1) if u.id == current.id), None)
    if not is_competitor(current) or my_rank is None:
        raise HTTPException(status_code=403, detail="Not eligible for carryover")

    mp = pesos_map.get(current.id, 0)
    share = PLACE_SPEND_SHARE.get(my_rank, 0.0)
    current.carryover_pesos = int(mp * share) + (current.carryover_pesos or 0)
    db.commit()
    return {"carryover": current.carryover_pesos}
